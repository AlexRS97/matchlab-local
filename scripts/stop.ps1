$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$ApiMarker = Join-Path $ProjectRoot 'backend\serve.py'
$WebMarker = Join-Path $ProjectRoot 'frontend\node_modules\vite\bin\vite.js'
# Windows virtual-environment launchers can create a child interpreter. Check the
# absolute workspace marker in every command line before stopping either process.
$AllProcesses = @(Get-CimInstance Win32_Process)
$Processes = @($AllProcesses | Where-Object {
    ($_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($ApiMarker)) -or
    ($_.Name -eq 'node.exe' -and $_.CommandLine -and $_.CommandLine.Contains($WebMarker)) -or
    ($_.Name -eq 'python.exe' -and $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith($ProjectRoot + '\', [System.StringComparison]::OrdinalIgnoreCase) -and
        $_.CommandLine -match '\s-m\s+app\.(learning|jobs\.daily_cli)(\s|$)')
})
# Include children such as the virtual-environment interpreter or a training worker.
# Only descendants of processes identified above belong to this shutdown.
$Owned = @{}
foreach ($process in $Processes) { $Owned[$process.ProcessId] = $process }
do {
    $Added = $false
    foreach ($process in $AllProcesses) {
        if (-not $Owned.ContainsKey($process.ProcessId) -and $Owned.ContainsKey($process.ParentProcessId) -and
            $process.CreationDate -ge $Owned[$process.ParentProcessId].CreationDate) {
            $Owned[$process.ProcessId] = $process
            $Added = $true
        }
    }
} while ($Added)
foreach ($process in ($Owned.Values | Sort-Object CreationDate -Descending)) {
    $Current = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $process.ProcessId) -ErrorAction SilentlyContinue
    if ($Current -and $Current.CreationDate -eq $process.CreationDate) {
        try {
            Stop-Process -Id $process.ProcessId -ErrorAction Stop
        } catch {
            # A child may exit while its parent is being stopped.
            if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) { throw }
        }
    }
}
# Closing the tray also stops its timers; it never restarts the app after shutdown.
try {
    $ExitEvent = [System.Threading.EventWaitHandle]::OpenExisting('Local\MatchLab.Tray.Exit')
    try { $ExitEvent.Set() | Out-Null } finally { $ExitEvent.Dispose() }
} catch [System.Threading.WaitHandleCannotBeOpenedException] {
    # The optional tray is not running.
}
foreach ($name in @('backend.pid','frontend.pid')) {
    $path = Join-Path $ProjectRoot ('.runtime\' + $name)
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
}
Write-Host 'MatchLab detenido: servidor, web y trabajos del proyecto cerrados. Datos y modelos guardados.' -ForegroundColor Green
