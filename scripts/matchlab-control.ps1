[CmdletBinding()]
param([Parameter(Mandatory)][ValidateSet('Start','Stop','Status','Update','Open','Logs')][string]$Action,[switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PowerShellExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
function Start-App {
    $script = Join-Path $PSScriptRoot 'start.ps1'
    $process = Start-Process -FilePath $PowerShellExe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $script + '" -NoBrowser') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    $null = $process.Handle
    $process.WaitForExit()
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw 'No se pudo iniciar MatchLab. Revisa .runtime.' }
}
switch ($Action) {
    'Start' { Start-App; if (-not $NoBrowser) { Start-Process 'http://localhost:3000' } }
    'Open' { Start-App; Start-Process 'http://localhost:3000' }
    'Stop' { & (Join-Path $PSScriptRoot 'stop.ps1') }
    'Status' {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2
            if ($health.application -eq 'matchlab-local') { Write-Output 'running'; exit 0 }
        } catch { }
        Write-Output 'stopped'; exit 1
    }
    'Update' {
        Start-App
        Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/refresh' -TimeoutSec 10 | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/learning/update' -TimeoutSec 10 | Out-Null
    }
    'Logs' { Start-Process explorer.exe -ArgumentList ('"' + (Join-Path $ProjectRoot '.runtime') + '"') }
}
