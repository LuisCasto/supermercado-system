#!/bin/bash
# Backup usando Docker

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "========================================="
echo "Backup con Docker - Sistema Supermercado"
echo "========================================="
echo "Fecha: $(date)"
echo "-----------------------------------------"

mkdir -p "$BACKUP_DIR/postgres"
mkdir -p "$BACKUP_DIR/mongo"

# ====================================
# BACKUP POSTGRESQL
# ====================================
echo ""
echo "=== 1/2: BACKUP POSTGRESQL ==="

PG_BACKUP_FILE="$BACKUP_DIR/postgres/supermercado_${TIMESTAMP}.sql"

echo "→ Ejecutando pg_dump en contenedor..."
docker exec supermercado_postgres pg_dump \
    -U admin \
    -d supermercado_db \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    > "$PG_BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL backup creado: $PG_BACKUP_FILE"
    
    # Comprimir
    gzip "$PG_BACKUP_FILE"
    PG_BACKUP_FILE="${PG_BACKUP_FILE}.gz"
    
    SIZE=$(du -h "$PG_BACKUP_FILE" | cut -f1)
    echo "✓ Comprimido: $SIZE"
else
    echo "✗ Error en backup PostgreSQL"
    exit 1
fi

# ====================================
# BACKUP MONGODB
# ====================================
echo ""
echo "=== 2/2: BACKUP MONGODB ==="

MONGO_BACKUP_FILE="$BACKUP_DIR/mongo/supermercado_sales_${TIMESTAMP}.gz"

echo "→ Ejecutando mongodump en contenedor..."
docker exec supermercado_mongo mongodump \
    --username admin \
    --password admin123 \
    --authenticationDatabase admin \
    --db supermercado_sales \
    --gzip \
    --archive > "$MONGO_BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✓ MongoDB backup creado: $MONGO_BACKUP_FILE"
    
    SIZE=$(du -h "$MONGO_BACKUP_FILE" | cut -f1)
    echo "✓ Tamaño: $SIZE"
else
    echo "✗ Error en backup MongoDB"
    exit 1
fi

# ====================================
# RESUMEN
# ====================================
echo ""
echo "========================================="
echo "✓ BACKUP COMPLETADO"
echo "========================================="
echo "Archivos:"
echo "  - PostgreSQL: $PG_BACKUP_FILE"
echo "  - MongoDB: $MONGO_BACKUP_FILE"
echo "========================================="

exit 0
