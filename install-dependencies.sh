#!/bin/bash
# ============================================
# Instalador Automático de Dependencias
# Sistema de Supermercado
# ============================================

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║   📦 Instalador de Dependencias Automático     ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# ====================================
# DETECTAR SISTEMA OPERATIVO
# ====================================
echo "→ Detectando sistema operativo..."

OS="unknown"
PACKAGE_MANAGER="unknown"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if command -v apt-get >/dev/null 2>&1; then
        PACKAGE_MANAGER="apt"
        print_success "Sistema: Ubuntu/Debian"
    elif command -v yum >/dev/null 2>&1; then
        PACKAGE_MANAGER="yum"
        print_success "Sistema: RedHat/CentOS/Fedora"
    elif command -v dnf >/dev/null 2>&1; then
        PACKAGE_MANAGER="dnf"
        print_success "Sistema: Fedora (dnf)"
    elif command -v pacman >/dev/null 2>&1; then
        PACKAGE_MANAGER="pacman"
        print_success "Sistema: Arch Linux"
    else
        print_error "Gestor de paquetes no soportado"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    print_success "Sistema: macOS"
else
    print_error "Sistema operativo no soportado: $OSTYPE"
    exit 1
fi

echo ""

# ====================================
# VERIFICAR DEPENDENCIAS ACTUALES
# ====================================
echo "→ Verificando dependencias instaladas..."
echo ""

NEED_DOCKER=0
NEED_DOCKER_COMPOSE=0
NEED_PYTHON=0
NEED_NODE=0

if ! command -v docker >/dev/null 2>&1; then
    print_warning "Docker no está instalado"
    NEED_DOCKER=1
else
    print_success "Docker ya está instalado ($(docker --version))"
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    print_warning "Docker Compose no está instalado"
    NEED_DOCKER_COMPOSE=1
else
    print_success "Docker Compose ya está instalado ($(docker-compose --version))"
fi

if ! command -v python3 >/dev/null 2>&1; then
    print_warning "Python3 no está instalado"
    NEED_PYTHON=1
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python3 ya está instalado (v${PYTHON_VERSION})"
fi

if ! command -v node >/dev/null 2>&1; then
    print_warning "Node.js no está instalado"
    NEED_NODE=1
else
    NODE_VERSION=$(node --version)
    print_success "Node.js ya está instalado (${NODE_VERSION})"
fi

# Si todo está instalado, salir
if [ $NEED_DOCKER -eq 0 ] && [ $NEED_DOCKER_COMPOSE -eq 0 ] && [ $NEED_PYTHON -eq 0 ] && [ $NEED_NODE -eq 0 ]; then
    echo ""
    print_success "¡Todas las dependencias ya están instaladas!"
    echo ""
    echo "Puedes ejecutar el sistema con:"
    echo "  ./start.sh"
    exit 0
fi

# ====================================
# CONFIRMAR INSTALACIÓN
# ====================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Dependencias que se instalarán:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
[ $NEED_DOCKER -eq 1 ] && echo "  • Docker"
[ $NEED_DOCKER_COMPOSE -eq 1 ] && echo "  • Docker Compose"
[ $NEED_PYTHON -eq 1 ] && echo "  • Python 3.11+"
[ $NEED_NODE -eq 1 ] && echo "  • Node.js 20+"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "¿Continuar con la instalación? (y/N): " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Instalación cancelada"
    exit 0
fi

echo ""

# ====================================
# INSTALAR DEPENDENCIAS - macOS
# ====================================
if [ "$OS" = "macos" ]; then
    echo "→ Instalando en macOS..."
    echo ""
    
    # Instalar Homebrew si no está
    if ! command -v brew >/dev/null 2>&1; then
        echo "→ Instalando Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Agregar Homebrew al PATH
        if [[ $(uname -m) == 'arm64' ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        else
            echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        
        print_success "Homebrew instalado"
    fi
    
    # Docker Desktop
    if [ $NEED_DOCKER -eq 1 ]; then
        echo "→ Instalando Docker Desktop..."
        brew install --cask docker
        print_success "Docker Desktop instalado"
        print_warning "Inicia Docker Desktop desde Aplicaciones antes de ejecutar el sistema"
    fi
    
    # Python
    if [ $NEED_PYTHON -eq 1 ]; then
        echo "→ Instalando Python 3.11..."
        brew install python@3.11
        print_success "Python 3.11 instalado"
    fi
    
    # Node.js
    if [ $NEED_NODE -eq 1 ]; then
        echo "→ Instalando Node.js 20..."
        brew install node@20
        brew link --overwrite node@20
        print_success "Node.js 20 instalado"
    fi
fi

# ====================================
# INSTALAR DEPENDENCIAS - Linux
# ====================================
if [ "$OS" = "linux" ]; then
    echo "→ Instalando en Linux ($PACKAGE_MANAGER)..."
    echo ""
    
    # Actualizar repositorios
    if [ "$PACKAGE_MANAGER" = "apt" ]; then
        echo "→ Actualizando repositorios..."
        sudo apt-get update -qq
        
        # Docker
        if [ $NEED_DOCKER -eq 1 ]; then
            echo "→ Instalando Docker..."
            sudo apt-get install -y docker.io
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            print_success "Docker instalado"
            print_warning "Reinicia tu sesión para usar Docker sin sudo"
        fi
        
        # Docker Compose
        if [ $NEED_DOCKER_COMPOSE -eq 1 ]; then
            echo "→ Instalando Docker Compose..."
            sudo apt-get install -y docker-compose
            print_success "Docker Compose instalado"
        fi
        
        # Python
        if [ $NEED_PYTHON -eq 1 ]; then
            echo "→ Instalando Python 3..."
            sudo apt-get install -y python3 python3-pip python3-venv
            print_success "Python 3 instalado"
        fi
        
        # Node.js
        if [ $NEED_NODE -eq 1 ]; then
            echo "→ Instalando Node.js 20..."
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install -y nodejs
            print_success "Node.js 20 instalado"
        fi
        
    elif [ "$PACKAGE_MANAGER" = "yum" ] || [ "$PACKAGE_MANAGER" = "dnf" ]; then
        CMD="sudo $PACKAGE_MANAGER"
        
        # Docker
        if [ $NEED_DOCKER -eq 1 ]; then
            echo "→ Instalando Docker..."
            $CMD install -y docker
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            print_success "Docker instalado"
        fi
        
        # Docker Compose
        if [ $NEED_DOCKER_COMPOSE -eq 1 ]; then
            echo "→ Instalando Docker Compose..."
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            print_success "Docker Compose instalado"
        fi
        
        # Python
        if [ $NEED_PYTHON -eq 1 ]; then
            echo "→ Instalando Python 3..."
            $CMD install -y python3 python3-pip
            print_success "Python 3 instalado"
        fi
        
        # Node.js
        if [ $NEED_NODE -eq 1 ]; then
            echo "→ Instalando Node.js 20..."
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
            $CMD install -y nodejs
            print_success "Node.js 20 instalado"
        fi
        
    elif [ "$PACKAGE_MANAGER" = "pacman" ]; then
        # Docker
        if [ $NEED_DOCKER -eq 1 ]; then
            echo "→ Instalando Docker..."
            sudo pacman -S --noconfirm docker
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            print_success "Docker instalado"
        fi
        
        # Docker Compose
        if [ $NEED_DOCKER_COMPOSE -eq 1 ]; then
            echo "→ Instalando Docker Compose..."
            sudo pacman -S --noconfirm docker-compose
            print_success "Docker Compose instalado"
        fi
        
        # Python
        if [ $NEED_PYTHON -eq 1 ]; then
            echo "→ Instalando Python 3..."
            sudo pacman -S --noconfirm python python-pip
            print_success "Python 3 instalado"
        fi
        
        # Node.js
        if [ $NEED_NODE -eq 1 ]; then
            echo "→ Instalando Node.js..."
            sudo pacman -S --noconfirm nodejs npm
            print_success "Node.js instalado"
        fi
    fi
fi

# ====================================
# VERIFICACIÓN FINAL
# ====================================
echo ""
echo "→ Verificando instalación..."
echo ""

ALL_OK=1

if command -v docker >/dev/null 2>&1; then
    print_success "Docker: $(docker --version)"
else
    print_error "Docker no se instaló correctamente"
    ALL_OK=0
fi

if command -v docker-compose >/dev/null 2>&1; then
    print_success "Docker Compose: $(docker-compose --version)"
else
    print_error "Docker Compose no se instaló correctamente"
    ALL_OK=0
fi

if command -v python3 >/dev/null 2>&1; then
    print_success "Python: $(python3 --version)"
else
    print_error "Python no se instaló correctamente"
    ALL_OK=0
fi

if command -v node >/dev/null 2>&1; then
    print_success "Node.js: $(node --version)"
    print_success "npm: $(npm --version)"
else
    print_error "Node.js no se instaló correctamente"
    ALL_OK=0
fi

# ====================================
# RESUMEN
# ====================================
echo ""
echo "╔════════════════════════════════════════════════╗"
if [ $ALL_OK -eq 1 ]; then
    echo "║     ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE     ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    echo "🎉 ¡Todas las dependencias están instaladas!"
    echo ""
    
    if [ "$OS" = "linux" ] && [ $NEED_DOCKER -eq 1 ]; then
        print_warning "IMPORTANTE: Reinicia tu sesión para usar Docker sin sudo"
        echo "  logout y login nuevamente"
        echo ""
    fi
    
    if [ "$OS" = "macos" ] && [ $NEED_DOCKER -eq 1 ]; then
        print_warning "IMPORTANTE: Inicia Docker Desktop desde Aplicaciones"
        echo ""
    fi
    
    echo "🚀 Ya puedes iniciar el sistema:"
    echo "   ./start.sh"
    echo ""
else
    echo "║      ⚠ INSTALACIÓN INCOMPLETA                  ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    print_error "Algunas dependencias no se instalaron correctamente"
    echo "Por favor revisa los errores anteriores"
    echo ""
    exit 1
fi