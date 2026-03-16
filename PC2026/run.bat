@echo off
title PC2026 — Dashboard Plan de Cuentas

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   PC2026 — Dashboard Plan de Cuentas     ║
echo  ║   http://localhost:8501                  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Verificar que Docker este corriendo
docker info >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Docker no esta corriendo. Abre Docker Desktop primero.
    pause
    exit /b 1
)

:: Construir imagen si no existe o si hubo cambios
echo  Verificando imagen...
docker compose build --quiet

echo  Iniciando app...
echo  Presiona Ctrl+C para detener.
echo.

:: Arrancar — cuando se detiene (Ctrl+C o cierre) cae al siguiente comando
docker compose up

:: Al salir: eliminar contenedor automaticamente
echo.
echo  Deteniendo y eliminando contenedor...
docker compose down

echo  Contenedor eliminado. Hasta luego.
timeout /t 2 >nul
