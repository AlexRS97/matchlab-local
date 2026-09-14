param([switch]$NoBrowser)
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$Root = Split-Path -Parent $PSScriptRoot
$ControlScript = Join-Path $PSScriptRoot "matchlab-control.ps1"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$IconPath = Join-Path $env:LOCALAPPDATA "MatchLab\MatchLab.ico"
$script:Busy = $false

$createdNew = $false
$mutex = [System.Threading.Mutex]::new(
    $true,
    "Local\MatchLab.Tray.Singleton",
    [ref]$createdNew
)
$activationEvent = [System.Threading.EventWaitHandle]::new(
    $false,
    [System.Threading.EventResetMode]::AutoReset,
    "Local\MatchLab.Tray.Activate"
)
$exitEvent = [System.Threading.EventWaitHandle]::new(
    $false,
    [System.Threading.EventResetMode]::AutoReset,
    "Local\MatchLab.Tray.Exit"
)

if (-not $createdNew) {
    $activationEvent.Set() | Out-Null
    $activationEvent.Dispose()
    $exitEvent.Dispose()
    $mutex.Dispose()
    exit 0
}

$notifyIcon = New-Object System.Windows.Forms.NotifyIcon
$loadedIcon = $null
if (Test-Path $IconPath) {
    $loadedIcon = [System.Drawing.Icon]::new($IconPath)
    $notifyIcon.Icon = $loadedIcon
} else {
    $notifyIcon.Icon = [System.Drawing.SystemIcons]::Application
}
$notifyIcon.Text = "MatchLab"
$notifyIcon.Visible = $true

$menu = New-Object System.Windows.Forms.ContextMenuStrip
$statusItem = [System.Windows.Forms.ToolStripMenuItem]::new("Estado: comprobando...")
$statusItem.Enabled = $false
$openItem = [System.Windows.Forms.ToolStripMenuItem]::new("Abrir MatchLab")
$updateItem = [System.Windows.Forms.ToolStripMenuItem]::new("Actualizar datos de hoy")
$startItem = [System.Windows.Forms.ToolStripMenuItem]::new("Iniciar / reactivar")
$gameItem = [System.Windows.Forms.ToolStripMenuItem]::new("Detener para jugar")
$logsItem = [System.Windows.Forms.ToolStripMenuItem]::new("Ver registros")
$exitItem = [System.Windows.Forms.ToolStripMenuItem]::new("Salir completamente")

[void]$menu.Items.Add($statusItem)
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
[void]$menu.Items.Add($openItem)
[void]$menu.Items.Add($updateItem)
[void]$menu.Items.Add($startItem)
[void]$menu.Items.Add($gameItem)
[void]$menu.Items.Add((New-Object System.Windows.Forms.ToolStripSeparator))
[void]$menu.Items.Add($logsItem)
[void]$menu.Items.Add($exitItem)
$notifyIcon.ContextMenuStrip = $menu

function Show-Notice {
    param(
        [string]$Title,
        [string]$Text,
        [System.Windows.Forms.ToolTipIcon]$Icon =
            [System.Windows.Forms.ToolTipIcon]::Info
    )

    $notifyIcon.BalloonTipTitle = $Title
    $notifyIcon.BalloonTipText = $Text
    $notifyIcon.BalloonTipIcon = $Icon
    $notifyIcon.ShowBalloonTip(4000)
}

function Test-MatchLab {
    try {
        foreach ($uri in @(
            "http://127.0.0.1:8000/health",
            "http://127.0.0.1:3000"
        )) {
            $request = [System.Net.HttpWebRequest]::Create($uri)
            $request.Proxy = $null
            $request.Timeout = 2000
            $request.ReadWriteTimeout = 2000
            $response = $request.GetResponse()
            try {
                if ([int]$response.StatusCode -ne 200) {
                    return $false
                }
            } finally {
                $response.Dispose()
            }
        }
        return $true
    } catch {
        return $false
    }
}

function Set-TrayState {
    param([ValidateSet("Running", "Stopped", "Busy", "Error")][string]$State)

    switch ($State) {
        "Running" {
            $statusItem.Text = "Estado: funcionando"
            $notifyIcon.Text = "MatchLab - funcionando"
            $openItem.Enabled = $true
            $updateItem.Enabled = $true
            $startItem.Enabled = $false
            $gameItem.Enabled = $true
        }
        "Stopped" {
            $statusItem.Text = "Estado: modo juego"
            $notifyIcon.Text = "MatchLab - detenido para jugar"
            $openItem.Enabled = $true
            $updateItem.Enabled = $false
            $startItem.Enabled = $true
            $gameItem.Enabled = $false
        }
        "Busy" {
            $statusItem.Text = "Estado: trabajando..."
            $notifyIcon.Text = "MatchLab - trabajando"
            $openItem.Enabled = $false
            $updateItem.Enabled = $false
            $startItem.Enabled = $false
            $gameItem.Enabled = $false
        }
        "Error" {
            $statusItem.Text = "Estado: necesita revision"
            $notifyIcon.Text = "MatchLab - error"
            $openItem.Enabled = $false
            $updateItem.Enabled = $false
            $startItem.Enabled = $true
            $gameItem.Enabled = $true
        }
    }
}

function Invoke-Control {
    param(
        [Parameter(Mandatory)][string]$Action,
        [switch]$NoBrowser
    )

    $arguments = (
        "-NoProfile -ExecutionPolicy Bypass -File `"$ControlScript`" " +
        "-Action $Action"
    )
    if ($NoBrowser) {
        $arguments += " -NoBrowser"
    }
    $process = Start-Process `
        -FilePath $PowerShell `
        -ArgumentList $arguments `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -PassThru
    $null = $process.Handle
    $process.WaitForExit()
    $process.Refresh()
    return $process.ExitCode
}

function Start-FromTray {
    param([switch]$OpenBrowser)

    if ($script:Busy) {
        return
    }
    $script:Busy = $true
    Set-TrayState "Busy"
    [System.Windows.Forms.Application]::DoEvents()
    $exitCode = Invoke-Control -Action "Start" -NoBrowser
    if ($exitCode -eq 0) {
        Set-TrayState "Running"
        Show-Notice "MatchLab preparado" "La aplicacion ya esta funcionando."
        if ($OpenBrowser) {
            Start-Process "http://localhost:3000"
        }
    } else {
        Set-TrayState "Error"
        Show-Notice `
            "No se pudo iniciar MatchLab" `
            "Consulta Ver registros o controller.log." `
            ([System.Windows.Forms.ToolTipIcon]::Error)
    }
    $script:Busy = $false
}

function Stop-ForGaming {
    if ($script:Busy) {
        return
    }
    $script:Busy = $true
    Set-TrayState "Busy"
    [System.Windows.Forms.Application]::DoEvents()
    $exitCode = Invoke-Control -Action "Stop" -NoBrowser
    if ($exitCode -eq 0) {
        Set-TrayState "Stopped"
        Show-Notice `
            "Modo juego activado" `
            "MatchLab esta detenido; los datos y modelos siguen guardados."
        $notifyIcon.Visible = $false
        [System.Windows.Forms.Application]::Exit()
    } else {
        Set-TrayState "Error"
        Show-Notice `
            "No se pudo detener todo" `
            "Revisa los registros de MatchLab." `
            ([System.Windows.Forms.ToolTipIcon]::Warning)
    }
    $script:Busy = $false
}

$openItem.Add_Click({ Start-FromTray -OpenBrowser })
$startItem.Add_Click({ Start-FromTray -OpenBrowser })
$gameItem.Add_Click({ Stop-ForGaming })
$updateItem.Add_Click({
    if ($script:Busy) {
        return
    }
    $script:Busy = $true
    Set-TrayState "Busy"
    [System.Windows.Forms.Application]::DoEvents()
    $exitCode = Invoke-Control -Action "Update" -NoBrowser
    if ($exitCode -eq 0) {
        Set-TrayState "Running"
        Show-Notice `
            "Actualizacion iniciada" `
            "Los datos de hoy se estan descargando y analizando."
    } else {
        Set-TrayState "Error"
        Show-Notice `
            "Fallo de actualizacion" `
            "Consulta los registros para ver el detalle." `
            ([System.Windows.Forms.ToolTipIcon]::Error)
    }
    $script:Busy = $false
})
$logsItem.Add_Click({
    [void](Invoke-Control -Action "Logs" -NoBrowser)
})
$exitItem.Add_Click({
    Stop-ForGaming
    $notifyIcon.Visible = $false
    [System.Windows.Forms.Application]::Exit()
})
$notifyIcon.Add_DoubleClick({ Start-FromTray -OpenBrowser })

$statusTimer = New-Object System.Windows.Forms.Timer
$statusTimer.Interval = 10000
$statusTimer.Add_Tick({
    if (-not $script:Busy) {
        if (Test-MatchLab) {
            Set-TrayState "Running"
        } else {
            Set-TrayState "Stopped"
        }
    }
})
$statusTimer.Start()

$activationTimer = New-Object System.Windows.Forms.Timer
$activationTimer.Interval = 500
$activationTimer.Add_Tick({
    if ($exitEvent.WaitOne(0)) {
        $notifyIcon.Visible = $false
        [System.Windows.Forms.Application]::Exit()
        return
    }
    if ($activationEvent.WaitOne(0)) {
        Start-FromTray -OpenBrowser
    }
})
$activationTimer.Start()

$startupTimer = New-Object System.Windows.Forms.Timer
$startupTimer.Interval = 600
$startupTimer.Add_Tick({
    $startupTimer.Stop()
    Start-FromTray -OpenBrowser:(-not $NoBrowser)
})
$startupTimer.Start()

try {
    [System.Windows.Forms.Application]::Run()
} finally {
    $statusTimer.Stop()
    $activationTimer.Stop()
    $startupTimer.Stop()
    $notifyIcon.Visible = $false
    $notifyIcon.Dispose()
    if ($loadedIcon) {
        $loadedIcon.Dispose()
    }
    $activationEvent.Dispose()
    $exitEvent.Dispose()
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
