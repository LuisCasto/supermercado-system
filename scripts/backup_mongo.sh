#!/bin/bash
# ============================================
# Script de Backup - MongoDB
# Sistema Supermercado
# ============================================

set -e

# ====================================
# CONFIGURACIÓN
# ====================================
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27018}"
MONGO_DB="${MONGO_DB:-supermercado_sales}"
MONGO_USER="${MONGO_USER:-admin}"
MONGO_PASSWORD="${MONGO_PASSWORD:-admin123}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"

# Directorio de backups
BACKUP_DIR="${BACKUP_DIR:-./backups/mongo}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"

# Retención
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# ====================================
# VALIDACIÓN
# ====================================
echo "========================================="
echo "Backup MongoDB - Sistema Supermercado"
echo "========================================="
echo "Fecha: $(date)"
echo "Host: ${MONGO_HOST}:${MONGO_PORT}"
echo "Base de datos: ${MONGO_DB}"
echo "-----------------------------------------"

# Crear directorio
mkdir -p "${BACKUP_DIR}"

# Verificar conexión
echo "→ Verificando conexión..."
if ! mongosh \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --quiet \
    --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "✗ ERROR: No se puede conectar a MongoDB"
    exit 1
fi
echo "✓ Conexión exitosa"

# ====================================
# BACKUP CON MONGODUMP
# ====================================
echo "→ Iniciando backup con mongodump..."

mongodump \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --db "${MONGO_DB}" \
    --out "${BACKUP_PATH}" \
    --gzip

if [ $? -eq 0 ]; then
    echo "✓ Backup creado en: ${BACKUP_PATH}"
    
    # Tamaño
    SIZE=$(du -sh "${BACKUP_PATH}" | cut -f1)
    echo "✓ Tamaño del backup: ${SIZE}"
    
    # Contar documentos respaldados
    COLLECTIONS=$(find "${BACKUP_PATH}/${MONGO_DB}" -name "*.bson.gz" | wc -l)
    echo "✓ Colecciones respaldadas: ${COLLECTIONS}"
else
    echo "✗ ERROR: Falló el backup"
    exit 1
fi

# ====================================
# BACKUP DE COLECCIÓN ESPECÍFICA
# ====================================
# Respaldar solo sales_tickets (la más importante)
COLLECTION_BACKUP_PATH="${BACKUP_DIR}/sales_tickets_${TIMESTAMP}"
echo "→ Backup de colección 'sales_tickets'..."

mongodump \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --db "${MONGO_DB}" \
    --collection "sales_tickets" \
    --out "${COLLECTION_BACKUP_PATH}" \
    --gzip

if [ $? -eq 0 ]; then
    echo "✓ Colección 'sales_tickets' respaldada"
fi

# ====================================
# BACKUP EN JSON (LEGIBLE)
# ====================================
# Útil para auditorías y revisión manual
JSON_BACKUP_DIR="${BACKUP_DIR}/json_exports"
mkdir -p "${JSON_BACKUP_DIR}"

echo "→ Exportando sales_tickets a JSON..."

mongoexport \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --db "${MONGO_DB}" \
    --collection "sales_tickets" \
    --out "${JSON_BACKUP_DIR}/sales_tickets_${TIMESTAMP}.json" \
    --jsonArray

if [ $? -eq 0 ]; then
    gzip "${JSON_BACKUP_DIR}/sales_tickets_${TIMESTAMP}.json"
    echo "✓ Exportación JSON creada"
fi

# ====================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ====================================
echo "→ Eliminando backups antiguos (>${RETENTION_DAYS} días)..."

find "${BACKUP_DIR}" -maxdepth 1 -type d -name "20*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
find "${BACKUP_DIR}" -maxdepth 1 -type d -name "sales_tickets_*" -mtime +${RETENTION_DAYS} -exec rm -rf {} \;
find "${JSON_BACKUP_DIR}" -name "sales_tickets_*.json.gz" -mtime +${RETENTION_DAYS} -delete

REMAINING=$(find "${BACKUP_DIR}" -maxdepth 1 -type d -name "20*" | wc -l)
echo "✓ Backups restantes: ${REMAINING}"

# ====================================
# ESTADÍSTICAS
# ====================================
echo "→ Obteniendo estadísticas de la base..."

STATS=$(mongosh \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --quiet \
    --eval "
        use ${MONGO_DB};
        const count = db.sales_tickets.countDocuments();
        const size = db.sales_tickets.stats().size;
        print('Documentos: ' + count + ' | Tamaño: ' + (size / 1024 / 1024).toFixed(2) + ' MB');
    ")

echo "  ${STATS}"

# ====================================
# RESUMEN
# ====================================
echo "========================================="
echo "✓ BACKUP COMPLETADO EXITOSAMENTE"
echo "========================================="
echo "Archivos creados:"
echo "  - Completo: ${BACKUP_PATH}"
echo "  - Colección: ${COLLECTION_BACKUP_PATH}"
echo "  - JSON: ${JSON_BACKUP_DIR}/sales_tickets_${TIMESTAMP}.json.gz"
echo "========================================="

exit 0