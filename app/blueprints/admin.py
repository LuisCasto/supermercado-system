from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/test', methods=['GET'])
def test():
    return {'message': 'Admin blueprint working'}, 200