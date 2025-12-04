@echo off
REM ============================================
REM Script de Inicio Rápido para Windows
REM Sistema de Supermercado
REM ============================================

echo ╔════════════════════════════════════════════════╗
echo ║   🛒 Sistema de Supermercado - Inicio Rápido   ║
echo ╚════════════════════════════════════════════════╝
echo.

REM ====================================
REM 1. VERIFICAR DEPENDENCIAS
REM ====================================
echo → Verificando dependencias...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Docker no está instalado
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Python no está instalado
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Node.js no está instalado
    pause
    exit /b 1
)

echo ✓ Todas las dependencias están instaladas
echo.

REM ====================================
REM 2. CREAR ARCHIVO .env
REM ====================================
if not exist .env (
    echo → Creando archivo .env...
    copy .env.example .env
    echo ✓ Archivo .env creado
)
echo.

REM ====================================
REM 3. LEVANTAR BASES DE DATOS
REM ====================================
echo → Levantando bases de datos (PostgreSQL y MongoDB)...
docker-compose -f docker-compose-dbs.yml up -d

echo → Esperando a que las bases de datos estén listas...
timeout /t 15 /nobreak >nul

echo ✓ Bases de datos iniciadas
echo.

REM ====================================
REM 4. CONFIGURAR BACKEND
REM ====================================
echo → Configurando backend...

if not exist venv (
    echo   Creando entorno virtual...
    python -m venv venv
)

echo   Activando entorno virtual...
call venv\Scripts\activate.bat

echo   Instalando dependencias Python...
pip install -q -r requirements.txt

echo ✓ Backend configurado
echo.

REM ====================================
REM 5. INICIAR BACKEND
REM ====================================
echo → Iniciando servidor backend...

REM Crear directorio de logs
if not exist logs mkdir logs

REM Iniciar backend en nueva ventana
start "Backend - Flask" cmd /k "venv\Scripts\activate.bat && python run.py"

echo ✓ Backend iniciado en nueva ventana
timeout /t 5 /nobreak >nul
echo.

REM ====================================
REM 6. CONFIGURAR FRONTEND
REM ====================================
echo → Configurando frontend...
cd frontend

if not exist .env (
    copy .env.example .env
)

if not exist node_modules (
    echo   Instalando dependencias npm...
    call npm install
)

echo ✓ Frontend configurado
echo.

REM ====================================
REM 7. INICIAR FRONTEND
REM ====================================
echo → Iniciando servidor frontend...

REM Iniciar frontend en nueva ventana
start "Frontend - React" cmd /k "npm run dev"

cd ..

echo ✓ Frontend iniciado en nueva ventana
echo.

REM ====================================
REM 8. RESUMEN
REM ====================================
timeout /t 8 /nobreak >nul

echo.
echo ╔════════════════════════════════════════════════╗
echo ║        ✅ SISTEMA INICIADO CORRECTAMENTE        ║
echo ╚════════════════════════════════════════════════╝
echo.
echo 📍 URLs de Acceso:
echo    Frontend:  http://localhost:5173
echo    Backend:   http://localhost:5000/health
echo.
echo 👤 Usuarios de Prueba:
echo    Gerente:    gerente1 / password123
echo    Cajero:     cajero1 / password123
echo    Inventario: inventario1 / password123
echo.
echo 📊 Bases de Datos:
echo    PostgreSQL: localhost:5433 (admin/admin123)
echo    MongoDB:    localhost:27018 (admin/admin123)
echo.
echo 🛑 Para detener el sistema:
echo    Cierra las ventanas de Backend y Frontend
echo    Ejecuta: docker-compose -f docker-compose-dbs.yml down
echo.

REM Abrir navegador automáticamente
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo ✓ Navegador abierto automáticamente
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul