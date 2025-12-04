#!/bin/bash
# ============================================
# Script de Inicio Rápido
# Sistema de Supermercado
# ============================================

set -e


# ====================================
# 1. VERIFICAR E INSTALAR DEPENDENCIAS
# ====================================
echo "→ Verificando dependencias del sistema..."

# Función para instalar dependencias en diferentes sistemas
install_dependencies() {
    echo ""
    echo "⚠ Algunas dependencias no están instaladas"
    echo "→ Intentando instalar automáticamente..."
    echo ""
    
    # Detectar sistema operativo
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            echo "→ Sistema detectado: Debian/Ubuntu"
            sudo apt-get update
            
            [ ! -x "$(command -v docker)" ] && sudo apt-get install -y docker.io
            [ ! -x "$(command -v docker-compose)" ] && sudo apt-get install -y docker-compose
            [ ! -x "$(command -v python3)" ] && sudo apt-get install -y python3 python3-pip python3-venv
            [ ! -x "$(command -v node)" ] && {
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                sudo apt-get install -y nodejs
            }
            
        elif command -v yum >/dev/null 2>&1; then
            # RedHat/CentOS/Fedora
            echo "→ Sistema detectado: RedHat/CentOS/Fedora"
            
            [ ! -x "$(command -v docker)" ] && sudo yum install -y docker
            [ ! -x "$(command -v docker-compose)" ] && sudo yum install -y docker-compose
            [ ! -x "$(command -v python3)" ] && sudo yum install -y python3 python3-pip
            [ ! -x "$(command -v node)" ] && {
                curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                sudo yum install -y nodejs
            }
        else
            echo "✗ Sistema Linux no soportado para instalación automática"
            echo "Por favor instala manualmente: Docker, Docker Compose, Python3, Node.js"
            exit 1
        fi
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "→ Sistema detectado: macOS"
        
        # Verificar si Homebrew está instalado
        if ! command -v brew >/dev/null 2>&1; then
            echo "→ Instalando Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        [ ! -x "$(command -v docker)" ] && brew install --cask docker
        [ ! -x "$(command -v python3)" ] && brew install python@3.11
        [ ! -x "$(command -v node)" ] && brew install node@20
        
    else
        echo "✗ Sistema operativo no soportado para instalación automática"
        exit 1
    fi
    
    echo ""
    echo "✓ Dependencias instaladas"
}

# Verificar cada dependencia
MISSING_DEPS=0

if ! command -v docker >/dev/null 2>&1; then
    echo "✗ Docker no está instalado"
    MISSING_DEPS=1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    echo "✗ Docker Compose no está instalado"
    MISSING_DEPS=1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ Python3 no está instalado"
    MISSING_DEPS=1
fi

if ! command -v node >/dev/null 2>&1; then
    echo "✗ Node.js no está instalado"
    MISSING_DEPS=1
fi

# Si faltan dependencias, intentar instalar
if [ $MISSING_DEPS -eq 1 ]; then
    read -p "¿Deseas instalar las dependencias faltantes automáticamente? (y/N): " INSTALL_DEPS
    
    if [[ $INSTALL_DEPS =~ ^[Yy]$ ]]; then
        install_dependencies
    else
        echo ""
        echo "❌ No se puede continuar sin las dependencias necesarias"
        echo ""
        echo "📦 Instala manualmente:"
        echo "   - Docker: https://docs.docker.com/get-docker/"
        echo "   - Docker Compose: https://docs.docker.com/compose/install/"
        echo "   - Python 3.11+: https://www.python.org/downloads/"
        echo "   - Node.js 20+: https://nodejs.org/"
        echo ""
        exit 1
    fi
fi

echo "✓ Todas las dependencias están instaladas"

# Verificar que Docker esté corriendo
if ! docker info >/dev/null 2>&1; then
    echo ""
    echo "⚠ Docker no está corriendo"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "→ Iniciando Docker Desktop..."
        open -a Docker
        echo "→ Esperando a que Docker inicie..."
        
        for i in {1..30}; do
            if docker info >/dev/null 2>&1; then
                echo "✓ Docker iniciado"
                break
            fi
            sleep 2
        done
        
        if ! docker info >/dev/null 2>&1; then
            echo "✗ Docker no pudo iniciarse. Por favor inícialo manualmente."
            exit 1
        fi
    else
        echo "→ Intentando iniciar Docker..."
        sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null
        sleep 3
        
        if ! docker info >/dev/null 2>&1; then
            echo "✗ No se pudo iniciar Docker. Inícialo manualmente con:"
            echo "   sudo systemctl start docker"
            exit 1
        fi
        echo "✓ Docker iniciado"
    fi
fi

echo ""

# ====================================
# 2. CREAR ARCHIVO .env SI NO EXISTE
# ====================================
if [ ! -f .env ]; then
    echo "→ Creando archivo .env..."
    cp .env.example .env
    echo "✓ Archivo .env creado"
fi
echo ""

# ====================================
# 3. LEVANTAR BASES DE DATOS
# ====================================
echo "→ Levantando bases de datos (PostgreSQL y MongoDB)..."
docker-compose -f docker-compose-dbs.yml up -d

echo "→ Esperando a que las bases de datos estén listas..."
sleep 10

# Verificar PostgreSQL
until docker exec supermercado_postgres pg_isready -U admin -d supermercado_db >/dev/null 2>&1; do
    echo "  Esperando PostgreSQL..."
    sleep 2
done
echo "✓ PostgreSQL está listo"

# Verificar MongoDB
until docker exec supermercado_mongo mongosh --eval "db.adminCommand('ping')" --quiet >/dev/null 2>&1; do
    echo "  Esperando MongoDB..."
    sleep 2
done
echo "✓ MongoDB está listo"
echo ""

# ====================================
# 4. CONFIGURAR BACKEND
# ====================================
echo "→ Configurando backend..."

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "  Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
echo "  Instalando dependencias Python..."
pip install -q -r requirements.txt

echo "✓ Backend configurado"
echo ""

# ====================================
# 5. INICIAR BACKEND EN BACKGROUND
# ====================================
echo "→ Iniciando servidor backend..."

python run.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✓ Backend iniciado (PID: $BACKEND_PID)"
echo "  Logs: tail -f logs/backend.log"

# Esperar a que el backend esté listo
echo "→ Esperando a que el backend esté listo..."
until curl -s http://localhost:5000/health > /dev/null 2>&1; do
    sleep 1
done
echo "✓ Backend respondiendo en http://localhost:5000"
echo ""

# ====================================
# 6. CONFIGURAR FRONTEND
# ====================================
echo "→ Configurando frontend..."
cd frontend

# Crear .env para frontend si no existe
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Instalar dependencias
if [ ! -d "node_modules" ]; then
    echo "  Instalando dependencias npm..."
    npm install --silent
fi

echo "✓ Frontend configurado"
echo ""

# ====================================
# 7. INICIAR FRONTEND EN BACKGROUND
# ====================================
echo "→ Iniciando servidor frontend..."

npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend iniciado (PID: $FRONTEND_PID)"
echo "  Logs: tail -f logs/frontend.log"

cd ..

# Esperar a que el frontend esté listo
echo "→ Esperando a que el frontend esté listo..."
sleep 5

# ====================================
# 8. RESUMEN Y ACCESO
# ====================================

echo "📍 URLs de Acceso:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:5000/health"
echo ""
echo "👤 Usuarios de Prueba:"
echo "   Gerente:    gerente1 / password123"
echo "   Cajero:     cajero1 / password123"
echo "   Inventario: inventario1 / password123"
echo ""
echo "📊 Bases de Datos:"
echo "   PostgreSQL: localhost:5433 (admin/admin123)"
echo "   MongoDB:    localhost:27018 (admin/admin123)"
echo ""
echo "🛑 Para detener el sistema:"
echo "   ./stop.sh"
echo ""
echo "📝 Logs en tiempo real:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""

# Guardar PIDs para poder detener después
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo "Presiona Ctrl+C para detener todos los servicios"

# Mantener el script corriendo y manejar Ctrl+C
trap 'echo ""; echo "→ Deteniendo servicios..."; ./stop.sh; exit 0' INT TERM

# Abrir navegador automáticamente (opcional)
if command -v xdg-open > /dev/null 2>&1; then
    sleep 2
    xdg-open http://localhost:5173 2>/dev/null || true
elif command -v open > /dev/null 2>&1; then
    sleep 2
    open http://localhost:5173 2>/dev/null || true
fi

# Esperar indefinidamente
wait