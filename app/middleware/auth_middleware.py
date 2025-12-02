"""
Middleware de autenticación con JWT
"""
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def token_required(f):
    """
    Decorador para rutas que requieren autenticación
    
    Uso:
        @token_required
        def protected_route(current_user):
            return {'message': f'Hello {current_user["username"]}'}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Obtener token del header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Formato esperado: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'error': 'Token inválido',
                    'message': 'Formato de Authorization header incorrecto. Use: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'error': 'Token no proporcionado',
                'message': 'Se requiere autenticación para acceder a este recurso'
            }), 401
        
        try:
            # Decodificar token
            data = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Verificar expiración
            if datetime.utcnow().timestamp() > data['exp']:
                return jsonify({
                    'error': 'Token expirado',
                    'message': 'El token ha expirado. Por favor inicia sesión nuevamente.'
                }), 401
            
            # Pasar datos del usuario a la función
            current_user = {
                'id': data['user_id'],
                'username': data['username'],
                'role': data['role']
            }
            
            logger.info(f"Usuario autenticado: {current_user['username']} ({current_user['role']})")
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expirado',
                'message': 'El token ha expirado. Por favor inicia sesión nuevamente.'
            }), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {e}")
            return jsonify({
                'error': 'Token inválido',
                'message': 'El token proporcionado no es válido'
            }), 401
        except Exception as e:
            logger.error(f"Error al verificar token: {e}")
            return jsonify({
                'error': 'Error de autenticación',
                'message': 'Ocurrió un error al verificar el token'
            }), 500
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def optional_token(f):
    """
    Decorador para rutas con autenticación opcional
    Si hay token válido, pasa current_user; si no, pasa None
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
                data = jwt.decode(
                    token,
                    current_app.config['JWT_SECRET_KEY'],
                    algorithms=['HS256']
                )
                
                if datetime.utcnow().timestamp() <= data['exp']:
                    current_user = {
                        'id': data['user_id'],
                        'username': data['username'],
                        'role': data['role']
                    }
            except:
                pass  # Token inválido o expirado, continuar sin usuario
        
        return f(current_user, *args, **kwargs)
    
    return decorated