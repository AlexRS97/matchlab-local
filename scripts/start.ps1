param(
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$Docker = if ($DockerCommand) {
    $DockerCommand.Source
} elseif (Test-Path "C:\Program Files\Docker\Docker\resources\bin\docker.exe") {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
} else {
    $null
}

if (-not $Docker) {
    Write-Host "Docker Desktop no esta instalado o no esta en PATH." -ForegroundColor Red
    Write-Host "Instalalo desde https://www.docker.com/products/docker-desktop/ y vuelve a ejecutar este script."
    exit 1
}

$VirtualizationEnabled = Get-CimInstance Win32_Processor |
    Select-Object -First 1 -ExpandProperty VirtualizationFirmwareEnabled
if (-not $VirtualizationEnabled) {
    Write-Host "La virtualizacion del procesador esta desactivada." -ForegroundColor Red
    Write-Host "En ASUS: UEFI/BIOS > F7 > Advanced > CPU Configuration > SVM Mode > Enabled."
    Write-Host "Guarda con F10, reinicia Windows y vuelve a ejecutar este script."
    exit 1
}

& wsl --status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "WSL 2 no esta disponible. Ejecuta 'wsl --install' como administrador y reinicia." -ForegroundColor Red
    exit 1
}

$DockerPipe = "\\.\pipe\dockerDesktopLinuxEngine"
$DockerReady = Test-Path $DockerPipe
if (-not $DockerReady) {
    $DockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $DockerDesktop)) {
        Write-Host "Docker Desktop esta instalado, pero no se encuentra su ejecutable." -ForegroundColor Red
        exit 1
    }
    Write-Host "Iniciando Docker Desktop..." -ForegroundColor Cyan
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Docker desktop start *> $null
    $DesktopStartExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousPreference
    if ($DesktopStartExitCode -ne 0) {
        Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
    }
    for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
        Start-Sleep -Seconds 2
        if (Test-Path $DockerPipe) {
            $DockerReady = $true
            break
        }
    }
    if (-not $DockerReady) {
        Write-Host "Docker no ha iniciado en 120 segundos. Abre Docker Desktop y revisa su aviso." -ForegroundColor Red
        exit 1
    }
}
& $Docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "El canal de Docker existe, pero el motor no responde." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    & (Join-Path $PSScriptRoot "new-env.ps1")
    Write-Host "Se ha creado .env con secretos locales aleatorios." -ForegroundColor Yellow
    Write-Host "Puedes anadir API_FOOTBALL_KEY cuando tengas la clave." -ForegroundColor Yellow
}

if ($NoBuild) {
    & $Docker compose up -d
} else {
    & $Docker compose up -d --build
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "No se pudieron iniciar los contenedores." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Esperando a la API..." -ForegroundColor Cyan
$ApiReady = $false
for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    try {
        $Response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2
        if ($Response.StatusCode -eq 200) {
            $ApiReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ApiReady) {
    Write-Host "Los contenedores arrancaron, pero la API no esta saludable." -ForegroundColor Yellow
    & $Docker compose ps
    Write-Host "Revisa los logs con: docker compose logs api migrate"
    exit 1
}

try {
    Invoke-RestMethod `
        -Method Post `
        -Uri "http://localhost:8000/api/v1/admin/ingestion/run-if-stale" `
        -TimeoutSec 5 | Out-Null
    Write-Host "Comprobacion automatica de datos iniciada." -ForegroundColor Cyan
} catch {
    Write-Host "La comprobacion automatica no pudo iniciarse; puedes usar Actualizar datos." -ForegroundColor Yellow
}

Write-Host "Aplicacion: http://localhost:3000" -ForegroundColor Green
Write-Host "API:        http://localhost:8000/docs" -ForegroundColor Green
& $Docker compose ps
