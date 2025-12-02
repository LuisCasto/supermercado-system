"""
Configuración de logging estructurado para la aplicación
"""
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(app):
    """Configurar logger para la aplicación"""
    
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    
    # Formato JSON para logs estructurados
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logHandler.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(logHandler)
    
    # Logger específico de la app
    app.logger.setLevel(log_level)
    app.logger.addHandler(logHandler)
    
    # Desactivar logs de werkzeug en producción
    if not app.config.get('DEBUG'):
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.logger.info("✓ Sistema de logging configurado", extra={
        'log_level': app.config.get('LOG_LEVEL'),
        'environment': app.config.get('FLASK_ENV', 'production')
    })