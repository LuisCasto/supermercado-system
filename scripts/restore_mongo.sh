#!/bin/bash
# ============================================
# Script de Restauración - MongoDB
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

BACKUP_DIR="${BACKUP_DIR:-./backups/mongo}"

# ====================================
# VALIDACIÓN DE ARGUMENTOS
# ====================================
if [ $# -eq 0 ]; then
    echo "========================================="
    echo "Restauración MongoDB"
    echo "========================================="
    echo "Uso: $0 <directorio_backup>"
    echo ""
    echo "Backups disponibles:"
    echo "-----------------------------------------"
    find "${BACKUP_DIR}" -maxdepth 1 -type d -name "20*" -printf "%T@ %p\n" | \
        sort -rn | \
        head -10 | \
        awk '{print $2}' | \
        nl
    echo "========================================="
    exit 1
fi

BACKUP_PATH="$1"

# Verificar que exista el directorio
if [ ! -d "${BACKUP_PATH}" ]; then
    echo "✗ ERROR: No se encontró el directorio: ${BACKUP_PATH}"
    exit 1
fi

echo "========================================="
echo "Restauración MongoDB"
echo "========================================="
echo "Directorio: ${BACKUP_PATH}"
echo "Base de datos: ${MONGO_DB}"
echo "Host: ${MONGO_HOST}:${MONGO_PORT}"
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
SAFETY_BACKUP="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S)"

mongodump \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --db "${MONGO_DB}" \
    --out "${SAFETY_BACKUP}" \
    --gzip \
    --quiet

if [ $? -eq 0 ]; then
    echo "✓ Backup de seguridad creado: ${SAFETY_BACKUP}"
else
    echo "⚠ No se pudo crear backup de seguridad"
fi

# ====================================
# ELIMINAR COLECCIONES EXISTENTES
# ====================================
echo "→ Eliminando colecciones existentes..."

mongosh \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --quiet \
    --eval "
        use ${MONGO_DB};
        db.getCollectionNames().forEach(function(col) {
            if (col != 'system.indexes') {
                db[col].drop();
                print('Eliminada: ' + col);
            }
        });
    "

echo "✓ Colecciones eliminadas"

# ====================================
# RESTAURAR BASE DE DATOS
# ====================================
echo "→ Restaurando base de datos..."

mongorestore \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --db "${MONGO_DB}" \
    --dir "${BACKUP_PATH}/${MONGO_DB}" \
    --gzip \
    --drop

if [ $? -eq 0 ]; then
    echo "✓ Base de datos restaurada exitosamente"
else
    echo "✗ ERROR: Falló la restauración"
    echo "  Puedes intentar restaurar desde: ${SAFETY_BACKUP}"
    exit 1
fi

# ====================================
# VERIFICACIÓN
# ====================================
echo "→ Verificando restauración..."

STATS=$(mongosh \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --quiet \
    --eval "
        use ${MONGO_DB};
        const collections = db.getCollectionNames().length;
        const count = db.sales_tickets.countDocuments();
        print('Colecciones: ' + collections + ' | Documentos en sales_tickets: ' + count);
    ")

echo "  ${STATS}"

# ====================================
# RECONSTRUIR ÍNDICES
# ====================================
echo "→ Reconstruyendo índices..."

mongosh \
    --host "${MONGO_HOST}" \
    --port "${MONGO_PORT}" \
    --username "${MONGO_USER}" \
    --password "${MONGO_PASSWORD}" \
    --authenticationDatabase "${MONGO_AUTH_DB}" \
    --quiet \
    --eval "
        use ${MONGO_DB};
        db.sales_tickets.reIndex();
        print('Índices reconstruidos');
    "

echo "✓ Índices reconstruidos"

# ====================================
# RESUMEN
# ====================================
echo "========================================="
echo "✓ RESTAURACIÓN COMPLETADA"
echo "========================================="
echo "Backup restaurado: ${BACKUP_PATH}"
echo "Backup de seguridad: ${SAFETY_BACKUP}"
echo "========================================="

exit 0