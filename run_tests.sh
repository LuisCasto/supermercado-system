#!/bin/bash

# ============================================
# Script para ejecutar tests del sistema
# ============================================

echo "========================================="
echo "Ejecutando Tests del Sistema Supermercado"
echo "========================================="

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
fi

# Configurar variables de entorno para testing
export FLASK_ENV=testing
export TESTING=True

# Limpiar cache de pytest
rm -rf .pytest_cache
rm -rf __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo ""
echo "→ Ejecutando tests básicos..."
pytest tests/test_basic.py -v --tb=short

echo ""
echo "→ Ejecutando tests de integración..."
pytest tests/test_integration_sales.py -v --tb=short -s

echo ""
echo "========================================="
echo "Tests completados"
echo "========================================="