"""
Tests de integración del flujo de ventas completo:
1. Crear venta en Postgres
2. Verificar outbox event
3. Worker procesa evento
4. Ticket aparece en MongoDB
"""
import pytest
import time
from datetime import datetime
from app import create_app
from app.utils.db_postgres import db_postgres
from app.utils.db_mongo import db_mongo
from app.models import User, Product, ProductBatch, OutboxEvent
from worker.outbox_worker import init_worker, get_worker


@pytest.fixture(scope='module')
def app():
    """Crear app de testing"""
    app = create_app('testing')
    
    with app.app_context():
        # Crear tablas
        from app.models import Base
        from app.utils.db_postgres import Base as ModelBase
        ModelBase.metadata.create_all(bind=db_postgres.engine)
        
        # Inicializar worker
        init_worker(app)
        
        yield app
        
        # Cleanup
        ModelBase.metadata.drop_all(bind=db_postgres.engine)


@pytest.fixture
def client(app):
    """Cliente de testing"""
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    """Headers con token JWT"""
    with app.app_context():
        session = db_postgres.get_session()
        
        # Crear usuario de prueba
        user = User(username='test_cajero', email='test@test.com', role='cajero')
        user.set_password('test123')
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Generar token
        from app.middleware.jwt_utils import generate_token
        token = generate_token(user)
        
        session.close()
        
        return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_product(app):
    """Crear producto de prueba con stock"""
    with app.app_context():
        session = db_postgres.get_session()
        
        # Crear producto
        product = Product(
            sku='TEST-001',
            name='Producto de Prueba',
            category='Testing',
            base_price=50.00
        )
        session.add(product)
        session.flush()
        
        # Crear lote con stock
        batch = ProductBatch(
            product_id=product.id,
            batch_code='BATCH-TEST-001',
            quantity=100,
            cost_per_unit=30.00,
            received_date=datetime.now().date()
        )
        session.add(batch)
        session.commit()
        
        product_id = product.id
        session.close()
        
        yield product_id
        
        # Cleanup
        session = db_postgres.get_session()
        session.query(Product).filter_by(id=product_id).delete()
        session.commit()
        session.close()


def test_complete_sale_flow(client, auth_headers, sample_product, app):
    """
    Test del flujo completo:
    1. Crear venta vía API
    2. Verificar que se decrementó el stock en Postgres
    3. Verificar que se creó evento en outbox
    4. Esperar a que worker procese
    5. Verificar que el ticket existe en MongoDB
    """
    
    # ========================================
    # PASO 1: Crear venta
    # ========================================
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
    
    response = client.post(
        '/api/sales',
        json=sale_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.get_json()
    
    sale_id = data['sale_id']
    outbox_event_id = data['outbox_event_id']
    
    assert sale_id is not None
    assert outbox_event_id is not None
    assert data['grand_total'] == 290.0  # (50*5) * 1.16
    
    # ========================================
    # PASO 2: Verificar stock decrementado
    # ========================================
    with app.app_context():
        session = db_postgres.get_session()
        
        batch = session.query(ProductBatch).filter_by(
            batch_code='BATCH-TEST-001'
        ).first()
        
        assert batch is not None
        assert batch.quantity == 95  # 100 - 5
        
        session.close()
    
    # ========================================
    # PASO 3: Verificar evento outbox
    # ========================================
    with app.app_context():
        session = db_postgres.get_session()
        
        event = session.query(OutboxEvent).filter_by(
            id=outbox_event_id
        ).first()
        
        assert event is not None
        assert event.event_type == 'SALE_CREATED'
        assert event.aggregate_id == sale_id
        assert event.status == 'PENDING'
        assert 'items' in event.payload
        
        session.close()
    
    # ========================================
    # PASO 4: Esperar a que worker procese
    # ========================================
    time.sleep(6)  # Esperar un ciclo del worker (5s + margen)
    
    # ========================================
    # PASO 5: Verificar evento procesado
    # ========================================
    with app.app_context():
        session = db_postgres.get_session()
        
        event = session.query(OutboxEvent).filter_by(
            id=outbox_event_id
        ).first()
        
        assert event.status == 'COMPLETED'
        assert event.processed_at is not None
        
        session.close()
    
    # ========================================
    # PASO 6: Verificar ticket en MongoDB
    # ========================================
    with app.app_context():
        mongo_db = db_mongo.get_db()
        sales_collection = mongo_db['sales_tickets']
        
        ticket = sales_collection.find_one({'sale_id': sale_id})
        
        assert ticket is not None
        assert ticket['grand_total'] == 290.0
        assert len(ticket['items']) == 1
        assert ticket['items'][0]['quantity'] == 5
        assert ticket['status'] == 'completed'
        
        # Cleanup MongoDB
        sales_collection.delete_one({'sale_id': sale_id})


def test_concurrent_sales_no_overselling(client, auth_headers, sample_product, app):
    """
    Test de concurrencia: dos ventas simultáneas no deben causar overselling
    """
    import threading
    
    results = []
    
    def make_sale():
        sale_data = {
            'items': [
                {
                    'product_id': sample_product,
                    'quantity': 60  # Intentar vender 60 unidades
                }
            ],
            'payment_method': 'cash'
        }
        
        response = client.post(
            '/api/sales',
            json=sale_data,
            headers=auth_headers
        )
        
        results.append({
            'status_code': response.status_code,
            'data': response.get_json()
        })
    
    # Ejecutar dos ventas concurrentes
    thread1 = threading.Thread(target=make_sale)
    thread2 = threading.Thread(target=make_sale)
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    # Verificar resultados
    success_count = sum(1 for r in results if r['status_code'] == 201)
    failure_count = sum(1 for r in results if r['status_code'] == 400)
    
    # Solo UNA debe tener éxito (stock insuficiente para ambas)
    assert success_count == 1
    assert failure_count == 1
    
    # Verificar que el stock final es correcto
    with app.app_context():
        session = db_postgres.get_session()
        
        batch = session.query(ProductBatch).filter_by(
            batch_code='BATCH-TEST-001'
        ).first()
        
        # Stock inicial: 100 - 5 (del test anterior) = 95
        # Una venta exitosa de 60: 95 - 60 = 35
        assert batch.quantity == 35
        
        session.close()


def test_outbox_idempotency(app):
    """
    Test de idempotencia: procesar el mismo evento dos veces
    no debe crear duplicados en MongoDB
    """
    with app.app_context():
        from worker.outbox_worker import get_worker
        
        session = db_postgres.get_session()
        mongo_db = db_mongo.get_db()
        sales_collection = mongo_db['sales_tickets']
        
        # Crear evento outbox manualmente
        event = OutboxEvent(
            event_type='SALE_CREATED',
            aggregate_id='TEST-IDEMPOTENCY-001',
            payload={
                'sale_id': 'TEST-IDEMPOTENCY-001',
                'cashier_id': 1,
                'items': [{'product_id': 1, 'quantity': 1, 'unit_price': 10, 'subtotal': 10}],
                'total': 10,
                'grand_total': 11.6,
                'payment_method': 'cash',
                'status': 'completed',
                'timestamp': datetime.utcnow().isoformat()
            },
            status='PENDING'
        )
        session.add(event)
        session.commit()
        event_id = event.id
        
        # Procesar primera vez
        worker = get_worker()
        worker._process_batch()
        
        # Verificar que se creó el ticket
        ticket = sales_collection.find_one({'sale_id': 'TEST-IDEMPOTENCY-001'})
        assert ticket is not None
        
        # Marcar evento como PENDING de nuevo (simular reintento)
        event = session.query(OutboxEvent).filter_by(id=event_id).first()
        event.status = 'PENDING'
        session.commit()
        
        # Procesar segunda vez
        worker._process_batch()
        
        # Verificar que NO se duplicó el ticket
        count = sales_collection.count_documents({'sale_id': 'TEST-IDEMPOTENCY-001'})
        assert count == 1
        
        # Cleanup
        sales_collection.delete_one({'sale_id': 'TEST-IDEMPOTENCY-001'})
        session.query(OutboxEvent).filter_by(id=event_id).delete()
        session.commit()
        session.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])