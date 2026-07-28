param(
    [switch]$ExternalAudits
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$Docker = if ($DockerCommand) {
    $DockerCommand.Source
} elseif (Test-Path "C:\Program Files\Docker\Docker\resources\bin\docker.exe") {
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
} else {
    throw "Docker no está disponible."
}

Set-Location $Root
$GitleaksImage = "ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
$PythonImage = "python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
$NodeImage = "node:22-alpine@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2"

Write-Host "Escaneando todo el historial Git en busca de secretos..." -ForegroundColor Cyan
& $Docker run --rm --volume "${Root}:/repo:ro" $GitleaksImage `
    git /repo --redact --no-banner
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Docker run --rm --volume "${Root}:/repo:ro" $GitleaksImage `
    dir /repo --redact --no-banner
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $ExternalAudits) {
    Write-Host "Escaneo local completado." -ForegroundColor Green
    Write-Host "Las auditorías externas están desactivadas: usa -ExternalAudits solo tras autorizar el envío de nombres y versiones de dependencias a PyPI, npm y Docker Scout." -ForegroundColor Yellow
    exit 0
}

Write-Host "Auditando la resolución de dependencias Python..." -ForegroundColor Cyan
& $Docker run --rm --volume "${Root}:/repo:ro" --workdir /repo $PythonImage `
    sh -c "python -m pip install --quiet pip-audit==2.10.1 && pip-audit . --progress-spinner off"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Auditando dependencias Node.js de producción..." -ForegroundColor Cyan
$Web = Join-Path $Root "apps\web"
& $Docker run --rm --volume "${Web}:/source:ro" --workdir /tmp/app $NodeImage `
    sh -c "cp /source/package.json /source/package-lock.json . && npm ci --omit=optional --ignore-scripts --quiet && npm audit --omit=dev --audit-level=high"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Auditando imágenes construidas con Docker Scout..." -ForegroundColor Cyan
foreach ($Image in @("football-analytics-api:latest", "football-analytics-web:latest")) {
    & $Docker scout cves "local://${Image}" --only-severity critical,high --exit-code
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Auditoría de secretos, dependencias e imágenes completada." -ForegroundColor Green
