# 🛒 Sistema de Supermercado - Inicio Rápido

Sistema completo de gestión para supermercados con control de inventario, ventas, y reportes en tiempo real.

## 🚀 Inicio Rápido (Un Solo Comando)

### Opción A: Instalación Automática de Dependencias ⭐ RECOMENDADO

```bash
# 1. Clonar el repositorio
git clone <tu-repositorio>
cd supermercado-system

# 2. Dar permisos de ejecución
chmod +x *.sh

# 3. Instalar dependencias automáticamente (si faltan)
./install-dependencies.sh

# 4. Iniciar el sistema
./start.sh
```

El script `install-dependencies.sh` detecta tu sistema operativo e instala automáticamente:
- ✅ Docker y Docker Compose
- ✅ Python 3.11+
- ✅ Node.js 20+

**Sistemas soportados:**
- Ubuntu/Debian (apt)
- RedHat/CentOS/Fedora (yum/dnf)
- Arch Linux (pacman)
- macOS (Homebrew)

### Opción B: Con Dependencias Ya Instaladas

Si ya tienes instalado Docker, Python y Node.js:

```bash
# 1. Clonar el repositorio
git clone <tu-repositorio>
cd supermercado-system

# 2. Dar permisos de ejecución
chmod +x start.sh stop.sh

# 3. Iniciar el sistema
./start.sh
```

El script `start.sh` verificará las dependencias y te preguntará si quieres instalarlas automáticamente si falta alguna.

### Para Windows

```bash
# 1. Clonar el repositorio
git clone <tu-repositorio>
cd supermercado-system

# 2. Ejecutar el script de inicio
start.bat
```

**Nota para Windows:** Debes instalar manualmente las dependencias:
- Docker Desktop: https://www.docker.com/products/docker-desktop
- Python 3.11+: https://www.python.org/downloads/ (marca "Add Python to PATH")
- Node.js 20+: https://nodejs.org/

**¡Eso es todo!** El script automáticamente:
- ✅ Levanta PostgreSQL y MongoDB con Docker
- ✅ Configura el entorno virtual de Python
- ✅ Instala todas las dependencias
- ✅ Inicia el backend Flask
- ✅ Inicia el frontend React
- ✅ Abre el navegador automáticamente

### 🌐 URLs de Acceso

Una vez iniciado, accede a:

| Servicio | URL |
|----------|-----|
| **Frontend (App)** | http://localhost:5173 |
| **Backend API** | http://localhost:5000 |
| **Health Check** | http://localhost:5000/health |

### 👤 Usuarios de Prueba

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `gerente1` | `password123` | Gerente (acceso completo) |
| `cajero1` | `password123` | Cajero (ventas) |
| `inventario1` | `password123` | Inventario (productos y stock) |

### 🛑 Detener el Sistema

```bash
./stop.sh
```

Esto detiene el backend y frontend. Opcionalmente puedes mantener las bases de datos corriendo.

---

## 📦 Inicio Manual (Paso a Paso)

Si prefieres control total, sigue estos pasos:

### 1. Levantar Bases de Datos

```bash
docker-compose -f docker-compose-dbs.yml up -d

# Verificar que estén corriendo
docker ps
```

### 2. Configurar Backend

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env (si no existe)
cp .env.example .env

# Iniciar servidor
python run.py
```

El backend estará en: http://localhost:5000

### 3. Configurar Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Crear .env (si no existe)
cp .env.example .env

# Iniciar servidor de desarrollo
npm run dev
```

El frontend estará en: http://localhost:5173

---

## 🗄️ Acceso a Bases de Datos

### PostgreSQL (Fuente de la Verdad)

```bash
# Conexión con psql
psql -h localhost -p 5433 -U admin -d supermercado_db

# Desde Docker
docker exec -it supermercado_postgres psql -U admin -d supermercado_db
```

**Credenciales:**
- Host: `localhost:5433`
- Usuario: `admin`
- Password: `admin123`
- Base de datos: `supermercado_db`

### MongoDB (Tickets de Venta)

```bash
# Conexión con mongosh
mongosh mongodb://admin:admin123@localhost:27018/supermercado_sales?authSource=admin

# Desde Docker
docker exec -it supermercado_mongo mongosh -u admin -p admin123 --authenticationDatabase admin
```

**Credenciales:**
- Host: `localhost:27018`
- Usuario: `admin`
- Password: `admin123`
- Base de datos: `supermercado_sales`

---

## 📊 Estructura del Proyecto

```
supermercado-system/
├── app/                    # Backend Flask
│   ├── blueprints/        # Endpoints REST
│   ├── models/            # Modelos SQLAlchemy
│   ├── middleware/        # Auth y RBAC
│   └── utils/             # Utilidades (DB, logs)
├── frontend/              # Frontend React
│   ├── src/
│   │   ├── components/   # Componentes reutilizables
│   │   ├── pages/        # Páginas principales
│   │   └── services/     # API client
├── worker/               # Worker del Outbox Pattern
├── database/             # Scripts de inicialización
│   ├── postgres/         # Schemas SQL
│   └── mongo/           # Colecciones MongoDB
├── scripts/             # Scripts de backup/restore
├── start.sh            # 🚀 Script de inicio rápido
├── stop.sh             # 🛑 Script de detención
└── docker-compose-dbs.yml
```

---

## 🔧 Comandos Útiles

### Ver Logs

```bash
# Backend
tail -f logs/backend.log

# Frontend
tail -f logs/frontend.log

# Docker (bases de datos)
docker-compose -f docker-compose-dbs.yml logs -f
```

### Reiniciar Solo un Servicio

```bash
# Reiniciar backend
pkill -f "python run.py"
python run.py &

# Reiniciar frontend
cd frontend
npm run dev &
```

### Backups

```bash
# Backup completo (PostgreSQL + MongoDB)
./scripts/backup_all.sh

# Solo PostgreSQL
./scripts/backup_postgres.sh

# Solo MongoDB
./scripts/backup_mongo.sh
```

### Restaurar

```bash
# PostgreSQL
./scripts/restore_postgres.sh backups/postgres/supermercado_YYYYMMDD_HHMMSS.sql.gz

# MongoDB
./scripts/restore_mongo.sh backups/mongo/YYYYMMDD_HHMMSS
```

---

## 🐛 Solución de Problemas

### Puerto 5000 ya está en uso

```bash
# Encontrar y matar el proceso
lsof -ti:5000 | xargs kill -9

# O cambiar el puerto en .env
FLASK_PORT=5001
```

### Puerto 5173 ya está en uso

```bash
# El frontend buscará automáticamente otro puerto
# O especifica uno manualmente:
npm run dev -- --port 5174
```

### Error de conexión a las bases de datos

```bash
# Verificar que los contenedores estén corriendo
docker ps

# Reiniciar contenedores
docker-compose -f docker-compose-dbs.yml restart

# Ver logs de errores
docker-compose -f docker-compose-dbs.yml logs
```

### Permisos denegados en scripts

```bash
chmod +x start.sh stop.sh
chmod +x scripts/*.sh
```

---

## 🎯 Funcionalidades Principales

### 👥 Sistema de Usuarios (RBAC)
- **Gerentes**: Acceso completo al sistema
- **Inventario**: Gestión de productos y stock
- **Cajeros**: Punto de venta

### 📦 Gestión de Productos
- Catálogo de productos con SKU
- Categorización
- Control de precios

### 📋 Control de Inventario (FIFO)
- Lotes con fechas de vencimiento
- Entradas y ajustes de stock
- Alertas de productos próximos a vencer
- Auditoría completa de movimientos

### 🛒 Punto de Venta
- Carrito de compras intuitivo
- Múltiples métodos de pago
- Cálculo automático de impuestos
- Tickets en MongoDB

### 📊 Reportes
- Estadísticas de ventas
- Análisis por cajero
- Métricas de inventario

### ⚙️ Panel de Administración
- Estado del sistema
- Monitoreo del Outbox Pattern
- Métricas generales
- Backups manuales

---

## 🏗️ Arquitectura

### Bases de Datos Duales

- **PostgreSQL**: Fuente de la verdad para productos, inventario, usuarios
- **MongoDB**: Almacenamiento de tickets de venta (consultas rápidas)

### Outbox Pattern

Garantiza consistencia eventual entre PostgreSQL y MongoDB:
1. Venta se registra en PostgreSQL
2. Evento se guarda en `outbox_events`
3. Worker sincroniza con MongoDB en background

### Seguridad

- JWT para autenticación
- RBAC (Role-Based Access Control)
- Passwords hasheados con bcrypt
- CORS configurado

---

## 📝 Desarrollo

### Tests

```bash
# Instalar dependencias de testing
pip install pytest pytest-flask

# Ejecutar tests
pytest
```

### Linting

```bash
# Backend
flake8 app/

# Frontend
cd frontend
npm run lint
```

---

## 📚 Documentación de API

Una vez iniciado el backend, accede a:
- Endpoints disponibles en cada blueprint
- Autenticación vía JWT en header: `Authorization: Bearer <token>`

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login` | Autenticación |
| GET | `/api/products` | Listar productos |
| POST | `/api/inventory/entry` | Registrar entrada |
| POST | `/api/sales` | Crear venta |
| GET | `/api/admin/metrics` | Métricas del sistema |

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea un branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto es de código abierto bajo la licencia MIT.

---

## 📧 Soporte

¿Problemas o preguntas? Abre un issue en el repositorio.

---

**¡Listo para usar! 🎉**

Simplemente ejecuta `./start.sh` y comienza a trabajar.