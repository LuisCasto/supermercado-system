"""
Factory de la aplicación Flask
"""
from flask import Flask
from flask_cors import CORS
import logging

from config import config
from app.utils.logger import setup_logger
from app.utils.db_postgres import db_postgres
from app.utils.db_mongo import db_mongo

logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """
    Factory para crear la aplicación Flask
    
    Args:
        config_name: Nombre de la configuración ('development', 'production', 'testing')
    
    Returns:
        Aplicación Flask configurada
    """
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Configurar logging
    setup_logger(app)
    logger.info(f"Iniciando aplicación en modo: {config_name}")
    
    # Configurar CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Inicializar conexiones a bases de datos
    db_postgres.init_app(app)
    db_mongo.init_app(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar manejadores de errores
    register_error_handlers(app)
    
    # Inicializar Outbox Worker (solo si no estamos en testing)
    if not app.config.get('TESTING'):
        from worker.outbox_worker import init_worker
        init_worker(app)
        logger.info("✓ Outbox Worker inicializado")
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Endpoint para verificar que la app está funcionando"""
        return {
            'status': 'healthy',
            'service': 'supermercado-api',
            'version': '1.0.0'
        }, 200
    
    logger.info("✓ Aplicación Flask inicializada correctamente")
    
    return app


def register_blueprints(app):
    """Registrar todos los blueprints de la aplicación"""
    
    from app.blueprints.auth import auth_bp
    from app.blueprints.products import products_bp
    from app.blueprints.inventory import inventory_bp
    from app.blueprints.sales import sales_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(inventory_bp, url_prefix='/api/inventory')
    app.register_blueprint(sales_bp, url_prefix='/api/sales')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    logger.info("✓ Blueprints registrados")


def register_error_handlers(app):
    """Registrar manejadores de errores personalizados"""
    
    from flask import jsonify
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Credenciales inválidas o token expirado'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'error': 'Forbidden',
            'message': 'No tienes permisos para realizar esta acción'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'Recurso no encontrado'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Error interno del servidor: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Ocurrió un error interno. Por favor contacta al administrador.'
        }), 500
    
    logger.info("✓ Manejadores de errores registrados")