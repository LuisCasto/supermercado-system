from flask import Blueprint

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/test', methods=['GET'])
def test():
    return {'message': 'Sales blueprint working'}, 200