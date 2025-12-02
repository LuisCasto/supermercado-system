"""
Blueprint de Productos
Endpoints: listar, crear, actualizar, eliminar, búsqueda
RBAC: 
- Todos pueden ver productos
- Solo gerentes pueden crear/modificar/eliminar
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from datetime import date, timedelta

from app.models import Product, ProductBatch
from app.utils.db_postgres import db_postgres
from app.middleware.auth_middleware import token_required, optional_token
from app.middleware.rbac_middleware import gerente_only
import logging

logger = logging.getLogger(__name__)

products_bp = Blueprint('products', __name__)


@products_bp.route('', methods=['GET'])
@optional_token
def list_products(current_user):
    """
    Listar productos con filtros opcionales
    
    Query params:
    - search: búsqueda por nombre o SKU
    - category: filtrar por categoría
    - active: true/false (solo activos)
    - expiring_soon: días hasta vencimiento (ej: 7)
    - include_stock: true/false (incluir cantidades de lotes)
    - page: número de página (default: 1)
    - per_page: productos por página (default: 20, max: 100)
    
    Response:
    {
        "products": [...],
        "total": 50,
        "page": 1,
        "per_page": 20,
        "pages": 3
    }
    """
    try:
        # Parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Filtros
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        active_only = request.args.get('active', 'true').lower() == 'true'
        include_stock = request.args.get('include_stock', 'false').lower() == 'true'
        expiring_days = request.args.get('expiring_soon', type=int)
        
        session = db_postgres.get_session()
        try:
            # Query base
            query = session.query(Product)
            
            # Filtro: solo activos
            if active_only:
                query = query.filter(Product.active == True)
            
            # Filtro: búsqueda por nombre o SKU
            if search:
                query = query.filter(
                    or_(
                        Product.name.ilike(f'%{search}%'),
                        Product.sku.ilike(f'%{search}%'),
                        Product.description.ilike(f'%{search}%')
                    )
                )
            
            # Filtro: categoría
            if category:
                query = query.filter(Product.category == category)
            
            # Ordenar por nombre
            query = query.order_by(Product.name.asc())
            
            # Total de resultados
            total = query.count()
            
            # Paginación
            products_page = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convertir a dict
            products_data = []
            for product in products_page:
                product_dict = product.to_dict(include_batches=include_stock)
                
                # Calcular stock total si se solicitó
                if include_stock:
                    total_stock = sum(
                        batch['quantity'] 
                        for batch in product_dict.get('batches', [])
                        if batch['quantity'] > 0
                    )
                    product_dict['total_stock'] = total_stock
                    
                    # Si hay filtro de productos por vencer
                    if expiring_days:
                        expiry_threshold = date.today() + timedelta(days=expiring_days)
                        expiring_batches = [
                            batch for batch in product_dict.get('batches', [])
                            if batch.get('expiration_date') and 
                               date.fromisoformat(batch['expiration_date']) <= expiry_threshold
                        ]
                        
                        if expiring_batches:
                            product_dict['expiring_soon'] = True
                            product_dict['expiring_batches'] = expiring_batches
                
                products_data.append(product_dict)
            
            # Filtrar productos por vencer si se aplicó el filtro
            if expiring_days and include_stock:
                products_data = [p for p in products_data if p.get('expiring_soon')]
            
            # Calcular páginas
            pages = (total + per_page - 1) // per_page
            
            logger.info(f"Listado de productos: {len(products_data)} resultados (página {page}/{pages})")
            
            return jsonify({
                'products': products_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error listando productos: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar los productos'
        }), 500


@products_bp.route('/<int:product_id>', methods=['GET'])
@optional_token
def get_product(current_user, product_id):
    """
    Obtener un producto específico por ID
    
    Query params:
    - include_batches: true/false (incluir lotes)
    
    Response:
    {
        "product": {...}
    }
    """
    try:
        include_batches = request.args.get('include_batches', 'true').lower() == 'true'
        
        session = db_postgres.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            
            if not product:
                return jsonify({
                    'error': 'Producto no encontrado',
                    'message': f'No existe un producto con ID {product_id}'
                }), 404
            
            product_dict = product.to_dict(include_batches=include_batches)
            
            # Agregar stock total
            if include_batches:
                total_stock = sum(
                    batch['quantity'] 
                    for batch in product_dict.get('batches', [])
                )
                product_dict['total_stock'] = total_stock
            
            return jsonify({
                'product': product_dict
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo producto {product_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener el producto'
        }), 500


@products_bp.route('', methods=['POST'])
@token_required
@gerente_only
def create_product(current_user):
    """
    Crear nuevo producto (solo gerentes)
    
    Body:
    {
        "sku": "LAC-003",
        "name": "Leche Deslactosada 1L",
        "description": "Leche sin lactosa",
        "category": "Lácteos",
        "base_price": 28.50
    }
    
    Response:
    {
        "message": "Producto creado exitosamente",
        "product": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['sku', 'name', 'base_price']
        for field in required_fields:
            if not data or field not in data:
                return jsonify({
                    'error': 'Datos incompletos',
                    'message': f'El campo {field} es requerido'
                }), 400
        
        # Validar precio
        try:
            base_price = float(data['base_price'])
            if base_price <= 0:
                raise ValueError("El precio debe ser mayor a 0")
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': 'Precio inválido',
                'message': 'El precio debe ser un número mayor a 0'
            }), 400
        
        session = db_postgres.get_session()
        try:
            # Verificar que el SKU no exista
            existing = session.query(Product).filter_by(sku=data['sku']).first()
            if existing:
                return jsonify({
                    'error': 'SKU duplicado',
                    'message': f'Ya existe un producto con el SKU {data["sku"]}'
                }), 409
            
            # Crear producto
            new_product = Product(
                sku=data['sku'].strip().upper(),
                name=data['name'].strip(),
                description=data.get('description', '').strip(),
                category=data.get('category', '').strip(),
                base_price=base_price,
                active=data.get('active', True)
            )
            
            session.add(new_product)
            session.commit()
            session.refresh(new_product)
            
            logger.info(
                f"Producto creado: {new_product.sku} por {current_user['username']}"
            )
            
            return jsonify({
                'message': 'Producto creado exitosamente',
                'product': new_product.to_dict()
            }), 201
        
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Error de integridad al crear producto: {e}")
            return jsonify({
                'error': 'Error de integridad',
                'message': 'El SKU ya existe o hay un problema con los datos'
            }), 409
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error creando producto: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al crear el producto'
        }), 500


@products_bp.route('/<int:product_id>', methods=['PUT', 'PATCH'])
@token_required
@gerente_only
def update_product(current_user, product_id):
    """
    Actualizar producto existente (solo gerentes)
    
    Body (todos los campos son opcionales):
    {
        "name": "Nuevo nombre",
        "description": "Nueva descripción",
        "category": "Nueva categoría",
        "base_price": 30.00,
        "active": false
    }
    
    Response:
    {
        "message": "Producto actualizado",
        "product": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Datos vacíos',
                'message': 'Debes enviar al menos un campo para actualizar'
            }), 400
        
        session = db_postgres.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            
            if not product:
                return jsonify({
                    'error': 'Producto no encontrado',
                    'message': f'No existe un producto con ID {product_id}'
                }), 404
            
            # Actualizar campos permitidos
            if 'name' in data:
                product.name = data['name'].strip()
            
            if 'description' in data:
                product.description = data['description'].strip()
            
            if 'category' in data:
                product.category = data['category'].strip()
            
            if 'base_price' in data:
                try:
                    base_price = float(data['base_price'])
                    if base_price <= 0:
                        raise ValueError()
                    product.base_price = base_price
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Precio inválido',
                        'message': 'El precio debe ser un número mayor a 0'
                    }), 400
            
            if 'active' in data:
                product.active = bool(data['active'])
            
            # NO permitir actualizar SKU (usar endpoint específico si se necesita)
            
            session.commit()
            session.refresh(product)
            
            logger.info(
                f"Producto actualizado: {product.sku} por {current_user['username']}"
            )
            
            return jsonify({
                'message': 'Producto actualizado exitosamente',
                'product': product.to_dict()
            }), 200
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error actualizando producto {product_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al actualizar el producto'
        }), 500


@products_bp.route('/<int:product_id>', methods=['DELETE'])
@token_required
@gerente_only
def delete_product(current_user, product_id):
    """
    Eliminar producto (soft delete - marca como inactivo)
    Solo gerentes
    
    Query params:
    - hard_delete: true (eliminar permanentemente - PELIGROSO)
    
    Response:
    {
        "message": "Producto eliminado",
        "product_id": 123
    }
    """
    try:
        hard_delete = request.args.get('hard_delete', 'false').lower() == 'true'
        
        session = db_postgres.get_session()
        try:
            product = session.query(Product).filter_by(id=product_id).first()
            
            if not product:
                return jsonify({
                    'error': 'Producto no encontrado',
                    'message': f'No existe un producto con ID {product_id}'
                }), 404
            
            if hard_delete:
                # Verificar que no tenga stock
                total_stock = sum(batch.quantity for batch in product.batches)
                if total_stock > 0:
                    return jsonify({
                        'error': 'No se puede eliminar',
                        'message': 'El producto tiene stock. Primero debes ajustar el inventario a 0.'
                    }), 400
                
                sku = product.sku
                session.delete(product)
                session.commit()
                
                logger.warning(
                    f"Producto eliminado permanentemente: {sku} por {current_user['username']}"
                )
                
                return jsonify({
                    'message': 'Producto eliminado permanentemente',
                    'product_id': product_id
                }), 200
            
            else:
                # Soft delete
                product.active = False
                session.commit()
                
                logger.info(
                    f"Producto desactivado: {product.sku} por {current_user['username']}"
                )
                
                return jsonify({
                    'message': 'Producto desactivado exitosamente',
                    'product': product.to_dict()
                }), 200
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error eliminando producto {product_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al eliminar el producto'
        }), 500


@products_bp.route('/categories', methods=['GET'])
@optional_token
def list_categories(current_user):
    """
    Listar todas las categorías de productos
    
    Response:
    {
        "categories": [
            {"name": "Lácteos", "count": 5},
            {"name": "Bebidas", "count": 8}
        ]
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            # Obtener categorías con conteo
            categories = session.query(
                Product.category,
                func.count(Product.id).label('count')
            ).filter(
                Product.active == True,
                Product.category != None,
                Product.category != ''
            ).group_by(
                Product.category
            ).order_by(
                Product.category.asc()
            ).all()
            
            categories_data = [
                {'name': cat, 'count': count}
                for cat, count in categories
            ]
            
            return jsonify({
                'categories': categories_data,
                'total': len(categories_data)
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error listando categorías: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar las categorías'
        }), 500