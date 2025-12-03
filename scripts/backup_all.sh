#!/bin/bash
# ============================================
# Script Maestro de Backup
# Sistema Supermercado - Postgres + MongoDB
# ============================================

set -e

# ====================================
# CONFIGURACIÓN
# ====================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/backups/backup_$(date +%Y%m%d_%H%M%S).log"

# Crear directorio de logs
mkdir -p "${SCRIPT_DIR}/backups"

# ====================================
# LOGGING
# ====================================
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "========================================="
echo "BACKUP COMPLETO DEL SISTEMA"
echo "========================================="
echo "Fecha: $(date)"
echo "Script: $0"
echo "-----------------------------------------"

# ====================================
# BACKUP POSTGRESQL
# ====================================
echo ""
echo "=== 1/2: BACKUP POSTGRESQL ==="
if [ -f "${SCRIPT_DIR}/scripts/backup_postgres.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/backup_postgres.sh"
    if [ $? -eq 0 ]; then
        echo "✓ PostgreSQL backup exitoso"
    else
        echo "✗ PostgreSQL backup falló"
        exit 1
    fi
else
    echo "⚠ Script de backup PostgreSQL no encontrado"
fi

# ====================================
# BACKUP MONGODB
# ====================================
echo ""
echo "=== 2/2: BACKUP MONGODB ==="
if [ -f "${SCRIPT_DIR}/scripts/backup_mongo.sh" ]; then
    bash "${SCRIPT_DIR}/scripts/backup_mongo.sh"
    if [ $? -eq 0 ]; then
        echo "✓ MongoDB backup exitoso"
    else
        echo "✗ MongoDB backup falló"
        exit 1
    fi
else
    echo "⚠ Script de backup MongoDB no encontrado"
fi

# ====================================
# VERIFICACIÓN
# ====================================
echo ""
echo "=== VERIFICACIÓN ==="

POSTGRES_BACKUPS=$(find "${SCRIPT_DIR}/backups/postgres" -name "supermercado_*.sql.gz" -type f -mtime -1 | wc -l)
MONGO_BACKUPS=$(find "${SCRIPT_DIR}/backups/mongo" -maxdepth 1 -type d -name "20*" -mtime -1 | wc -l)

echo "Backups de hoy:"
echo "  - PostgreSQL: ${POSTGRES_BACKUPS}"
echo "  - MongoDB: ${MONGO_BACKUPS}"

# ====================================
# RESUMEN
# ====================================
echo ""
echo "========================================="
echo "✓ BACKUP COMPLETO FINALIZADO"
echo "========================================="
echo "Log guardado en: ${LOG_FILE}"
echo "========================================="

exit 0