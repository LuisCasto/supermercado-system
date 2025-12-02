"""
Middleware de RBAC (Role-Based Access Control)
"""
from functools import wraps
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def role_required(*allowed_roles):
    """
    Decorador para restringir acceso por roles
    
    Uso:
        @token_required
        @role_required('gerente', 'inventario')
        def admin_route(current_user):
            return {'message': 'Solo gerentes e inventario'}
    
    Args:
        allowed_roles: Roles permitidos ('gerente', 'inventario', 'cajero')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(current_user, *args, **kwargs):
            # Verificar que el usuario tenga uno de los roles permitidos
            if current_user['role'] not in allowed_roles:
                logger.warning(
                    f"Acceso denegado: {current_user['username']} ({current_user['role']}) "
                    f"intentó acceder a recurso que requiere roles: {allowed_roles}"
                )
                return jsonify({
                    'error': 'Acceso denegado',
                    'message': f'Esta acción requiere el rol: {", ".join(allowed_roles)}',
                    'required_roles': list(allowed_roles),
                    'your_role': current_user['role']
                }), 403
            
            logger.info(
                f"Acceso autorizado: {current_user['username']} ({current_user['role']}) "
                f"a recurso que requiere: {allowed_roles}"
            )
            
            return f(current_user, *args, **kwargs)
        
        return decorated_function
    
    return decorator


# Decoradores de conveniencia para roles específicos
def gerente_only(f):
    """Solo gerentes"""
    return role_required('gerente')(f)


def inventario_or_gerente(f):
    """Gerentes o personal de inventario"""
    return role_required('gerente', 'inventario')(f)


def cajero_or_gerente(f):
    """Cajeros o gerentes"""
    return role_required('gerente', 'cajero')(f)