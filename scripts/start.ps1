param([switch]$Setup, [switch]$NoBuild, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDirectory = Join-Path $ProjectRoot '.runtime'
$BackendDirectory = Join-Path $ProjectRoot 'backend'
$FrontendDirectory = Join-Path $ProjectRoot 'frontend'
$Python = Join-Path $BackendDirectory '.venv\Scripts\python.exe'
$PortablePython = Join-Path $ProjectRoot '.tools\python\cpython-3.12.13-windows-x86_64-none\python.exe'
$NodeDirectory = Join-Path $ProjectRoot '.tools\node-v22.16.0-win-x64'
if (Test-Path -LiteralPath (Join-Path $NodeDirectory 'node.exe')) { $env:PATH = $NodeDirectory + ';' + $env:PATH }
$Node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
if (-not $Node) { throw 'Instala Node.js 22 y vuelve a ejecutar start.ps1 -Setup.' }
New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
if ($Setup) {
    if (-not (Test-Path -LiteralPath $Python)) {
        $BasePython = if (Test-Path -LiteralPath $PortablePython) { $PortablePython } else { (Get-Command python.exe -ErrorAction Stop).Source }
        & $BasePython -m venv (Join-Path $BackendDirectory '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python 3.12.' }
    }
    & $Python -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar pip.' }
    & $Python -m pip install -c (Join-Path $BackendDirectory 'constraints.txt') -e ($BackendDirectory + '[dev,learning]')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias Python.' }
    Push-Location $FrontendDirectory
    try { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci ha fallado.' } } finally { Pop-Location }
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.env')) -and -not (Test-Path -LiteralPath (Join-Path $BackendDirectory '.env'))) {
        Copy-Item -LiteralPath (Join-Path $BackendDirectory '.env.example') -Destination (Join-Path $BackendDirectory '.env')
    }
}
if (-not (Test-Path -LiteralPath $Python)) { throw 'Falta backend/.venv. Ejecuta .\start.ps1 -Setup.' }
$Vite = Join-Path $FrontendDirectory 'node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $Vite)) { throw 'Faltan dependencias web. Ejecuta .\start.ps1 -Setup.' }
function Test-MatchLabApi {
    try { return (Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2).application -eq 'matchlab-local' } catch { return $false }
}
function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $Port); return $true } catch { return $false } finally { $client.Dispose() }
}
if (-not (Test-MatchLabApi)) {
    if (Test-Port 8000) { throw 'El puerto 8000 lo ocupa otro servicio. Detenlo antes de iniciar MatchLab.' }
    $ServerScript = Join-Path $BackendDirectory 'serve.py'
    $process = Start-Process -FilePath $Python -ArgumentList ('-u "' + $ServerScript + '"') -WorkingDirectory $BackendDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeDirectory 'backend.log') -RedirectStandardError (Join-Path $RuntimeDirectory 'backend-error.log')
    try { $process.PriorityClass = 'BelowNormal' } catch { Write-Warning 'No se pudo reducir la prioridad del proceso.' }
    $process.Id | Set-Content -LiteralPath (Join-Path $RuntimeDirectory 'backend.pid')
}
$WebStarted = $false
if (Test-Port 3000) {
    try { $WebStarted = (Invoke-WebRequest 'http://127.0.0.1:3000' -UseBasicParsing -TimeoutSec 3).Content.Contains('<title>MatchLab') } catch { }
    if (-not $WebStarted) { throw 'El puerto 3000 lo ocupa otro servicio.' }
}
if (-not $WebStarted) {
    $Bundle = Join-Path $FrontendDirectory 'dist\index.html'
    $NeedsBuild = -not (Test-Path -LiteralPath $Bundle)
    if (-not $NeedsBuild -and -not $NoBuild) {
        $BuiltAt = (Get-Item -LiteralPath $Bundle).LastWriteTimeUtc
        $Inputs = @(Get-ChildItem -LiteralPath (Join-Path $FrontendDirectory 'src') -Recurse -File)
        $Inputs += @(Get-ChildItem -LiteralPath $FrontendDirectory -File)
        if (Test-Path -LiteralPath (Join-Path $FrontendDirectory 'public')) {
            $Inputs += @(Get-ChildItem -LiteralPath (Join-Path $FrontendDirectory 'public') -Recurse -File)
        }
        $NeedsBuild = @($Inputs | Where-Object { $_.LastWriteTimeUtc -gt $BuiltAt }).Count -gt 0
    }
    if ($NeedsBuild) {
        Push-Location $FrontendDirectory
        try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'La compilacion web ha fallado.' } } finally { Pop-Location }
    }
    $process = Start-Process -FilePath $Node -ArgumentList ('"' + $Vite + '" preview --host 127.0.0.1 --port 3000 --strictPort') -WorkingDirectory $FrontendDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeDirectory 'frontend.log') -RedirectStandardError (Join-Path $RuntimeDirectory 'frontend-error.log')
    try { $process.PriorityClass = 'BelowNormal' } catch { Write-Warning 'No se pudo reducir la prioridad del proceso.' }
    $process.Id | Set-Content -LiteralPath (Join-Path $RuntimeDirectory 'frontend.pid')
}
for ($attempt=0; $attempt -lt 25; $attempt++) {
    if ((Test-MatchLabApi) -and (Test-Port 3000)) {
        Write-Host 'MatchLab: http://localhost:3000 | API: http://localhost:8000/docs' -ForegroundColor Green
        Write-Host 'Inicio manual. Actualizaciones solo mientras este abierto; entrenamiento desde Model Lab.'
        Write-Host 'Antes de jugar: ejecuta .\stop.ps1. Cerrar la pestana no detiene MatchLab. Logs: .runtime/'
        if (-not $NoBrowser) { Start-Process 'http://localhost:3000' }
        exit 0
    }
    Start-Sleep -Seconds 1
}
throw 'No se completo el arranque. Revisa .runtime/backend-error.log y frontend-error.log.'
