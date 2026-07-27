[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("Start", "Stop", "Status", "Update", "Open", "Logs")]
    [string]$Action,
    [switch]$StopDocker,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LogDirectory = Join-Path $env:LOCALAPPDATA "MatchLab"
$LogFile = Join-Path $LogDirectory "controller.log"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
Set-Location $Root

function Write-ControlLog {
    param([string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $LogFile -Value "[$timestamp] $Message" -Encoding UTF8
}

function Get-DockerPath {
    $command = Get-Command docker -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $desktopDocker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $desktopDocker) {
        return $desktopDocker
    }
    throw "Docker Desktop no esta instalado."
}

function Invoke-DockerLogged {
    param(
        [Parameter(Mandatory)][string]$Docker,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = & $Docker @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    foreach ($line in $output) {
        Write-ControlLog "$line"
    }
    return $exitCode
}

function Test-Endpoint {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [int]$TimeoutMilliseconds = 2500
    )

    try {
        $request = [System.Net.HttpWebRequest]::Create($Uri)
        $request.Proxy = $null
        $request.Timeout = $TimeoutMilliseconds
        $request.ReadWriteTimeout = $TimeoutMilliseconds
        $response = $request.GetResponse()
        try {
            return [int]$response.StatusCode -eq 200
        } finally {
            $response.Dispose()
        }
    } catch {
        return $false
    }
}

function Test-Api {
    return Test-Endpoint -Uri "http://127.0.0.1:8000/health"
}

function Test-Web {
    return Test-Endpoint -Uri "http://127.0.0.1:3000" -TimeoutMilliseconds 3500
}

function Wait-ForApplication {
    param([int]$TimeoutSeconds = 120)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Test-Api) -and (Test-Web)) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Start-MatchLab {
    $docker = Get-DockerPath
    if ((Test-Api) -and (Test-Web)) {
        Write-ControlLog "La aplicacion ya estaba iniciada."
        return
    }

    Write-ControlLog "Iniciando Docker Desktop."
    $desktopExitCode = Invoke-DockerLogged `
        -Docker $docker `
        -Arguments @("desktop", "start")
    if ($desktopExitCode -ne 0) {
        $desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path $desktop)) {
            throw "No se encuentra Docker Desktop."
        }
        Start-Process -FilePath $desktop -WindowStyle Hidden
    }

    $dockerReady = $false
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        & $docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $dockerReady) {
        throw "Docker Desktop no ha respondido en 120 segundos."
    }

    if (-not (Test-Path (Join-Path $Root ".env"))) {
        Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    }

    Write-ControlLog "Levantando los servicios de MatchLab."
    $composeExitCode = Invoke-DockerLogged `
        -Docker $docker `
        -Arguments @("compose", "up", "-d", "--no-build")
    if ($composeExitCode -ne 0) {
        Write-ControlLog "Faltaba alguna imagen; se inicia una compilacion unica."
        $buildExitCode = Invoke-DockerLogged `
            -Docker $docker `
            -Arguments @("compose", "up", "-d", "--build")
        if ($buildExitCode -ne 0) {
            throw "No se pudieron iniciar los contenedores."
        }
    }

    if (-not (Wait-ForApplication)) {
        throw "Los servicios arrancaron, pero la aplicacion no esta saludable."
    }
    try {
        $response = Invoke-RestMethod `
            -Method Post `
            -Uri "http://localhost:8000/api/v1/admin/ingestion/run-if-stale" `
            -TimeoutSec 5
        Write-ControlLog "Comprobacion automatica encolada: $($response.task_id)"
    } catch {
        Write-ControlLog "No se pudo encolar la comprobacion automatica: $($_.Exception.Message)"
    }
    Write-ControlLog "MatchLab iniciado correctamente."
}

function Stop-MatchLab {
    $stopScript = Join-Path $PSScriptRoot "stop.ps1"
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$stopScript`""
    if ($StopDocker) {
        $arguments += " -StopDocker"
    }
    $process = Start-Process `
        -FilePath $PowerShell `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($process.ExitCode -ne 0) {
        throw "No se pudo detener MatchLab correctamente."
    }
    Write-ControlLog "MatchLab detenido. StopDocker=$StopDocker"
}

try {
    switch ($Action) {
        "Start" {
            Start-MatchLab
            if (-not $NoBrowser) {
                Start-Process "http://localhost:3000"
            }
        }
        "Stop" {
            Stop-MatchLab
        }
        "Status" {
            if ((Test-Api) -and (Test-Web)) {
                Write-Output "running"
                exit 0
            }
            Write-Output "stopped"
            exit 1
        }
        "Update" {
            Start-MatchLab
            $response = Invoke-RestMethod `
                -Method Post `
                -Uri "http://localhost:8000/api/v1/admin/ingestion/run" `
                -TimeoutSec 10
            Write-ControlLog "Actualizacion encolada: $($response.task_id)"
            Write-Output $response.task_id
        }
        "Open" {
            Start-MatchLab
            Start-Process "http://localhost:3000"
        }
        "Logs" {
            $docker = Get-DockerPath
            $arguments = (
                "-NoExit -Command `"& '$docker' compose logs --tail=100 -f api worker web`""
            )
            Start-Process `
                -FilePath $PowerShell `
                -ArgumentList $arguments `
                -WorkingDirectory $Root
        }
    }
} catch {
    Write-ControlLog "ERROR: $($_.Exception.Message)"
    Write-Error $_.Exception.Message
    exit 1
}
