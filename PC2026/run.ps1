$Host.UI.RawUI.WindowTitle = "PC2026 Dashboard"

Write-Host ""
Write-Host "  PC2026 - Dashboard Plan de Cuentas" -ForegroundColor Cyan
Write-Host "  http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

# Verificar Docker
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Docker no esta corriendo. Abre Docker Desktop primero." -ForegroundColor Red
    Read-Host "  Presiona Enter para salir"
    exit 1
}

# Construir imagen si cambio el codigo
Write-Host "  Verificando imagen..." -ForegroundColor Yellow
docker compose build --quiet

Write-Host "  Iniciando app - Ctrl+C para detener" -ForegroundColor Green
Write-Host ""

try {
    docker compose up
} finally {
    Write-Host ""
    Write-Host "  Eliminando contenedor..." -ForegroundColor Yellow
    docker compose down
    Write-Host "  Listo. Hasta luego." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
}
