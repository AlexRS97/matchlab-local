$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$NodeDirectory = Join-Path $ProjectRoot '.tools\node-v22.16.0-win-x64'
if (Test-Path -LiteralPath $NodeDirectory) { $env:PATH = $NodeDirectory + ';' + $env:PATH }
$Python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
$ParserErrors = @()
Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' | ForEach-Object {
    $tokens=$null; $errors=$null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors) | Out-Null
    $ParserErrors += $errors
}
if ($ParserErrors.Count) { $ParserErrors | Format-List; exit 1 }
Push-Location (Join-Path $ProjectRoot 'backend')
try {
    & $Python -m ruff check app tests serve.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python -m mypy app
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $Python -m pytest -o cache_dir=../.runtime/pytest-cache
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
Push-Location (Join-Path $ProjectRoot 'frontend')
try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } finally { Pop-Location }
Write-Host 'Lint, tipos, pruebas y compilacion correctos.' -ForegroundColor Green
