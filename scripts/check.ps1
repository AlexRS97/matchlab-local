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
    Write-Host "Docker no esta disponible. Instala Docker Desktop para ejecutar la validacion." -ForegroundColor Red
    exit 1
}

& $Docker compose config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose build api migrate worker beat web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose run --rm api ruff check apps/api packages migrations tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose run --rm api pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Configuracion, compilacion, lint y tests completados." -ForegroundColor Green
