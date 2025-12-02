"""
Modelos SQLAlchemy para PostgreSQL
"""
from app.utils.db_postgres import Base

# Importar todos los modelos
from .user import User
from .product import Product
from .product_batch import ProductBatch
from .inventory_movement import InventoryMovement
from .outbox_event import OutboxEvent

__all__ = [
    'Base',
    'User',
    'Product',
    'ProductBatch',
    'InventoryMovement',
    'OutboxEvent'
]