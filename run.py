"""
Entry point de la aplicación Flask
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app import create_app

# Crear aplicación
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False') == 'True'
    
    print(f"""
    ╔════════════════════════════════════════════════╗
    ║   Sistema de Supermercado - API REST           ║
    ║   Iniciando en modo: {config_name:20s}      ║
    ║   URL: http://{host}:{port}                     ║
    ╚════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)