from flask import Blueprint

products_bp = Blueprint('products', __name__)

@products_bp.route('/test', methods=['GET'])
def test():
    return {'message': 'Products blueprint working'}, 200