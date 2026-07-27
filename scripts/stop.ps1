param(
    [switch]$StopDocker
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
    Write-Host "Docker Desktop no esta instalado." -ForegroundColor Yellow
    exit 0
}

& $Docker info *> $null
if ($LASTEXITCODE -eq 0) {
    & $Docker compose stop --timeout 20
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($StopDocker) {
    & $Docker desktop stop
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host "MatchLab y Docker Desktop estan detenidos. Modo juego activo." -ForegroundColor Green
} else {
    Write-Host "MatchLab esta detenido; los datos permanecen guardados." -ForegroundColor Green
}
