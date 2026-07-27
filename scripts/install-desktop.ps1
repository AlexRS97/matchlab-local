param(
    [switch]$Launch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TrayScript = Join-Path $PSScriptRoot "matchlab-tray.ps1"
$ApplicationDirectory = Join-Path $env:LOCALAPPDATA "MatchLab"
$IconPath = Join-Path $ApplicationDirectory "MatchLab.ico"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

New-Item -ItemType Directory -Path $ApplicationDirectory -Force | Out-Null

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MatchLabNativeMethods {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

$bitmap = [System.Drawing.Bitmap]::new(64, 64)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::Transparent)
$background = [System.Drawing.SolidBrush]::new(
    [System.Drawing.Color]::FromArgb(200, 255, 61)
)
$foreground = [System.Drawing.Pen]::new(
    [System.Drawing.Color]::FromArgb(16, 23, 16),
    6
)
$foreground.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$foreground.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$foreground.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
$graphics.FillEllipse($background, 2, 2, 60, 60)
$points = [System.Drawing.Point[]]@(
    (New-Object System.Drawing.Point(15, 43)),
    (New-Object System.Drawing.Point(24, 20)),
    (New-Object System.Drawing.Point(32, 39)),
    (New-Object System.Drawing.Point(39, 24)),
    (New-Object System.Drawing.Point(49, 43))
)
$graphics.DrawLines($foreground, $points)

$iconHandle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)
$stream = [System.IO.File]::Create($IconPath)
try {
    $icon.Save($stream)
} finally {
    $stream.Dispose()
    $icon.Dispose()
    [void][MatchLabNativeMethods]::DestroyIcon($iconHandle)
    $foreground.Dispose()
    $background.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MatchLab.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $PowerShell
$shortcut.Arguments = (
    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -STA -File `"$TrayScript`""
)
$shortcut.WorkingDirectory = $Root
$shortcut.IconLocation = "$IconPath,0"
$shortcut.Description = "Inicia MatchLab y lo controla desde la bandeja de Windows"
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "Acceso directo creado: $shortcutPath" -ForegroundColor Green
Write-Host "Icono de bandeja instalado: $IconPath" -ForegroundColor Green

if ($Launch) {
    Start-Process `
        -FilePath $PowerShell `
        -ArgumentList (
            "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden " +
            "-STA -File `"$TrayScript`""
        ) `
        -WorkingDirectory $Root `
        -WindowStyle Hidden
}
