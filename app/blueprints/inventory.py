from flask import Blueprint

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/test', methods=['GET'])
def test():
    return {'message': 'Inventory blueprint working'}, 200