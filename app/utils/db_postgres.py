"""
Utilidad para conexión a PostgreSQL usando SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Base para los modelos SQLAlchemy
Base = declarative_base()

class PostgresDB:
    """Gestor de conexión a PostgreSQL"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.Session = None
    
    def init_app(self, app):
        """Inicializar con la aplicación Flask"""
        database_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Detectar si es SQLite (para testing)
        is_sqlite = database_uri.startswith('sqlite')
        
        # Configuración base del engine
        engine_config = {
            'echo': app.config.get('SQLALCHEMY_ECHO', False)
        }
        
        # Solo agregar opciones de pool si NO es SQLite
        if not is_sqlite:
            engine_config.update({
                'pool_size': 10,
                'max_overflow': 20,
                'pool_pre_ping': True,  # Verificar conexiones antes de usar
            })
        
        # Crear engine
        self.engine = create_engine(database_uri, **engine_config)
        
        # Session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        logger.info(f"✓ Conectado a base de datos: {database_uri.split('@')[-1] if '@' in database_uri else 'SQLite'}")
    
    def get_session(self):
        """Obtener una sesión de SQLAlchemy"""
        return self.Session()
    
    @contextmanager
    def session_scope(self):
        """Context manager para sesiones con auto-commit/rollback"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en transacción: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Cerrar conexiones"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
            logger.info("✓ Conexión a base de datos cerrada")


# Instancia global
db_postgres = PostgresDB()