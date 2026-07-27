$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Failures = 0

function Write-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    if ($Passed) {
        Write-Host "[OK]   $Name - $Detail" -ForegroundColor Green
    } else {
        Write-Host "[FALLO] $Name - $Detail" -ForegroundColor Red
        $script:Failures++
    }
}

$VirtualizationEnabled = Get-CimInstance Win32_Processor |
    Select-Object -First 1 -ExpandProperty VirtualizationFirmwareEnabled
$VirtualizationDetail = if ($VirtualizationEnabled) {
    "SVM/AMD-V habilitado"
} else {
    "Activa UEFI > Advanced > CPU Configuration > SVM Mode"
}
Write-Check "Virtualizacion" $VirtualizationEnabled $VirtualizationDetail

& wsl --status *> $null
$WslReady = $LASTEXITCODE -eq 0
$WslDetail = if ($WslReady) { "instalado" } else { "no disponible" }
Write-Check "WSL 2" $WslReady $WslDetail

$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$Docker = if ($DockerCommand) {
    $DockerCommand.Source
} elseif (Test-Path "C:\Program Files\Docker\Docker\resources\bin\docker.exe") {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
} else {
    $null
}
$DockerCliReady = $null -ne $Docker
$DockerCliDetail = if ($DockerCliReady) { $Docker } else { "no instalado" }
Write-Check "Docker CLI" $DockerCliReady $DockerCliDetail

$DockerReady = $false
if ($Docker) {
    $DockerReady = $VirtualizationEnabled -and (Test-Path "\\.\pipe\dockerDesktopLinuxEngine")
}
$DockerDetail = if ($DockerReady) { "en ejecucion" } else { "detenido o bloqueado" }
Write-Check "Motor Docker" $DockerReady $DockerDetail

$EnvReady = Test-Path ".env"
$EnvDetail = if ($EnvReady) { "presente" } else { "copia .env.example a .env" }
Write-Check "Configuracion .env" $EnvReady $EnvDetail

if ($DockerReady) {
    & $Docker compose config --quiet
    $ComposeReady = $LASTEXITCODE -eq 0
    $ComposeDetail = if ($ComposeReady) { "configuracion valida" } else { "configuracion invalida" }
    Write-Check "Docker Compose" $ComposeReady $ComposeDetail
}

if ($Failures -eq 0) {
    Write-Host "`nEl equipo esta preparado. Ejecuta .\scripts\start.ps1" -ForegroundColor Green
    exit 0
}

Write-Host "`nHay $Failures comprobaciones pendientes." -ForegroundColor Yellow
exit 1
