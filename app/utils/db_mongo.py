"""
Utilidad para conexión a MongoDB usando PyMongo
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    """Gestor de conexión a MongoDB"""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    def init_app(self, app):
        """Inicializar con la aplicación Flask"""
        mongo_uri = app.config['MONGO_URI']
        mongo_db_name = app.config['MONGO_DB']
        
        try:
            # Crear cliente con configuraciones de producción
            self.client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=50
            )
            
            # Verificar conexión
            self.client.admin.command('ping')
            
            # Seleccionar base de datos
            self.db = self.client[mongo_db_name]
            
            logger.info(f"✓ Conectado a MongoDB: {app.config['MONGO_HOST']}:{app.config['MONGO_PORT']}")
            
        except ConnectionFailure as e:
            logger.error(f"✗ Error conectando a MongoDB: {e}")
            raise
    
    def get_db(self):
        """Obtener referencia a la base de datos"""
        return self.db
    
    def get_collection(self, collection_name):
        """Obtener una colección específica"""
        return self.db[collection_name]
    
    def close(self):
        """Cerrar conexión"""
        if self.client:
            self.client.close()
            logger.info("✓ Conexión a MongoDB cerrada")


# Instancia global
db_mongo = MongoDB()