"""
Blueprint de Administración
Endpoints: métricas, outbox stats, health checks
RBAC: Solo gerentes
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from app.models import OutboxEvent, InventoryMovement, User, Product, ProductBatch
from app.utils.db_postgres import db_postgres
from app.utils.db_mongo import db_mongo
from app.middleware.auth_middleware import token_required
from app.middleware.rbac_middleware import gerente_only
from worker.outbox_worker import get_worker
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check completo del sistema
    No requiere autenticación (útil para load balancers)
    
    Response:
    {
        "status": "healthy",
        "databases": {...},
        "worker": {...}
    }
    """
    try:
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'databases': {},
            'worker': {}
        }
        
        # Check PostgreSQL
        try:
            session = db_postgres.get_session()
            session.execute('SELECT 1')
            session.close()
            health['databases']['postgresql'] = 'connected'
        except Exception as e:
            health['databases']['postgresql'] = f'error: {str(e)}'
            health['status'] = 'degraded'
        
        # Check MongoDB
        try:
            mongo_db = db_mongo.get_db()
            mongo_db.command('ping')
            health['databases']['mongodb'] = 'connected'
        except Exception as e:
            health['databases']['mongodb'] = f'error: {str(e)}'
            health['status'] = 'degraded'
        
        # Check Worker
        worker = get_worker()
        if worker and worker.running:
            health['worker']['status'] = 'running'
            health['worker']['poll_interval'] = worker.poll_interval
        else:
            health['worker']['status'] = 'stopped'
            health['status'] = 'degraded'
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return jsonify(health), status_code
    
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@admin_bp.route('/outbox/stats', methods=['GET'])
@token_required
@gerente_only
def outbox_stats(current_user):
    """
    Estadísticas del outbox
    Solo gerentes
    
    Response:
    {
        "pending": 5,
        "processing": 0,
        "completed": 120,
        "failed": 2,
        "total": 127,
        "oldest_pending": "2025-12-02T10:30:00",
        "recent_failures": [...]
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            # Contar por estado
            stats = {}
            for status in ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']:
                count = session.query(OutboxEvent).filter_by(status=status).count()
                stats[status.lower()] = count
            
            stats['total'] = session.query(OutboxEvent).count()
            
            # Evento pendiente más antiguo
            oldest_pending = session.query(OutboxEvent).filter_by(
                status='PENDING'
            ).order_by(OutboxEvent.created_at.asc()).first()
            
            if oldest_pending:
                stats['oldest_pending'] = oldest_pending.created_at.isoformat()
                stats['oldest_pending_age_seconds'] = (
                    datetime.utcnow() - oldest_pending.created_at
                ).total_seconds()
            else:
                stats['oldest_pending'] = None
            
            # Fallos recientes (últimas 24 horas)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_failures = session.query(OutboxEvent).filter(
                and_(
                    OutboxEvent.status == 'FAILED',
                    OutboxEvent.created_at >= yesterday
                )
            ).order_by(OutboxEvent.created_at.desc()).limit(10).all()
            
            stats['recent_failures'] = [
                {
                    'id': e.id,
                    'event_type': e.event_type,
                    'aggregate_id': e.aggregate_id,
                    'error_message': e.error_message,
                    'retry_count': e.retry_count,
                    'created_at': e.created_at.isoformat()
                }
                for e in recent_failures
            ]
            
            return jsonify(stats), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo stats del outbox: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener las estadísticas'
        }), 500


@admin_bp.route('/outbox/events', methods=['GET'])
@token_required
@gerente_only
def list_outbox_events(current_user):
    """
    Listar eventos del outbox
    Solo gerentes
    
    Query params:
    - status: PENDING, PROCESSING, COMPLETED, FAILED
    - page, per_page: paginación
    
    Response:
    {
        "events": [...],
        "total": 50,
        "page": 1,
        "pages": 5
    }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        
        session = db_postgres.get_session()
        try:
            query = session.query(OutboxEvent)
            
            if status:
                query = query.filter(OutboxEvent.status == status.upper())
            
            query = query.order_by(OutboxEvent.created_at.desc())
            
            total = query.count()
            events = query.offset((page - 1) * per_page).limit(per_page).all()
            
            pages = (total + per_page - 1) // per_page
            
            return jsonify({
                'events': [e.to_dict() for e in events],
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': pages
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error listando eventos del outbox: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al listar los eventos'
        }), 500


@admin_bp.route('/outbox/retry/<int:event_id>', methods=['POST'])
@token_required
@gerente_only
def retry_failed_event(current_user, event_id):
    """
    Reintentar un evento fallido manualmente
    Solo gerentes
    
    Response:
    {
        "message": "Evento marcado para reintento",
        "event_id": 123
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            event = session.query(OutboxEvent).filter_by(id=event_id).first()
            
            if not event:
                return jsonify({
                    'error': 'Evento no encontrado',
                    'message': f'No existe un evento con ID {event_id}'
                }), 404
            
            if event.status not in ['FAILED', 'COMPLETED']:
                return jsonify({
                    'error': 'Estado inválido',
                    'message': f'Solo se pueden reintentar eventos FAILED (estado actual: {event.status})'
                }), 400
            
            # Resetear estado
            event.status = 'PENDING'
            event.error_message = None
            session.commit()
            
            logger.info(f"Evento {event_id} marcado para reintento por {current_user['username']}")
            
            return jsonify({
                'message': 'Evento marcado para reintento',
                'event_id': event_id,
                'note': 'El worker lo procesará en el próximo ciclo'
            }), 200
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error reintentando evento {event_id}: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al reintentar el evento'
        }), 500

@admin_bp.route('/outbox/process-now', methods=['POST'])
@token_required
@gerente_only
def process_outbox_now(current_user):
    """
    Procesar eventos del outbox manualmente
    Solo gerentes - Útil para debugging
    """
    try:
        from worker.outbox_worker import OutboxWorker
        from flask import current_app
        
        worker = OutboxWorker(current_app._get_current_object())
        
        with current_app.app_context():
            worker._process_batch()
        
        logger.info(f"Procesamiento manual del outbox por {current_user['username']}")
        
        return jsonify({
            'message': 'Eventos procesados exitosamente',
            'note': 'Revisa los logs para ver los detalles'
        }), 200
    
    except Exception as e:
        logger.error(f"Error procesando outbox manualmente: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': str(e)
        }), 500
    
@admin_bp.route('/metrics', methods=['GET'])
@token_required
@gerente_only
def system_metrics(current_user):
    """
    Métricas generales del sistema
    Solo gerentes
    
    Response:
    {
        "products": {...},
        "inventory": {...},
        "sales": {...},
        "outbox": {...}
    }
    """
    try:
        session = db_postgres.get_session()
        mongo_db = db_mongo.get_db()
        
        try:
            metrics = {}
            
            # Productos
            metrics['products'] = {
                'total': session.query(Product).count(),
                'active': session.query(Product).filter_by(active=True).count(),
                'inactive': session.query(Product).filter_by(active=False).count()
            }
            
            # Inventario
            total_batches = session.query(ProductBatch).count()
            batches_with_stock = session.query(ProductBatch).filter(
                ProductBatch.quantity > 0
            ).count()
            
            metrics['inventory'] = {
                'total_batches': total_batches,
                'batches_with_stock': batches_with_stock,
                'total_movements': session.query(InventoryMovement).count()
            }
            
            # Ventas (desde MongoDB)
            sales_collection = mongo_db['sales_tickets']
            total_sales = sales_collection.count_documents({})
            
            # Calcular total vendido
            pipeline = [
                {'$group': {
                    '_id': None,
                    'total_amount': {'$sum': '$grand_total'}
                }}
            ]
            sales_total = list(sales_collection.aggregate(pipeline))
            total_amount = sales_total[0]['total_amount'] if sales_total else 0
            
            metrics['sales'] = {
                'total_tickets': total_sales,
                'total_amount': round(total_amount, 2)
            }
            
            # Outbox
            metrics['outbox'] = {
                'pending': session.query(OutboxEvent).filter_by(status='PENDING').count(),
                'failed': session.query(OutboxEvent).filter_by(status='FAILED').count(),
                'completed': session.query(OutboxEvent).filter_by(status='COMPLETED').count()
            }
            
            # Usuarios
            metrics['users'] = {
                'total': session.query(User).count(),
                'active': session.query(User).filter_by(active=True).count()
            }
            
            return jsonify({
                'metrics': metrics,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener las métricas'
        }), 500


@admin_bp.route('/backup/postgres', methods=['POST'])
@token_required
@gerente_only
def trigger_postgres_backup(current_user):
    """
    Ejecutar backup de PostgreSQL manualmente
    Solo gerentes
    """
    import subprocess
    import os
    
    try:
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_postgres.sh')
        
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'Script no encontrado',
                'message': f'No se encontró el script en: {script_path}'
            }), 404
        
        logger.info(f"Backup PostgreSQL iniciado por {current_user['username']}")
        
        # Ejecutar script en background
        result = subprocess.run(
            ['bash', script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo
        )
        
        if result.returncode == 0:
            return jsonify({
                'message': 'Backup de PostgreSQL completado exitosamente',
                'output': result.stdout,
                'triggered_by': current_user['username']
            }), 200
        else:
            return jsonify({
                'error': 'Error en backup',
                'message': 'El script falló',
                'output': result.stderr
            }), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Timeout',
            'message': 'El backup tardó más de 5 minutos'
        }), 500
    except Exception as e:
        logger.error(f"Error ejecutando backup PostgreSQL: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': str(e)
        }), 500


@admin_bp.route('/backup/mongodb', methods=['POST'])
@token_required
@gerente_only
def trigger_mongo_backup(current_user):
    """
    Ejecutar backup de MongoDB manualmente
    Solo gerentes
    """
    import subprocess
    import os
    
    try:
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_mongo.sh')
        
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'Script no encontrado',
                'message': f'No se encontró el script en: {script_path}'
            }), 404
        
        logger.info(f"Backup MongoDB iniciado por {current_user['username']}")
        
        result = subprocess.run(
            ['bash', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return jsonify({
                'message': 'Backup de MongoDB completado exitosamente',
                'output': result.stdout,
                'triggered_by': current_user['username']
            }), 200
        else:
            return jsonify({
                'error': 'Error en backup',
                'message': 'El script falló',
                'output': result.stderr
            }), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Timeout',
            'message': 'El backup tardó más de 5 minutos'
        }), 500
    except Exception as e:
        logger.error(f"Error ejecutando backup MongoDB: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': str(e)
        }), 500


@admin_bp.route('/backup/all', methods=['POST'])
@token_required
@gerente_only
def trigger_full_backup(current_user):
    """
    Ejecutar backup completo (PostgreSQL + MongoDB)
    Solo gerentes
    """
    import subprocess
    import os
    
    try:
        script_path = os.path.join(os.getcwd(), 'scripts', 'backup_all.sh')
        
        if not os.path.exists(script_path):
            return jsonify({
                'error': 'Script no encontrado',
                'message': f'No se encontró el script en: {script_path}'
            }), 404
        
        logger.info(f"Backup completo iniciado por {current_user['username']}")
        
        result = subprocess.run(
            ['bash', script_path],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos para backup completo
        )
        
        if result.returncode == 0:
            return jsonify({
                'message': 'Backup completo exitoso (PostgreSQL + MongoDB)',
                'output': result.stdout,
                'triggered_by': current_user['username']
            }), 200
        else:
            return jsonify({
                'error': 'Error en backup',
                'message': 'El script falló',
                'output': result.stderr
            }), 500
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Timeout',
            'message': 'El backup tardó más de 10 minutos'
        }), 500
    except Exception as e:
        logger.error(f"Error ejecutando backup completo: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': str(e)
        }), 500