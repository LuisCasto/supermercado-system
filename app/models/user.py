"""
Modelo User - Usuarios del sistema
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.sql import func
from app.utils.db_postgres import Base
import bcrypt


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('gerente', 'inventario', 'cajero')",
            name='check_user_role'
        ),
    )
    
    def set_password(self, password):
        """Hashear y guardar password"""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.hashed_password = hashed.decode('utf-8')
    
    def check_password(self, password):
        """Verificar password"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.hashed_password.encode('utf-8')
        )
    
    def to_dict(self):
        """Convertir a diccionario (sin password)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"