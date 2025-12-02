"""
Script temporal para probar conexiones a las bases de datos
"""
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.utils.db_postgres import db_postgres
from app.utils.db_mongo import db_mongo
from app.models import User, Product

app = create_app('development')

with app.app_context():
    print("\n=== PROBANDO CONEXIONES ===\n")
    
    # Probar PostgreSQL
    print("1. Probando PostgreSQL...")
    try:
        session = db_postgres.get_session()
        
        # Contar usuarios
        user_count = session.query(User).count()
        print(f"   ✓ Usuarios en la DB: {user_count}")
        
        # Listar usuarios
        users = session.query(User).limit(3).all()
        for user in users:
            print(f"   - {user.username} ({user.role})")
        
        # Contar productos
        product_count = session.query(Product).count()
        print(f"   ✓ Productos en la DB: {product_count}")
        
        session.close()
        print("   ✓ PostgreSQL funcionando correctamente\n")
        
    except Exception as e:
        print(f"   ✗ Error en PostgreSQL: {e}\n")
    
    # Probar MongoDB
    print("2. Probando MongoDB...")
    try:
        mongo_db = db_mongo.get_db()
        
        # Contar tickets
        sales_collection = mongo_db['sales_tickets']
        ticket_count = sales_collection.count_documents({})
        print(f"   ✓ Tickets en la DB: {ticket_count}")
        
        # Mostrar un ticket
        ticket = sales_collection.find_one()
        if ticket:
            print(f"   - Ticket ID: {ticket.get('sale_id')}")
            print(f"   - Total: ${ticket.get('grand_total', ticket.get('total'))}")
        
        print("   ✓ MongoDB funcionando correctamente\n")
        
    except Exception as e:
        print(f"   ✗ Error en MongoDB: {e}\n")
    
    print("=== PRUEBAS COMPLETADAS ===\n")