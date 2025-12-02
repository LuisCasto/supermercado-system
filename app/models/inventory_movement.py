"""
Modelo InventoryMovement - Auditoría de movimientos de inventario
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.utils.db_postgres import Base


class InventoryMovement(Base):
    __tablename__ = 'inventory_movements'
    
    id = Column(Integer, primary_key=True)
    product_batch_id = Column(Integer, ForeignKey('product_batches.id', ondelete='CASCADE'), nullable=False, index=True)
    movement_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    reference_id = Column(String(100), index=True)
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relaciones
    batch = relationship('ProductBatch', back_populates='movements')
    user = relationship('User')
    
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('ENTRY', 'SALE', 'ADJUSTMENT', 'EXPIRATION')",
            name='check_movement_type'
        ),
    )
    
    def to_dict(self, include_relations=False):
        """Convertir a diccionario"""
        result = {
            'id': self.id,
            'product_batch_id': self.product_batch_id,
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'user_id': self.user_id,
            'reference_id': self.reference_id,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_relations:
            if self.batch:
                result['batch'] = self.batch.to_dict(include_product=True)
            if self.user:
                result['user'] = self.user.to_dict()
        
        return result
    
    def __repr__(self):
        return f"<InventoryMovement {self.movement_type} - Qty: {self.quantity}>"