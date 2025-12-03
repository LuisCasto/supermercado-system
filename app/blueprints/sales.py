"""
Blueprint de Ventas
Endpoints: crear venta, listar tickets, consultar venta
Implementa Outbox Pattern para consistencia eventual con MongoDB

IMPORTANTE:
- PostgreSQL es la fuente de la verdad del stock
- MongoDB almacena los tickets para consultas
- El Outbox garantiza que cada venta en Postgres tenga su ticket en Mongo
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid
import logging

from app.models import Product, ProductBatch, InventoryMovement, OutboxEvent, User
from app.utils.db_postgres import db_postgres
from app.utils.db_mongo import db_mongo
from app.middleware.auth_middleware import token_required
from app.middleware.rbac_middleware import cajero_or_gerente, gerente_only

logger = logging.getLogger(__name__)

sales_bp = Blueprint('sales', __name__)


def allocate_stock_fifo(session, product_id, quantity_needed):
    """
    Asignar stock usando estrategia FIFO (First In, First Out)
    Prioriza lotes por fecha de vencimiento
    
    Args:
        session: Sesión de SQLAlchemy
        product_id: ID del producto
        quantity_needed: Cantidad a asignar
    
    Returns:
        list: Lista de asignaciones [(batch_id, quantity, unit_cost), ...]
    
    Raises:
        ValueError: Si no hay suficiente stock
    """
    # Obtener lotes con stock disponible, ordenados por FIFO
    batches = session.query(ProductBatch).filter(
        and_(
            ProductBatch.product_id == product_id,
            ProductBatch.quantity > 0
        )
    ).order_by(
        # Primero los que vencen antes (FIFO)
        ProductBatch.expiration_date.asc().nullslast(),
        # Luego los recibidos primero
        ProductBatch.received_date.asc()
    ).with_for_update().all()  # ← LOCK para evitar race conditions
    
    if not batches:
        raise ValueError(f"No hay stock disponible para el producto {product_id}")
    
    # Verificar stock total disponible
    total_available = sum(b.quantity for b in batches)
    if total_available < quantity_needed:
        raise ValueError(
            f"Stock insuficiente. Disponible: {total_available}, "
            f"Requerido: {quantity_needed}"
        )
    
    # Asignar cantidades desde los lotes (FIFO)
    allocations = []
    remaining = quantity_needed
    
    for batch in batches:
        if remaining <= 0:
            break
        
        # Cantidad a tomar de este lote
        quantity_from_batch = min(batch.quantity, remaining)
        
        allocations.append({
            'batch_id': batch.id,
            'batch_code': batch.batch_code,
            'quantity': quantity_from_batch,
            'cost_per_unit': float(batch.cost_per_unit)
        })
        
        remaining -= quantity_from_batch
    
    return allocations


@sales_bp.route('', methods=['POST'])
@token_required
@cajero_or_gerente
def create_sale(current_user):
    """
    Crear venta y registrarla en Outbox
    Solo cajeros y gerentes
    
    Body:
    {
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "unit_price": 25.50  // opcional, usa base_price si no se provee
            },
            {
                "product_id": 3,
                "quantity": 1
            }
        ],
        "payment_method": "cash",  // cash, card, transfer
        "payment_details": {       // opcional
            "amount_paid": 100.00,
            "change": 19.00
        },
        "tax_rate": 0.16           // opcional, default: 0.16 (16%)
    }
    
    Response:
    {
        "message": "Venta registrada exitosamente",
        "sale_id": "SALE-2025-001",
        "total": 69.00,
        "grand_total": 80.04,
        "outbox_event_id": 123
    }
    """
    try:
        data = request.get_json()
        
        # Validar estructura
        if not data or 'items' not in data or not data['items']:
            return jsonify({
                'error': 'Datos incompletos',
                'message': 'Debes enviar al menos un item en la venta'
            }), 400
        
        # Validar items
        for idx, item in enumerate(data['items']):
            if 'product_id' not in item or 'quantity' not in item:
                return jsonify({
                    'error': f'Item {idx} incompleto',
                    'message': 'Cada item debe tener product_id y quantity'
                }), 400
            
            try:
                qty = int(item['quantity'])
                if qty <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    'error': f'Cantidad inválida en item {idx}',
                    'message': 'La cantidad debe ser un número entero mayor a 0'
                }), 400
        
        # Validar payment_method
        payment_method = data.get('payment_method', 'cash')
        valid_methods = ['cash', 'card', 'transfer', 'other']
        if payment_method not in valid_methods:
            return jsonify({
                'error': 'Método de pago inválido',
                'message': f'Debe ser uno de: {", ".join(valid_methods)}'
            }), 400
        
        # Tax rate
        tax_rate = float(data.get('tax_rate', 0.16))
        
        session = db_postgres.get_session()
        try:
            # ====================================================================
            # FASE 1: VALIDACIÓN Y PREPARACIÓN
            # ====================================================================
            
            sale_items = []
            total = 0.0
            
            for item in data['items']:
                product_id = item['product_id']
                quantity = int(item['quantity'])
                
                # Obtener producto
                product = session.query(Product).filter_by(
                    id=product_id,
                    active=True
                ).first()
                
                if not product:
                    return jsonify({
                        'error': 'Producto no encontrado',
                        'message': f'El producto {product_id} no existe o está inactivo'
                    }), 404
                
                # Precio unitario (usar el provisto o el base_price)
                unit_price = float(item.get('unit_price', product.base_price))
                
                # Asignar stock usando FIFO
                try:
                    allocations = allocate_stock_fifo(session, product_id, quantity)
                except ValueError as e:
                    session.rollback()
                    return jsonify({
                        'error': 'Stock insuficiente',
                        'message': str(e),
                        'product': product.to_dict()
                    }), 400
                
                # Calcular subtotal
                subtotal = unit_price * quantity
                total += subtotal
                
                sale_items.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'sku': product.sku,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': subtotal,
                    'allocations': allocations  # Para decrementar después
                })
            
            # Calcular totales
            tax = total * tax_rate
            grand_total = total + tax
            
            # ====================================================================
            # FASE 2: TRANSACCIÓN ATÓMICA (Postgres)
            # ====================================================================
            
            # Generar ID único de venta
            sale_id = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
            
            # Decrementar stock y registrar movimientos
            for item in sale_items:
                for allocation in item['allocations']:
                    batch_id = allocation['batch_id']
                    qty_allocated = allocation['quantity']
                    
                    # Actualizar cantidad del lote
                    batch = session.query(ProductBatch).filter_by(id=batch_id).first()
                    batch.quantity -= qty_allocated
                    
                    # Registrar movimiento de inventario
                    movement = InventoryMovement(
                        product_batch_id=batch_id,
                        movement_type='SALE',
                        quantity=-qty_allocated,  # Negativo porque es salida
                        user_id=current_user['id'],
                        reference_id=sale_id,
                        note=f"Venta {sale_id}"
                    )
                    session.add(movement)
            
            # ====================================================================
            # FASE 3: CREAR EVENTO OUTBOX (garantiza consistencia eventual)
            # ====================================================================
            
            # Preparar payload del ticket para MongoDB
            ticket_payload = {
                'sale_id': sale_id,
                'cashier_id': current_user['id'],
                'cashier_name': current_user['username'],
                'items': [
                    {
                        'product_id': item['product_id'],
                        'product_name': item['product_name'],
                        'sku': item['sku'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'subtotal': item['subtotal']
                    }
                    for item in sale_items
                ],
                'total': round(total, 2),
                'tax': round(tax, 2),
                'grand_total': round(grand_total, 2),
                'payment_method': payment_method,
                'payment_details': data.get('payment_details', {}),
                'status': 'completed',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Crear evento en Outbox
            outbox_event = OutboxEvent(
                event_type='SALE_CREATED',
                aggregate_id=sale_id,
                payload=ticket_payload,
                status='PENDING'
            )
            session.add(outbox_event)
            
            # COMMIT: todo o nada
            session.commit()
            session.refresh(outbox_event)
            
            # ====================================================================
            # ÉXITO
            # ====================================================================
            
            logger.info(
                f"Venta creada: {sale_id} - Total: ${grand_total:.2f} - "
                f"Cajero: {current_user['username']} - Outbox: {outbox_event.id}"
            )
            
            return jsonify({
                'message': 'Venta registrada exitosamente',
                'sale_id': sale_id,
                'items_count': len(sale_items),
                'total': round(total, 2),
                'tax': round(tax, 2),
                'grand_total': round(grand_total, 2),
                'payment_method': payment_method,
                'outbox_event_id': outbox_event.id,
                'note': 'El ticket se procesará en MongoDB a través del worker'
            }), 201
        
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Error de integridad en venta: {e}")
            return jsonify({
                'error': 'Error de integridad',
                'message': 'Ocurrió un problema al procesar la venta'
            }), 500
        except Exception as e:
            session.rollback()
            logger.error(f"Error en venta: {e}")
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error crítico en venta: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al procesar la venta'
        }), 500


@sales_bp.route('/<sale_id>', methods=['GET'])
@token_required
def get_sale(current_user, sale_id):
    """
    Obtener detalles de una venta
    - Gerentes pueden ver cualquier venta
    - Cajeros solo pueden ver sus propias ventas
    
    Response:
    {
        "sale": {...}  // ticket desde MongoDB
    }
    """
    try:
        mongo_db = db_mongo.get_db()
        sales_collection = mongo_db['sales_tickets']
        
        # Buscar ticket en MongoDB
        ticket = sales_collection.find_one({'sale_id': sale_id})
        
        if not ticket:
            return jsonify({
                'error': 'Venta no encontrada',
                'message': f'No existe una venta con ID {sale_id}',
                'note': 'Si la venta acaba de crearse, el worker aún no la ha procesado'
            }), 404
        
        # Control de acceso: cajeros solo ven sus ventas
        if current_user['role'] == 'cajero':
            if ticket.get('cashier_id') != current_user['id']:
                return jsonify({
                    'error': 'Acceso denegado',
                    'message': 'Solo puedes ver tus propias ventas'
                }), 403
        
        # Convertir ObjectId a string
        ticket['_id'] = str(ticket['_id'])
        
        return jsonify({
            'sale': ticket
        }), 200
    
    except Exception as e:
        logger.error(f"Error obteniendo venta {sale_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener la venta'
        }), 500


@sales_bp.route('', methods=['GET'])
@token_required
def list_sales(current_user):
    """
    Listar ventas desde MongoDB
    - Gerentes pueden ver todas las ventas
    - Cajeros solo ven sus propias ventas
    
    Query params:
    - cashier_id: filtrar por cajero (solo gerentes)
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - status: completed, cancelled, refunded
    - page, per_page: paginación
    
    Response:
    {
        "sales": [...],
        "total": 50,
        "page": 1,
        "pages": 5
    }
    """
    try:
        # Paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        skip = (page - 1) * per_page
        
        # Filtros
        cashier_id = request.args.get('cashier_id', type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        mongo_db = db_mongo.get_db()
        sales_collection = mongo_db['sales_tickets']
        
        # Construir query de MongoDB
        query = {}
        
        # Control de acceso: cajeros solo ven sus ventas
        if current_user['role'] == 'cajero':
            query['cashier_id'] = current_user['id']
        elif cashier_id:  # Gerentes pueden filtrar por cajero
            query['cashier_id'] = cashier_id
        
        # Filtro por estado
        if status:
            query['status'] = status
        
        # Filtro por rango de fechas
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    date_filter['$gte'] = start
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    # Incluir todo el día
                    end = end.replace(hour=23, minute=59, second=59)
                    date_filter['$lte'] = end
                except ValueError:
                    pass
            
            if date_filter:
                query['timestamp'] = date_filter
        
        # Obtener total
        total = sales_collection.count_documents(query)
        
        # Obtener documentos con paginación
        sales_cursor = sales_collection.find(query).sort(
            'timestamp', -1  # Más recientes primero
        ).skip(skip).limit(per_page)
        
        sales = []
        for sale in sales_cursor:
            sale['_id'] = str(sale['_id'])
            sales.append(sale)
        
        pages = (total + per_page - 1) // per_page
        
        return jsonify({
            'sales': sales,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }), 200
    
    except Exception as e:
        logger.error(f"Error listando ventas: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar las ventas'
        }), 500


@sales_bp.route('/stats', methods=['GET'])
@token_required
def sales_stats(current_user):
    """
    Estadísticas de ventas
    - Gerentes: estadísticas globales
    - Cajeros: solo sus estadísticas
    
    Query params:
    - start_date, end_date: rango de fechas
    
    Response:
    {
        "total_sales": 45,
        "total_amount": 12500.50,
        "average_ticket": 277.79,
        "by_payment_method": {...},
        "top_products": [...]
    }
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        mongo_db = db_mongo.get_db()
        sales_collection = mongo_db['sales_tickets']
        
        # Construir filtro base
        match_filter = {}
        
        # Control de acceso
        if current_user['role'] == 'cajero':
            match_filter['cashier_id'] = current_user['id']
        
        # Filtro de fechas
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    date_filter['$gte'] = start
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    end = end.replace(hour=23, minute=59, second=59)
                    date_filter['$lte'] = end
                except ValueError:
                    pass
            
            if date_filter:
                match_filter['timestamp'] = date_filter
        
        # Pipeline de agregación
        pipeline = [
            {'$match': match_filter},
            {
                '$group': {
                    '_id': None,
                    'total_sales': {'$sum': 1},
                    'total_amount': {'$sum': '$grand_total'},
                    'by_payment_method': {
                        '$push': '$payment_method'
                    }
                }
            }
        ]
        
        result = list(sales_collection.aggregate(pipeline))
        
        if not result:
            return jsonify({
                'total_sales': 0,
                'total_amount': 0,
                'average_ticket': 0,
                'by_payment_method': {}
            }), 200
        
        stats = result[0]
        total_sales = stats['total_sales']
        total_amount = stats['total_amount']
        
        # Calcular promedio
        average_ticket = total_amount / total_sales if total_sales > 0 else 0
        
        # Contar por método de pago
        payment_methods = {}
        for method in stats['by_payment_method']:
            payment_methods[method] = payment_methods.get(method, 0) + 1
        
        return jsonify({
            'total_sales': total_sales,
            'total_amount': round(total_amount, 2),
            'average_ticket': round(average_ticket, 2),
            'by_payment_method': payment_methods
        }), 200
    
    except Exception as e:
        logger.error(f"Error generando estadísticas: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al generar las estadísticas'
        }), 500