"""
Blueprint de Inventario
Endpoints: gestión de lotes (batches), entradas, ajustes, consultas
RBAC:
- Gerentes e inventario: todas las operaciones
- Cajeros: solo consultar stock
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta

from app.models import Product, ProductBatch, InventoryMovement, User
from app.utils.db_postgres import db_postgres
from app.middleware.auth_middleware import token_required
from app.middleware.rbac_middleware import inventario_or_gerente, gerente_only
import logging

logger = logging.getLogger(__name__)

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/batches', methods=['GET'])
@token_required
def list_batches(current_user):
    """
    Listar lotes de productos con filtros
    
    Query params:
    - product_id: filtrar por producto específico
    - expired: true/false (solo expirados)
    - expiring_soon: días (ej: 7 = próximos 7 días)
    - low_stock: cantidad mínima (ej: 10)
    - page: número de página
    - per_page: lotes por página
    
    Response:
    {
        "batches": [...],
        "total": 50,
        "page": 1,
        "pages": 5
    }
    """
    try:
        # Paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Filtros
        product_id = request.args.get('product_id', type=int)
        expired = request.args.get('expired', '').lower() == 'true'
        expiring_days = request.args.get('expiring_soon', type=int)
        low_stock = request.args.get('low_stock', type=int)
        
        session = db_postgres.get_session()
        try:
            # Query base
            query = session.query(ProductBatch).join(Product)
            
            # Filtro: producto específico
            if product_id:
                query = query.filter(ProductBatch.product_id == product_id)
            
            # Filtro: lotes expirados
            if expired:
                query = query.filter(
                    and_(
                        ProductBatch.expiration_date != None,
                        ProductBatch.expiration_date < date.today()
                    )
                )
            
            # Filtro: próximos a vencer
            if expiring_days:
                expiry_threshold = date.today() + timedelta(days=expiring_days)
                query = query.filter(
                    and_(
                        ProductBatch.expiration_date != None,
                        ProductBatch.expiration_date <= expiry_threshold,
                        ProductBatch.expiration_date >= date.today()
                    )
                )
            
            # Filtro: stock bajo
            if low_stock:
                query = query.filter(
                    and_(
                        ProductBatch.quantity > 0,
                        ProductBatch.quantity <= low_stock
                    )
                )
            
            # Ordenar: por fecha de vencimiento (FIFO)
            query = query.order_by(
                ProductBatch.expiration_date.asc().nullslast(),
                ProductBatch.received_date.asc()
            )
            
            # Total
            total = query.count()
            
            # Paginación
            batches_page = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convertir a dict
            batches_data = [batch.to_dict(include_product=True) for batch in batches_page]
            
            # Agregar información adicional
            for batch_dict in batches_data:
                batch_obj = next(b for b in batches_page if b.id == batch_dict['id'])
                
                # Verificar si está expirado
                if batch_obj.expiration_date:
                    batch_dict['is_expired'] = batch_obj.expiration_date < date.today()
                    
                    # Días hasta vencimiento
                    if batch_obj.expiration_date >= date.today():
                        days_until_expiry = (batch_obj.expiration_date - date.today()).days
                        batch_dict['days_until_expiry'] = days_until_expiry
            
            pages = (total + per_page - 1) // per_page
            
            return jsonify({
                'batches': batches_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error listando lotes: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar los lotes'
        }), 500


@inventory_bp.route('/batches/<int:batch_id>', methods=['GET'])
@token_required
def get_batch(current_user, batch_id):
    """
    Obtener detalles de un lote específico
    
    Query params:
    - include_movements: true/false (incluir historial de movimientos)
    
    Response:
    {
        "batch": {...},
        "movements": [...]  # si include_movements=true
    }
    """
    try:
        include_movements = request.args.get('include_movements', 'false').lower() == 'true'
        
        session = db_postgres.get_session()
        try:
            batch = session.query(ProductBatch).filter_by(id=batch_id).first()
            
            if not batch:
                return jsonify({
                    'error': 'Lote no encontrado',
                    'message': f'No existe un lote con ID {batch_id}'
                }), 404
            
            batch_dict = batch.to_dict(include_product=True)
            
            # Agregar información de expiración
            if batch.expiration_date:
                batch_dict['is_expired'] = batch.expiration_date < date.today()
                if batch.expiration_date >= date.today():
                    batch_dict['days_until_expiry'] = (batch.expiration_date - date.today()).days
            
            # Incluir movimientos si se solicita
            if include_movements:
                movements = session.query(InventoryMovement).filter_by(
                    product_batch_id=batch_id
                ).order_by(
                    InventoryMovement.created_at.desc()
                ).all()
                
                batch_dict['movements'] = [
                    mov.to_dict(include_relations=True) for mov in movements
                ]
            
            return jsonify({
                'batch': batch_dict
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo lote {batch_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener el lote'
        }), 500


@inventory_bp.route('/entry', methods=['POST'])
@token_required
@inventario_or_gerente
def create_entry(current_user):
    """
    Registrar entrada de mercancía (nuevo lote)
    Solo gerentes e inventario
    
    Body:
    {
        "product_id": 1,
        "batch_code": "LOTE-2025-001",
        "quantity": 100,
        "cost_per_unit": 15.50,
        "expiration_date": "2025-12-31",  # opcional
        "received_date": "2025-11-28",     # opcional (default: hoy)
        "note": "Recepción de proveedor XYZ"
    }
    
    Response:
    {
        "message": "Entrada registrada",
        "batch": {...},
        "movement": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['product_id', 'batch_code', 'quantity', 'cost_per_unit']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({
                    'error': 'Datos incompletos',
                    'message': f'El campo {field} es requerido'
                }), 400
        
        # Validar cantidad
        try:
            quantity = int(data['quantity'])
            if quantity <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Cantidad inválida',
                'message': 'La cantidad debe ser un número entero mayor a 0'
            }), 400
        
        # Validar costo
        try:
            cost_per_unit = float(data['cost_per_unit'])
            if cost_per_unit <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Costo inválido',
                'message': 'El costo debe ser un número mayor a 0'
            }), 400
        
        # Validar fechas
        expiration_date = None
        if data.get('expiration_date'):
            try:
                expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Fecha inválida',
                    'message': 'El formato de expiration_date debe ser YYYY-MM-DD'
                }), 400
        
        received_date = date.today()
        if data.get('received_date'):
            try:
                received_date = datetime.strptime(data['received_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Fecha inválida',
                    'message': 'El formato de received_date debe ser YYYY-MM-DD'
                }), 400
        
        session = db_postgres.get_session()
        try:
            # Verificar que el producto exista
            product = session.query(Product).filter_by(id=data['product_id']).first()
            if not product:
                return jsonify({
                    'error': 'Producto no encontrado',
                    'message': f'No existe un producto con ID {data["product_id"]}'
                }), 404
            
            # Verificar que no exista el mismo batch_code para este producto
            existing_batch = session.query(ProductBatch).filter_by(
                product_id=data['product_id'],
                batch_code=data['batch_code']
            ).first()
            
            if existing_batch:
                return jsonify({
                    'error': 'Lote duplicado',
                    'message': f'Ya existe un lote con código {data["batch_code"]} para este producto'
                }), 409
            
            # Crear lote
            new_batch = ProductBatch(
                product_id=data['product_id'],
                batch_code=data['batch_code'].strip().upper(),
                quantity=quantity,
                cost_per_unit=cost_per_unit,
                expiration_date=expiration_date,
                received_date=received_date
            )
            
            session.add(new_batch)
            session.flush()  # Para obtener el ID del lote
            
            # Crear movimiento de inventario
            movement = InventoryMovement(
                product_batch_id=new_batch.id,
                movement_type='ENTRY',
                quantity=quantity,
                user_id=current_user['id'],
                note=data.get('note', f'Entrada de lote {new_batch.batch_code}')
            )
            
            session.add(movement)
            session.commit()
            
            # Refrescar para obtener datos completos
            session.refresh(new_batch)
            session.refresh(movement)
            
            logger.info(
                f"Entrada registrada: {new_batch.batch_code} ({quantity} unidades) "
                f"por {current_user['username']}"
            )
            
            return jsonify({
                'message': 'Entrada registrada exitosamente',
                'batch': new_batch.to_dict(include_product=True),
                'movement': movement.to_dict()
            }), 201
        
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Error de integridad al crear entrada: {e}")
            return jsonify({
                'error': 'Error de integridad',
                'message': 'El lote ya existe o hay un problema con los datos'
            }), 409
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error registrando entrada: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al registrar la entrada'
        }), 500


@inventory_bp.route('/adjustment', methods=['POST'])
@token_required
@inventario_or_gerente
def create_adjustment(current_user):
    """
    Realizar ajuste de inventario (aumentar o disminuir stock)
    Solo gerentes e inventario
    
    Body:
    {
        "batch_id": 1,
        "quantity": -5,  # negativo para disminuir, positivo para aumentar
        "note": "Producto dañado"
    }
    
    Response:
    {
        "message": "Ajuste realizado",
        "batch": {...},
        "movement": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['batch_id', 'quantity', 'note']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({
                    'error': 'Datos incompletos',
                    'message': f'El campo {field} es requerido'
                }), 400
        
        # Validar cantidad
        try:
            quantity = int(data['quantity'])
            if quantity == 0:
                raise ValueError("La cantidad no puede ser 0")
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': 'Cantidad inválida',
                'message': 'La cantidad debe ser un número entero diferente de 0'
            }), 400
        
        session = db_postgres.get_session()
        try:
            # Obtener lote
            batch = session.query(ProductBatch).filter_by(id=data['batch_id']).first()
            
            if not batch:
                return jsonify({
                    'error': 'Lote no encontrado',
                    'message': f'No existe un lote con ID {data["batch_id"]}'
                }), 404
            
            # Verificar que no quede negativo
            new_quantity = batch.quantity + quantity
            if new_quantity < 0:
                return jsonify({
                    'error': 'Cantidad insuficiente',
                    'message': f'El lote tiene {batch.quantity} unidades. No puedes disminuir {abs(quantity)} unidades.'
                }), 400
            
            # Actualizar cantidad del lote
            batch.quantity = new_quantity
            
            # Crear movimiento
            movement = InventoryMovement(
                product_batch_id=batch.id,
                movement_type='ADJUSTMENT',
                quantity=quantity,
                user_id=current_user['id'],
                note=data['note']
            )
            
            session.add(movement)
            session.commit()
            
            session.refresh(batch)
            session.refresh(movement)
            
            logger.info(
                f"Ajuste realizado: {batch.batch_code} ({quantity:+d} unidades) "
                f"por {current_user['username']}"
            )
            
            return jsonify({
                'message': 'Ajuste realizado exitosamente',
                'batch': batch.to_dict(include_product=True),
                'movement': movement.to_dict()
            }), 200
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error realizando ajuste: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al realizar el ajuste'
        }), 500


@inventory_bp.route('/movements', methods=['GET'])
@token_required
def list_movements(current_user):
    """
    Listar movimientos de inventario (auditoría)
    
    Query params:
    - batch_id: filtrar por lote
    - product_id: filtrar por producto
    - movement_type: ENTRY, SALE, ADJUSTMENT, EXPIRATION
    - user_id: filtrar por usuario
    - start_date: fecha inicio (YYYY-MM-DD)
    - end_date: fecha fin (YYYY-MM-DD)
    - page, per_page: paginación
    
    Response:
    {
        "movements": [...],
        "total": 100,
        "page": 1,
        "pages": 10
    }
    """
    try:
        # Paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        # Filtros
        batch_id = request.args.get('batch_id', type=int)
        product_id = request.args.get('product_id', type=int)
        movement_type = request.args.get('movement_type')
        user_id = request.args.get('user_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        session = db_postgres.get_session()
        try:
            # Query base
            query = session.query(InventoryMovement)
            
            # Filtro: lote específico
            if batch_id:
                query = query.filter(InventoryMovement.product_batch_id == batch_id)
            
            # Filtro: producto específico
            if product_id:
                query = query.join(ProductBatch).filter(ProductBatch.product_id == product_id)
            
            # Filtro: tipo de movimiento
            if movement_type:
                valid_types = ['ENTRY', 'SALE', 'ADJUSTMENT', 'EXPIRATION']
                if movement_type.upper() in valid_types:
                    query = query.filter(InventoryMovement.movement_type == movement_type.upper())
            
            # Filtro: usuario
            if user_id:
                query = query.filter(InventoryMovement.user_id == user_id)
            
            # Filtro: rango de fechas
            if start_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    query = query.filter(InventoryMovement.created_at >= start)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    # Incluir todo el día
                    end = end.replace(hour=23, minute=59, second=59)
                    query = query.filter(InventoryMovement.created_at <= end)
                except ValueError:
                    pass
            
            # Ordenar por fecha (más recientes primero)
            query = query.order_by(InventoryMovement.created_at.desc())
            
            # Total
            total = query.count()
            
            # Paginación
            movements_page = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convertir a dict con relaciones
            movements_data = [
                mov.to_dict(include_relations=True) for mov in movements_page
            ]
            
            pages = (total + per_page - 1) // per_page
            
            return jsonify({
                'movements': movements_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error listando movimientos: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar los movimientos'
        }), 500


@inventory_bp.route('/stock-summary', methods=['GET'])
@token_required
def stock_summary(current_user):
    """
    Resumen de stock por producto
    
    Response:
    {
        "summary": [
            {
                "product": {...},
                "total_quantity": 150,
                "total_batches": 3,
                "oldest_expiration": "2025-12-01",
                "expired_quantity": 0,
                "expiring_soon_quantity": 20
            }
        ]
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            # Obtener todos los productos activos
            products = session.query(Product).filter_by(active=True).all()
            
            summary = []
            today = date.today()
            expiry_threshold = today + timedelta(days=7)
            
            for product in products:
                # Calcular estadísticas
                batches = product.batches.filter(ProductBatch.quantity > 0).all()
                
                total_quantity = sum(b.quantity for b in batches)
                total_batches = len(batches)
                
                # Lotes expirados
                expired_batches = [
                    b for b in batches 
                    if b.expiration_date and b.expiration_date < today
                ]
                expired_quantity = sum(b.quantity for b in expired_batches)
                
                # Lotes próximos a vencer
                expiring_batches = [
                    b for b in batches
                    if b.expiration_date and today <= b.expiration_date <= expiry_threshold
                ]
                expiring_soon_quantity = sum(b.quantity for b in expiring_batches)
                
                # Fecha de vencimiento más próxima
                valid_expiry_dates = [
                    b.expiration_date for b in batches
                    if b.expiration_date and b.expiration_date >= today
                ]
                oldest_expiration = min(valid_expiry_dates) if valid_expiry_dates else None
                
                summary.append({
                    'product': product.to_dict(),
                    'total_quantity': total_quantity,
                    'total_batches': total_batches,
                    'oldest_expiration': oldest_expiration.isoformat() if oldest_expiration else None,
                    'expired_quantity': expired_quantity,
                    'expiring_soon_quantity': expiring_soon_quantity
                })
            
            # Ordenar por cantidad total (mayor a menor)
            summary.sort(key=lambda x: x['total_quantity'], reverse=True)
            
            return jsonify({
                'summary': summary,
                'total_products': len(summary)
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error generando resumen de stock: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al generar el resumen'
        }), 500