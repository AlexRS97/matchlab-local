param([switch]$WaitForCompletion)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDirectory = Join-Path $ProjectRoot '.runtime'
New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
$LogFile = Join-Path $RuntimeDirectory 'daily-refresh.log'
try {
    $ApiRunning = $false
    try { $ApiRunning = (Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2).application -eq 'matchlab-local' } catch { }
    if (-not $ApiRunning) {
        $Python = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $Python)) { throw 'Instala primero MatchLab con start.ps1 -Setup.' }
        $process = Start-Process -FilePath $Python -ArgumentList '-u -m app.jobs.daily_cli' -WorkingDirectory (Join-Path $ProjectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeDirectory 'daily-worker.log') -RedirectStandardError (Join-Path $RuntimeDirectory 'daily-worker-error.log')
        $null = $process.Handle
        $process.WaitForExit()
        $process.Refresh()
        if ($process.ExitCode -ne 0) { throw 'El trabajo diario ha fallado. Revisa .runtime/daily-worker-error.log.' }
        Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ((Get-Date -Format o) + ' Trabajo diario finalizado. Estado detallado: daily-worker.log.')
        Write-Host 'Ciclo diario finalizado. Los partidos y analisis disponibles quedan guardados.'
        exit 0
    }
    Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/refresh/daily' -TimeoutSec 10 | Out-Null
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ((Get-Date -Format o) + ' Actualizacion diaria de partidos y analisis solicitada.')
    if ($WaitForCompletion) {
        $Deadline = (Get-Date).AddMinutes(30)
        do {
            Start-Sleep -Seconds 5
            $status = Invoke-RestMethod 'http://127.0.0.1:8000/api/refresh/status' -TimeoutSec 10
        } while (($status.job.running -or $status.learning.running) -and (Get-Date) -lt $Deadline)
        if ($status.job.running -or $status.learning.running) { throw 'La actualizacion sigue en curso; consulta el estado en la aplicacion.' }
        Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ($status | ConvertTo-Json -Depth 6 -Compress)
        if ($status.job.errors.Count -gt 0 -or $status.learning.errors.Count -gt 0) { Write-Warning 'Actualizacion parcial. Revisa los proveedores y .runtime/daily-refresh.log.' }
    }
    Write-Host 'Actualizacion diaria iniciada. Partidos y analisis se recalculan para hoy.'
} catch {
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value ((Get-Date -Format o) + ' ERROR: ' + $_.Exception.Message)
    throw
}
