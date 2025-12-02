"""
Modelo OutboxEvent - Patrón Outbox para consistencia eventual
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.utils.db_postgres import Base


class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    aggregate_id = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name='check_outbox_status'
        ),
        Index('idx_outbox_status_created', 'status', 'created_at'),
    )
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'aggregate_id': self.aggregate_id,
            'payload': self.payload,
            'status': self.status,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    def mark_processing(self):
        """Marcar como en procesamiento"""
        self.status = 'PROCESSING'
    
    def mark_completed(self):
        """Marcar como completado"""
        self.status = 'COMPLETED'
        self.processed_at = func.now()
    
    def mark_failed(self, error_msg):
        """Marcar como fallido"""
        self.status = 'FAILED'
        self.retry_count += 1
        self.error_message = error_msg
    
    def __repr__(self):
        return f"<OutboxEvent {self.event_type} - {self.status}>"