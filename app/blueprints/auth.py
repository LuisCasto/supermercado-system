"""
Blueprint de Autenticación
Endpoints: login, registro, refresh token, me (perfil actual)
"""
from flask import Blueprint, request, jsonify
from app.models import User
from app.utils.db_postgres import db_postgres
from app.middleware.auth_middleware import token_required
from app.middleware.jwt_utils import generate_token, decode_token
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autenticar usuario y generar JWT token
    
    Body:
    {
        "username": "cajero1",
        "password": "password123"
    }
    
    Response:
    {
        "message": "Login exitoso",
        "token": "eyJ...",
        "user": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Datos incompletos',
                'message': 'Se requiere username y password'
            }), 400
        
        username = data['username']
        password = data['password']
        
        # Buscar usuario en la base de datos
        session = db_postgres.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            
            if not user:
                logger.warning(f"Intento de login con usuario inexistente: {username}")
                return jsonify({
                    'error': 'Credenciales inválidas',
                    'message': 'Usuario o contraseña incorrectos'
                }), 401
            
            # Verificar que el usuario esté activo
            if not user.active:
                logger.warning(f"Intento de login con usuario inactivo: {username}")
                return jsonify({
                    'error': 'Usuario inactivo',
                    'message': 'Tu cuenta ha sido desactivada. Contacta al administrador.'
                }), 403
            
            # Verificar contraseña
            if not user.check_password(password):
                logger.warning(f"Contraseña incorrecta para usuario: {username}")
                return jsonify({
                    'error': 'Credenciales inválidas',
                    'message': 'Usuario o contraseña incorrectos'
                }), 401
            
            # Generar token JWT
            token = generate_token(user)
            
            logger.info(f"Login exitoso: {username} ({user.role})")
            
            return jsonify({
                'message': 'Login exitoso',
                'token': token,
                'user': user.to_dict()
            }), 200
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al procesar el login'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registrar nuevo usuario (solo para testing/desarrollo)
    En producción, esto debería estar protegido y solo accesible por gerentes
    
    Body:
    {
        "username": "nuevo_cajero",
        "email": "nuevo@supermercado.com",
        "password": "password123",
        "role": "cajero"
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['username', 'email', 'password', 'role']
        for field in required_fields:
            if not data or not data.get(field):
                return jsonify({
                    'error': 'Datos incompletos',
                    'message': f'El campo {field} es requerido'
                }), 400
        
        # Validar rol
        valid_roles = ['gerente', 'inventario', 'cajero']
        if data['role'] not in valid_roles:
            return jsonify({
                'error': 'Rol inválido',
                'message': f'El rol debe ser uno de: {", ".join(valid_roles)}'
            }), 400
        
        session = db_postgres.get_session()
        try:
            # Verificar si el usuario ya existe
            existing_user = session.query(User).filter(
                (User.username == data['username']) | (User.email == data['email'])
            ).first()
            
            if existing_user:
                if existing_user.username == data['username']:
                    return jsonify({
                        'error': 'Usuario existente',
                        'message': 'El nombre de usuario ya está registrado'
                    }), 409
                else:
                    return jsonify({
                        'error': 'Email existente',
                        'message': 'El email ya está registrado'
                    }), 409
            
            # Crear nuevo usuario
            new_user = User(
                username=data['username'],
                email=data['email'],
                role=data['role'],
                active=True
            )
            new_user.set_password(data['password'])
            
            session.add(new_user)
            session.commit()
            
            logger.info(f"Usuario registrado: {new_user.username} ({new_user.role})")
            
            # Generar token para el nuevo usuario
            token = generate_token(new_user)
            
            return jsonify({
                'message': 'Usuario registrado exitosamente',
                'token': token,
                'user': new_user.to_dict()
            }), 201
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error en registro: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al registrar el usuario'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """
    Obtener información del usuario autenticado
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
    {
        "user": {
            "id": 1,
            "username": "cajero1",
            "role": "cajero",
            ...
        }
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            # Obtener datos completos del usuario desde la DB
            user = session.query(User).filter_by(id=current_user['id']).first()
            
            if not user:
                return jsonify({
                    'error': 'Usuario no encontrado',
                    'message': 'El usuario del token no existe en la base de datos'
                }), 404
            
            if not user.active:
                return jsonify({
                    'error': 'Usuario inactivo',
                    'message': 'Tu cuenta ha sido desactivada'
                }), 403
            
            return jsonify({
                'user': user.to_dict()
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo perfil: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al obtener el perfil'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@token_required
def refresh_token(current_user):
    """
    Refrescar token JWT (generar uno nuevo antes de que expire)
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
    {
        "message": "Token refrescado",
        "token": "eyJ..."
    }
    """
    try:
        session = db_postgres.get_session()
        try:
            # Obtener usuario actualizado
            user = session.query(User).filter_by(id=current_user['id']).first()
            
            if not user or not user.active:
                return jsonify({
                    'error': 'Usuario no válido',
                    'message': 'No se puede refrescar el token'
                }), 403
            
            # Generar nuevo token
            new_token = generate_token(user)
            
            logger.info(f"Token refrescado para: {user.username}")
            
            return jsonify({
                'message': 'Token refrescado exitosamente',
                'token': new_token
            }), 200
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error refrescando token: {e}")
        return jsonify({
            'error': 'Error interno',
            'message': 'Ocurrió un error al refrescar el token'
        }), 500


@auth_bp.route('/validate', methods=['GET'])
@token_required
def validate_token(current_user):
    """
    Validar si un token es válido (útil para frontends)
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
    {
        "valid": true,
        "user": {...}
    }
    """
    return jsonify({
        'valid': True,
        'user': current_user
    }), 200