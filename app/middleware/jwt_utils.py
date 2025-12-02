"""
Utilidades para manejo de JWT tokens
"""
import jwt
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)


def generate_token(user):
    """
    Generar JWT token para un usuario
    
    Args:
        user: Objeto User de SQLAlchemy o dict con id, username, role
    
    Returns:
        str: Token JWT
    """
    try:
        # Obtener datos del usuario
        if hasattr(user, 'id'):
            # Es un objeto User de SQLAlchemy
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'role': user.role
            }
        else:
            # Es un dict
            user_data = {
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        
        # Calcular expiración
        expiration = datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        
        # Payload del token
        payload = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'role': user_data['role'],
            'iat': datetime.utcnow(),  # Issued at
            'exp': expiration  # Expiration
        }
        
        # Generar token
        token = jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        logger.info(f"Token generado para usuario: {user_data['username']}")
        
        return token
    
    except Exception as e:
        logger.error(f"Error al generar token: {e}")
        raise


def decode_token(token):
    """
    Decodificar y validar un JWT token
    
    Args:
        token: Token JWT como string
    
    Returns:
        dict: Payload del token
    
    Raises:
        jwt.ExpiredSignatureError: Token expirado
        jwt.InvalidTokenError: Token inválido
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Intento de uso de token expirado")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {e}")
        raise


def refresh_token(old_token):
    """
    Generar un nuevo token a partir de uno existente (si no ha expirado)
    
    Args:
        old_token: Token JWT existente
    
    Returns:
        str: Nuevo token JWT
    """
    try:
        # Decodificar token viejo
        payload = decode_token(old_token)
        
        # Crear nuevo token con datos actuales
        user_data = {
            'id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role']
        }
        
        return generate_token(user_data)
    
    except Exception as e:
        logger.error(f"Error al refrescar token: {e}")
        raise