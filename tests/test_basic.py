"""
Tests básicos del sistema
pytest tests/test_basic.py -v
"""
import pytest
from sqlalchemy import text
from app import create_app
from app.utils.db_postgres import db_postgres, Base
from app.utils.db_mongo import db_mongo
from app.models import User, Product, ProductBatch


@pytest.fixture(scope='module')
def app():
    """Crear app de testing"""
    app = create_app('testing')
    
    with app.app_context():
        # Crear todas las tablas
        Base.metadata.create_all(bind=db_postgres.engine)
        
        yield app
        
        # Limpiar Postgres
        Base.metadata.drop_all(bind=db_postgres.engine)
        
        # Limpiar MongoDB (con manejo de errores)
        try:
            mongo_db = db_mongo.get_db()
            mongo_db['sales_tickets'].delete_many({})
        except Exception as e:
            print(f"Warning: No se pudo limpiar MongoDB: {e}")


@pytest.fixture
def client(app):
    """Cliente de testing"""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Limpiar base de datos antes de cada test"""
    with app.app_context():
        session = db_postgres.get_session()
        try:
            # Usar text() para compatibilidad con SQLite
            session.execute(text('DELETE FROM inventory_movements'))
            session.execute(text('DELETE FROM outbox_events'))
            session.execute(text('DELETE FROM product_batches'))
            session.execute(text('DELETE FROM products'))
            session.execute(text('DELETE FROM users'))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error limpiando DB: {e}")
        finally:
            session.close()
        
        # Limpiar MongoDB (con manejo de errores)
        try:
            mongo_db = db_mongo.get_db()
            mongo_db['sales_tickets'].delete_many({})
        except Exception as e:
            # Si falla, continuar con los tests
            print(f"Warning: No se pudo limpiar MongoDB: {e}")


class TestAuth:
    """Tests de autenticación"""
    
    def test_register_user(self, client):
        """Test: Registrar nuevo usuario"""
        response = client.post('/api/auth/register', json={
            'username': 'test_user',
            'email': 'test@test.com',
            'password': 'test123',
            'role': 'cajero'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'token' in data
        assert data['user']['username'] == 'test_user'
    
    def test_login_success(self, client):
        """Test: Login exitoso"""
        # Registrar
        client.post('/api/auth/register', json={
            'username': 'login_test',
            'email': 'login@test.com',
            'password': 'password123',
            'role': 'cajero'
        })
        
        # Login
        response = client.post('/api/auth/login', json={
            'username': 'login_test',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
    
    def test_login_wrong_password(self, client):
        """Test: Login con contraseña incorrecta"""
        # Registrar
        client.post('/api/auth/register', json={
            'username': 'wrong_pwd',
            'email': 'wrong@test.com',
            'password': 'correct123',
            'role': 'cajero'
        })
        
        # Login incorrecto
        response = client.post('/api/auth/login', json={
            'username': 'wrong_pwd',
            'password': 'wrong_password'
        })
        
        assert response.status_code == 401


class TestProducts:
    """Tests de productos"""
    
    @pytest.fixture
    def auth_token(self, client):
        """Token de gerente"""
        response = client.post('/api/auth/register', json={
            'username': 'gerente_test',
            'email': 'gerente@test.com',
            'password': 'test123',
            'role': 'gerente'
        })
        return response.get_json()['token']
    
    def test_create_product(self, client, auth_token):
        """Test: Crear producto"""
        response = client.post('/api/products', 
            json={
                'sku': 'TEST-001',
                'name': 'Producto Test',
                'category': 'Testing',
                'base_price': 100.00
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['product']['sku'] == 'TEST-001'
    
    def test_list_products(self, client, auth_token):
        """Test: Listar productos"""
        # Crear producto
        client.post('/api/products', 
            json={
                'sku': 'LIST-001',
                'name': 'Para Listar',
                'base_price': 50.00
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Listar
        response = client.get('/api/products')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'products' in data


class TestInventory:
    """Tests de inventario"""
    
    @pytest.fixture
    def setup(self, client, app):
        """Setup"""
        with app.app_context():
            # Crear usuario
            response = client.post('/api/auth/register', json={
                'username': 'inv_manager',
                'email': 'inv@test.com',
                'password': 'test123',
                'role': 'inventario'
            })
            token = response.get_json()['token']
            
            # Crear producto
            session = db_postgres.get_session()
            product = Product(
                sku='INV-001',
                name='Producto Inventario',
                base_price=100.00
            )
            session.add(product)
            session.commit()
            product_id = product.id
            session.close()
            
            return {'token': token, 'product_id': product_id}
    
    def test_create_batch(self, client, setup):
        """Test: Crear lote"""
        response = client.post('/api/inventory/entry',
            json={
                'product_id': setup['product_id'],
                'batch_code': 'BATCH-TEST-001',
                'quantity': 100,
                'cost_per_unit': 50.00
            },
            headers={'Authorization': f'Bearer {setup["token"]}'}
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['batch']['quantity'] == 100


class TestHealthCheck:
    """Tests de health check"""
    
    def test_health_endpoint(self, client):
        """Test: Health check"""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])