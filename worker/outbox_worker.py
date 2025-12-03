"""
Worker Integrado del Outbox Pattern
Se ejecuta como thread en la misma aplicación Flask

Procesa eventos PENDING de outbox_events y los sincroniza con MongoDB
"""
import threading
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OutboxWorker:
    """
    Worker que procesa eventos del outbox en background
    """
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
        self.poll_interval = app.config.get('OUTBOX_POLL_INTERVAL', 5)  # segundos
        self.batch_size = app.config.get('OUTBOX_BATCH_SIZE', 10)
        self.max_retries = app.config.get('OUTBOX_MAX_RETRIES', 3)
    
    def start(self):
        """Iniciar el worker en un thread separado"""
        if self.running:
            logger.warning("El worker ya está en ejecución")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"✓ Outbox Worker iniciado (intervalo: {self.poll_interval}s)")
    
    def stop(self):
        """Detener el worker"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("✓ Outbox Worker detenido")
    
    def _run(self):
        """Loop principal del worker"""
        logger.info("🔄 Outbox Worker ejecutándose en background...")
        
        while self.running:
            try:
                with self.app.app_context():
                    self._process_batch()
            except Exception as e:
                logger.error(f"Error en worker loop: {e}", exc_info=True)
            
            # Esperar antes del siguiente ciclo
            time.sleep(self.poll_interval)
    
    def _process_batch(self):
        """Procesar un lote de eventos pendientes"""
        from app.utils.db_postgres import db_postgres
        from app.utils.db_mongo import db_mongo
        from app.models import OutboxEvent
        
        session = db_postgres.get_session()
        
        try:
            # Obtener eventos pendientes o que fallaron con retries disponibles
            events = session.query(OutboxEvent).filter(
                (OutboxEvent.status == 'PENDING') | 
                (
                    (OutboxEvent.status == 'FAILED') & 
                    (OutboxEvent.retry_count < self.max_retries)
                )
            ).order_by(
                OutboxEvent.created_at.asc()
            ).limit(self.batch_size).all()
            
            if not events:
                return  # No hay eventos pendientes
            
            logger.info(f"📦 Procesando {len(events)} eventos del outbox...")
            
            mongo_db = db_mongo.get_db()
            sales_collection = mongo_db['sales_tickets']
            
            for event in events:
                try:
                    # Marcar como procesando
                    event.status = 'PROCESSING'
                    session.commit()
                    
                    # Procesar según tipo de evento
                    if event.event_type == 'SALE_CREATED':
                        self._process_sale_event(event, sales_collection, session)
                    else:
                        logger.warning(f"Tipo de evento no soportado: {event.event_type}")
                        event.status = 'FAILED'
                        event.error_message = f"Tipo de evento no soportado: {event.event_type}"
                        event.retry_count += 1
                        session.commit()
                
                except Exception as e:
                    logger.error(f"Error procesando evento {event.id}: {e}")
                    event.status = 'FAILED'
                    event.error_message = str(e)[:500]  # Limitar longitud
                    event.retry_count += 1
                    session.commit()
        
        except Exception as e:
            logger.error(f"Error crítico en batch processing: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()
    
    def _process_sale_event(self, event, sales_collection, session):
        """
        Procesar evento de venta: crear ticket en MongoDB
        
        Implementa idempotencia: si el ticket ya existe, no lo crea de nuevo
        """
        try:
            # Verificar idempotencia: ¿ya existe este ticket?
            existing = sales_collection.find_one({'sale_id': event.aggregate_id})
            
            if existing:
                logger.info(f"  ⚠ Ticket ya existe en MongoDB: {event.aggregate_id} (idempotente)")
                event.status = 'COMPLETED'
                event.processed_at = datetime.utcnow()
                session.commit()
                return
            
            # Preparar documento para MongoDB
            ticket_doc = event.payload.copy()
            
            # Convertir timestamp string a datetime si es necesario
            if isinstance(ticket_doc.get('timestamp'), str):
                try:
                    # Intentar parsear ISO format
                    timestamp_str = ticket_doc['timestamp'].replace('Z', '+00:00')
                    ticket_doc['timestamp'] = datetime.fromisoformat(timestamp_str)
                except (ValueError, AttributeError):
                    # Si falla, usar fecha actual
                    ticket_doc['timestamp'] = datetime.utcnow()
            
            # Agregar metadata de creación
            ticket_doc['created_at'] = datetime.utcnow()
            ticket_doc['synced_from_outbox'] = True
            ticket_doc['outbox_event_id'] = event.id
            
            # Insertar en MongoDB
            result = sales_collection.insert_one(ticket_doc)
            
            logger.info(
                f"  ✓ Ticket creado en MongoDB: {event.aggregate_id} "
                f"(MongoDB _id: {result.inserted_id})"
            )
            
            # Marcar evento como completado
            event.status = 'COMPLETED'
            event.processed_at = datetime.utcnow()
            event.error_message = None  # Limpiar errores previos
            session.commit()
        
        except Exception as e:
            logger.error(f"  ✗ Error creando ticket en MongoDB: {e}")
            raise  # Re-lanzar para que el handler principal lo maneje


# Instancia global del worker
_worker_instance = None


def init_worker(app):
    """
    Inicializar y arrancar el worker
    Llamar desde el factory de la app
    """
    global _worker_instance
    
    if _worker_instance is not None:
        logger.warning("Worker ya fue inicializado")
        return _worker_instance
    
    _worker_instance = OutboxWorker(app)
    _worker_instance.start()
    
    return _worker_instance


def get_worker():
    """Obtener la instancia del worker"""
    return _worker_instance


def stop_worker():
    """Detener el worker (útil para testing o shutdown)"""
    global _worker_instance
    if _worker_instance:
        _worker_instance.stop()
        _worker_instance = None