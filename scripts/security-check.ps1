param([switch]$ExternalAudits)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Portable = Join-Path $ProjectRoot '.tools\gitleaks\gitleaks.exe'
$Gitleaks = if (Test-Path -LiteralPath $Portable) { $Portable } else { (Get-Command gitleaks -ErrorAction Stop).Source }
Push-Location $ProjectRoot
try {
    $Candidates = @(git ls-files --cached --others --exclude-standard)
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo revisar el indice Git.' }
    $Forbidden = @($Candidates | Where-Object {
        ($_ -match '(^|/)(\.env($|\.)|[^/]+\.(pem|key|p12|pfx|duckdb|wal)$)' -and $_ -notmatch '\.env\.example$') -or
        $_ -match '(^|/)(\.venv|\.tools|\.runtime|node_modules|data)/'
    })
    if ($Forbidden.Count) { throw ('Archivos privados o generados incluidos en Git: ' + ($Forbidden -join ', ')) }
    & $Gitleaks git . --redact --no-banner
    if ($LASTEXITCODE -ne 0) { throw 'Gitleaks ha detectado problemas en el historial.' }
    git diff --cached --no-ext-diff | & $Gitleaks stdin --redact --no-banner
    if ($LASTEXITCODE -ne 0) { throw 'Gitleaks ha detectado problemas en los cambios preparados.' }
    if ($ExternalAudits) {
        $Python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
        & $Python -m pip_audit --skip-editable --progress-spinner off
        if ($LASTEXITCODE -ne 0) { throw 'La auditoria Python no ha pasado.' }
        $NodeDirectory = Join-Path $ProjectRoot '.tools\node-v22.16.0-win-x64'
        if (Test-Path -LiteralPath $NodeDirectory) { $env:PATH = $NodeDirectory + ';' + $env:PATH }
        Push-Location frontend
        try { & npm.cmd audit --audit-level=high; if ($LASTEXITCODE -ne 0) { throw 'La auditoria web no ha pasado.' } } finally { Pop-Location }
    }
    Write-Host 'Comprobaciones de seguridad completadas.' -ForegroundColor Green
} finally { Pop-Location }
