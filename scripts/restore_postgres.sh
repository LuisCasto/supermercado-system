#!/bin/bash
# ============================================
# Script de Restauración - PostgreSQL
# Sistema Supermercado
# ============================================

set -e

# ====================================
# CONFIGURACIÓN
# ====================================
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5433}"
POSTGRES_DB="${POSTGRES_DB:-supermercado_db}"
POSTGRES_USER="${POSTGRES_USER:-admin}"
PGPASSWORD="${POSTGRES_PASSWORD:-admin123}"
export PGPASSWORD

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"

# ====================================
# VALIDACIÓN DE ARGUMENTOS
# ====================================
if [ $# -eq 0 ]; then
    echo "========================================="
    echo "Restauración PostgreSQL"
    echo "========================================="
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo ""
    echo "Backups disponibles:"
    echo "-----------------------------------------"
    find "${BACKUP_DIR}" -name "supermercado_*.sql.gz" -type f -printf "%T@ %p\n" | \
        sort -rn | \
        head -10 | \
        awk '{print $2}' | \
        nl
    echo "========================================="
    exit 1
fi

BACKUP_FILE="$1"

# Verificar que exista el archivo
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "✗ ERROR: No se encontró el archivo: ${BACKUP_FILE}"
    exit 1
fi

echo "========================================="
echo "Restauración PostgreSQL"
echo "========================================="
echo "Archivo: ${BACKUP_FILE}"
echo "Base de datos: ${POSTGRES_DB}"
echo "Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "-----------------------------------------"

# Confirmación
read -p "⚠ ADVERTENCIA: Esto ELIMINARÁ todos los datos actuales. ¿Continuar? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Operación cancelada"
    exit 0
fi

# ====================================
# BACKUP DE SEGURIDAD ANTES DE RESTAURAR
# ====================================
echo "→ Creando backup de seguridad de la base actual..."
SAFETY_BACKUP="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).sql"

pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-acl \
    --file="${SAFETY_BACKUP}"

if [ $? -eq 0 ]; then
    gzip "${SAFETY_BACKUP}"
    echo "✓ Backup de seguridad creado: ${SAFETY_BACKUP}.gz"
else
    echo "⚠ No se pudo crear backup de seguridad"
fi

# ====================================
# DESCOMPRIMIR BACKUP
# ====================================
TEMP_FILE="/tmp/restore_postgres_${RANDOM}.sql"

echo "→ Descomprimiendo backup..."
gunzip -c "${BACKUP_FILE}" > "${TEMP_FILE}"

if [ $? -ne 0 ]; then
    echo "✗ ERROR: No se pudo descomprimir el backup"
    exit 1
fi

echo "✓ Backup descomprimido"

# ====================================
# TERMINAR CONEXIONES ACTIVAS
# ====================================
echo "→ Terminando conexiones activas a la base..."

psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "SELECT pg_terminate_backend(pg_stat_activity.pid) 
        FROM pg_stat_activity 
        WHERE pg_stat_activity.datname = '${POSTGRES_DB}' 
        AND pid <> pg_backend_pid();" > /dev/null 2>&1

echo "✓ Conexiones terminadas"

# ====================================
# RESTAURAR BASE DE DATOS
# ====================================
echo "→ Restaurando base de datos..."

psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -f "${TEMP_FILE}" \
    --single-transaction

if [ $? -eq 0 ]; then
    echo "✓ Base de datos restaurada exitosamente"
else
    echo "✗ ERROR: Falló la restauración"
    echo "  Puedes intentar restaurar desde: ${SAFETY_BACKUP}.gz"
    rm -f "${TEMP_FILE}"
    exit 1
fi

# Limpiar archivo temporal
rm -f "${TEMP_FILE}"

# ====================================
# VERIFICACIÓN
# ====================================
echo "→ Verificando restauración..."

# Contar tablas
TABLE_COUNT=$(psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")

echo "  Tablas restauradas: ${TABLE_COUNT}"

# Contar usuarios
USER_COUNT=$(psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -t -c "SELECT COUNT(*) FROM users")

echo "  Usuarios en la base: ${USER_COUNT}"

# ====================================
# RESUMEN
# ====================================
echo "========================================="
echo "✓ RESTAURACIÓN COMPLETADA"
echo "========================================="
echo "Backup restaurado: ${BACKUP_FILE}"
echo "Backup de seguridad: ${SAFETY_BACKUP}.gz"
echo "========================================="

exit 0