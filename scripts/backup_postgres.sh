#!/bin/bash
# ============================================
# Script de Backup - PostgreSQL
# Sistema Supermercado
# ============================================

set -e  # Salir si hay errores

# ====================================
# CONFIGURACIÓN
# ====================================
# Variables de entorno (o usar valores por defecto)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-supermercado_db}"
POSTGRES_USER="${POSTGRES_USER:-admin}"
PGPASSWORD="${POSTGRES_PASSWORD:-admin123}"
export PGPASSWORD

# Directorio de backups
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/supermercado_${TIMESTAMP}.sql"

# Retención: eliminar backups más antiguos que X días
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# ====================================
# VALIDACIÓN
# ====================================
echo "========================================="
echo "Backup PostgreSQL - Sistema Supermercado"
echo "========================================="
echo "Fecha: $(date)"
echo "Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "Base de datos: ${POSTGRES_DB}"
echo "-----------------------------------------"

# Crear directorio si no existe
mkdir -p "${BACKUP_DIR}"

# Verificar conexión
echo "→ Verificando conexión..."
if ! pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" > /dev/null 2>&1; then
    echo "✗ ERROR: No se puede conectar a PostgreSQL"
    exit 1
fi
echo "✓ Conexión exitosa"

# ====================================
# BACKUP COMPLETO (pg_dump)
# ====================================
echo "→ Iniciando backup completo..."

pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    --file="${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✓ Backup creado: ${BACKUP_FILE}"
    
    # Comprimir backup
    echo "→ Comprimiendo backup..."
    gzip "${BACKUP_FILE}"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    echo "✓ Backup comprimido: ${BACKUP_FILE}"
    
    # Tamaño del archivo
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✓ Tamaño del backup: ${SIZE}"
else
    echo "✗ ERROR: Falló el backup"
    exit 1
fi

# ====================================
# BACKUP DE SOLO DATOS (DATA-ONLY)
# ====================================
# Útil para restauraciones rápidas sin estructura
DATA_BACKUP_FILE="${BACKUP_DIR}/supermercado_data_${TIMESTAMP}.sql"

echo "→ Creando backup de solo datos..."
pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --format=plain \
    --data-only \
    --no-owner \
    --no-acl \
    --file="${DATA_BACKUP_FILE}"

if [ $? -eq 0 ]; then
    gzip "${DATA_BACKUP_FILE}"
    DATA_BACKUP_FILE="${DATA_BACKUP_FILE}.gz"
    echo "✓ Backup de datos creado: ${DATA_BACKUP_FILE}"
fi

# ====================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ====================================
echo "→ Eliminando backups antiguos (>${RETENTION_DAYS} días)..."

find "${BACKUP_DIR}" -name "supermercado_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "supermercado_data_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

REMAINING=$(find "${BACKUP_DIR}" -name "supermercado_*.sql.gz" -type f | wc -l)
echo "✓ Backups restantes: ${REMAINING}"

# ====================================
# BACKUP INCREMENTAL (WAL - Opcional)
# ====================================
# Para configurar WAL archiving, necesitas modificar postgresql.conf:
# wal_level = replica
# archive_mode = on
# archive_command = 'test ! -f /path/to/archive/%f && cp %p /path/to/archive/%f'

WAL_BACKUP_DIR="${BACKUP_DIR}/wal_archives"
if [ -d "${WAL_BACKUP_DIR}" ]; then
    echo "→ WAL archiving detectado en: ${WAL_BACKUP_DIR}"
    WAL_COUNT=$(find "${WAL_BACKUP_DIR}" -type f | wc -l)
    echo "  Archivos WAL: ${WAL_COUNT}"
fi

# ====================================
# RESUMEN
# ====================================
echo "========================================="
echo "✓ BACKUP COMPLETADO EXITOSAMENTE"
echo "========================================="
echo "Archivos creados:"
echo "  - Completo: ${BACKUP_FILE}"
echo "  - Solo datos: ${DATA_BACKUP_FILE}"
echo "========================================="

exit 0