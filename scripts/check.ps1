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

$ParserErrors = @()
Get-ChildItem (Join-Path $Root "scripts") -Filter "*.ps1" | ForEach-Object {
    $Tokens = $null
    $FileErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName,
        [ref]$Tokens,
        [ref]$FileErrors
    ) | Out-Null
    $ParserErrors += $FileErrors
}
if ($ParserErrors.Count -gt 0) {
    $ParserErrors | Format-List
    exit 1
}

& $Docker compose config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose build api migrate worker beat web
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose run --rm -e RUFF_CACHE_DIR=/tmp/ruff api `
    ruff check apps/api packages migrations tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose run --rm -e MYPY_CACHE_DIR=/tmp/mypy api `
    mypy apps/api packages
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Docker compose run --rm api pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Scripts, configuracion, compilacion, lint, tipos y tests completados." -ForegroundColor Green
