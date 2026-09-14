$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
Write-Host ('Entorno Python: ' + (Test-Path -LiteralPath $Python))
Write-Host ('Dependencias web: ' + (Test-Path -LiteralPath (Join-Path $ProjectRoot 'frontend\node_modules')))
Write-Host ('Bundle web: ' + (Test-Path -LiteralPath (Join-Path $ProjectRoot 'frontend\dist\index.html')))
try {
    $status = Invoke-RestMethod 'http://127.0.0.1:8000/api/refresh/status' -TimeoutSec 5
    $status | ConvertTo-Json -Depth 5
    (Invoke-RestMethod 'http://127.0.0.1:8000/api/providers/status' -TimeoutSec 5).providers | Select-Object provider,status,configured,requests_remaining
} catch { Write-Host 'Backend cerrado o no disponible. Ejecuta start.ps1 y revisa .runtime/.' }
