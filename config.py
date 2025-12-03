import os
from datetime import timedelta

class Config:
    """Configuración base de la aplicación"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # PostgreSQL (Fuente de la verdad)
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5433'))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'supermercado_db')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'app_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'apppass123')
    
    # URI de conexión para SQLAlchemy
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # MongoDB (Almacenamiento de tickets)
    MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
    MONGO_PORT = int(os.getenv('MONGO_PORT', '27018'))
    MONGO_DB = os.getenv('MONGO_DB', 'supermercado_sales')
    MONGO_USER = os.getenv('MONGO_USER', 'app_user')
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'apppass123')
    
    # URI de conexión para PyMongo
    MONGO_URI = (
        f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@"
        f"{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource={MONGO_DB}"
    )
    
    # Configuración del Worker Outbox
    OUTBOX_POLL_INTERVAL = 5
    OUTBOX_BATCH_SIZE = 10
    OUTBOX_MAX_RETRIES = 3
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def init_app(app):
        """Inicialización adicional de la app"""
        pass


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log a archivo en producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        os.makedirs('logs', exist_ok=True)
        
        file_handler = RotatingFileHandler(
            'logs/supermercado.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class TestingConfig(Config):
    """Configuración para tests"""
    TESTING = True
    
    # ✅ SQLite con archivo temporal (compartido entre threads)
    import tempfile
    import os as _os
    _test_db = _os.path.join(tempfile.gettempdir(), 'test_supermercado.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{_test_db}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # ✅ MongoDB: USAR LA MISMA BASE (con limpieza en tests)
    # Esto evita problemas de permisos
    MONGO_DB = 'supermercado_sales_test'  # ← Misma base que desarrollo
    MONGO_URI = (
        f"mongodb://{Config.MONGO_USER}:{Config.MONGO_PASSWORD}@"
        f"{Config.MONGO_HOST}:{Config.MONGO_PORT}/{MONGO_DB}?authSource={MONGO_DB}"
    )
    
    # Worker más rápido para tests
    OUTBOX_POLL_INTERVAL = 2
    OUTBOX_BATCH_SIZE = 5
    OUTBOX_MAX_RETRIES = 3


# Diccionario de configuraciones
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}