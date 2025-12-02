"""
Modelo ProductBatch - Lotes de productos con fecha de expiración
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_postgres import Base


class ProductBatch(Base):
    __tablename__ = 'product_batches'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_code = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    cost_per_unit = Column(Numeric(10, 2), nullable=False)
    expiration_date = Column(Date)
    received_date = Column(Date, nullable=False, server_default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    product = relationship('Product', back_populates='batches')
    movements = relationship('InventoryMovement', back_populates='batch', lazy='dynamic')
    
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='check_batch_quantity_positive'),
        CheckConstraint('cost_per_unit > 0', name='check_batch_cost_positive'),
        UniqueConstraint('product_id', 'batch_code', name='uq_product_batch'),
    )
    
    def to_dict(self, include_product=False):
        """Convertir a diccionario"""
        result = {
            'id': self.id,
            'product_id': self.product_id,
            'batch_code': self.batch_code,
            'quantity': self.quantity,
            'cost_per_unit': float(self.cost_per_unit),
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_product and self.product:
            result['product'] = self.product.to_dict()
        
        return result
    
    def is_expired(self):
        """Verificar si el lote está expirado"""
        if not self.expiration_date:
            return False
        from datetime import date
        return self.expiration_date < date.today()
    
    def __repr__(self):
        return f"<ProductBatch {self.batch_code} - Qty: {self.quantity}>"