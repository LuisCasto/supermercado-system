"""
Modelo Product - Productos del catálogo
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_postgres import Base


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    batches = relationship('ProductBatch', back_populates='product', lazy='dynamic')
    
    def to_dict(self, include_batches=False):
        """Convertir a diccionario"""
        result = {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'base_price': float(self.base_price),
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_batches:
            result['batches'] = [batch.to_dict() for batch in self.batches.all()]
        
        return result
    
    def get_total_stock(self):
        """Obtener stock total de todos los lotes"""
        return sum(batch.quantity for batch in self.batches.filter_by(quantity__gt=0).all())
    
    def __repr__(self):
        return f"<Product {self.sku}: {self.name}>"