"""
Tests de integración del flujo de ventas completo
"""
import pytest
import time
from datetime import datetime, date
from sqlalchemy import text
from app import create_app
from app.utils.db_postgres import db_postgres, Base
from app.utils.db_mongo import db_mongo
from app.models import User, Product, ProductBatch, OutboxEvent, InventoryMovement
from worker.outbox_worker import init_worker, get_worker, stop_worker


@pytest.fixture(scope='module')
def app():
    """Crear app de testing"""
    app = create_app('testing')
    
    with app.app_context():
        # ✅ CREAR TABLAS PRIMERO
        Base.metadata.create_all(bind=db_postgres.engine)
        
        # ✅ AHORA SÍ INICIALIZAR WORKER (después de crear tablas)
        worker = init_worker(app)
        
        yield app
        
        # Cleanup
        if worker:
            worker.stop()
        
        Base.metadata.drop_all(bind=db_postgres.engine)
        
        try:
            mongo_db = db_mongo.get_db()
            mongo_db['sales_tickets'].delete_many({})
        except:
            pass
        
        # ✅ LIMPIAR ARCHIVO SQLite TEMPORAL
        import os
        import tempfile
        test_db = os.path.join(tempfile.gettempdir(), 'test_supermercado.db')
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except:
                pass


@pytest.fixture
def client(app):
    """Cliente de testing"""
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_test_data(app):
    """Limpiar datos antes de cada test"""
    with app.app_context():
        # Limpiar PostgreSQL/SQLite
        session = db_postgres.get_session()
        try:
            session.execute(text('DELETE FROM inventory_movements'))
            session.execute(text('DELETE FROM outbox_events'))
            session.execute(text('DELETE FROM product_batches'))
            session.execute(text('DELETE FROM products'))
            session.execute(text('DELETE FROM users'))
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()
        
        # ✅ Limpiar MongoDB SOLO de datos de test
        try:
            mongo_db = db_mongo.get_db()
            # Eliminar solo tickets con sale_id de test (que empiezan con SALE-)
            # Para evitar eliminar datos reales si compartes la base
            result = mongo_db['sales_tickets'].delete_many({
                'sale_id': {'$regex': '^SALE-'}
            })
            print(f"🧹 MongoDB limpiado: {result.deleted_count} documentos eliminados")
        except Exception as e:
            print(f"⚠️ Error limpiando MongoDB: {e}")
    
    yield  # Ejecutar test
    
    # Limpiar después también
    with app.app_context():
        try:
            mongo_db = db_mongo.get_db()
            mongo_db['sales_tickets'].delete_many({
                'sale_id': {'$regex': '^SALE-'}
            })
        except:
            pass


@pytest.fixture
def auth_headers(app):
    """Headers con token JWT"""
    with app.app_context():
        session = db_postgres.get_session()
        
        user = User(username='test_cajero', email='test@test.com', role='cajero', active=True)
        user.set_password('test123')
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
        session.close()
        
        from app.middleware.jwt_utils import generate_token
        session = db_postgres.get_session()
        user = session.query(User).filter_by(id=user_id).first()
        token = generate_token(user)
        session.close()
        
        return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_product(app):
    """Crear producto con stock"""
    with app.app_context():
        session = db_postgres.get_session()
        
        product = Product(
            sku='TEST-001',
            name='Producto Test',
            category='Testing',
            base_price=50.00,
            active=True
        )
        session.add(product)
        session.flush()
        
        batch = ProductBatch(
            product_id=product.id,
            batch_code='BATCH-001',
            quantity=100,
            cost_per_unit=30.00,
            received_date=date.today()
        )
        session.add(batch)
        session.commit()
        
        product_id = product.id
        session.close()
        
        yield product_id


def test_complete_sale_flow(client, auth_headers, sample_product, app):
    """
    Test: Flujo completo de venta
    1. Crear venta → 2. Verificar stock → 3. Verificar outbox → 4. Worker procesa → 5. Ticket en MongoDB
    """
    
    print("\n=== TEST: Flujo Completo de Venta ===")
    
    # 1. Crear venta
    sale_data = {
        'items': [
            {
                'product_id': sample_product,
                'quantity': 5,
                'unit_price': 50.00
            }
        ],
        'payment_method': 'cash',
        'tax_rate': 0.16
    }
    
    response = client.post('/api/sales', json=sale_data, headers=auth_headers)
    
    assert response.status_code == 201, f"Error: {response.get_json()}"
    data = response.get_json()
    
    sale_id = data['sale_id']
    outbox_event_id = data['outbox_event_id']
    
    print(f"✓ Venta creada: {sale_id}")
    assert data['grand_total'] == 290.0
    
    # 2. Verificar stock
    with app.app_context():
        session = db_postgres.get_session()
        batch = session.query(ProductBatch).filter_by(batch_code='BATCH-001').first()
        assert batch.quantity == 95, f"Stock esperado 95, obtenido {batch.quantity}"
        print(f"✓ Stock decrementado: 100 → 95")
        session.close()
    
    # 3. Verificar outbox
    with app.app_context():
        session = db_postgres.get_session()
        event = session.query(OutboxEvent).filter_by(id=outbox_event_id).first()
        assert event.status == 'PENDING'
        print(f"✓ Evento outbox creado (ID: {outbox_event_id})")
        session.close()
    
    # 4. Esperar worker (aumentar tiempo para dar margen)
    print("⏳ Esperando worker (5 segundos)...")
    time.sleep(5)
    
    # 5. Verificar procesado
    with app.app_context():
        session = db_postgres.get_session()
        event = session.query(OutboxEvent).filter_by(id=outbox_event_id).first()
        
        if event.status != 'COMPLETED':
            print(f"❌ Evento no procesado. Estado: {event.status}")
            print(f"   Retry count: {event.retry_count}")
            print(f"   Error: {event.error_message}")
        
        assert event.status == 'COMPLETED', f"Estado: {event.status}, Error: {event.error_message}"
        print(f"✓ Evento procesado por worker")
        session.close()
    
    # 6. Verificar MongoDB
    with app.app_context():
        try:
            mongo_db = db_mongo.get_db()
            ticket = mongo_db['sales_tickets'].find_one({'sale_id': sale_id})
            
            assert ticket is not None, f"Ticket {sale_id} no encontrado en MongoDB"
            assert ticket['grand_total'] == 290.0
            print(f"✓ Ticket verificado en MongoDB")
            print(f"\n=== TEST PASADO ===\n")
        
        except Exception as e:
            print(f"❌ Error verificando MongoDB: {e}")
            raise


def test_insufficient_stock(client, auth_headers, sample_product):
    """Test: No se puede vender más de lo disponible"""
    
    print("\n=== TEST: Stock Insuficiente ===")
    
    sale_data = {
        'items': [
            {
                'product_id': sample_product,
                'quantity': 150  # Solo hay 100
            }
        ],
        'payment_method': 'cash'
    }
    
    response = client.post('/api/sales', json=sale_data, headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'insuficiente' in data['message'].lower() or 'insufficient' in data['message'].lower()
    
    print(f"✓ Venta rechazada correctamente: {data['message']}")
    print(f"=== TEST PASADO ===\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])