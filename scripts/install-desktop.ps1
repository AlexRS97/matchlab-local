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
$background = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    [System.Drawing.Rectangle]::new(0, 0, 64, 64),
    [System.Drawing.Color]::FromArgb(69, 194, 255),
    [System.Drawing.Color]::FromArgb(11, 53, 88),
    45
)
$ball = [System.Drawing.SolidBrush]::new(
    [System.Drawing.Color]::FromArgb(239, 248, 255)
)
$ballOutline = [System.Drawing.Pen]::new(
    [System.Drawing.Color]::FromArgb(155, 217, 255),
    2
)
$panel = [System.Drawing.SolidBrush]::new(
    [System.Drawing.Color]::FromArgb(11, 53, 88)
)
$seam = [System.Drawing.Pen]::new(
    [System.Drawing.Color]::FromArgb(47, 111, 237),
    2.5
)
$seam.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$seam.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$shine = [System.Drawing.SolidBrush]::new(
    [System.Drawing.Color]::FromArgb(115, 255, 255, 255)
)

$graphics.FillEllipse($background, 1, 1, 62, 62)
$graphics.FillEllipse($ball, 10, 10, 44, 44)
$graphics.DrawEllipse($ballOutline, 10, 10, 44, 44)
$centerPanel = [System.Drawing.PointF[]]@(
    [System.Drawing.PointF]::new(32, 20),
    [System.Drawing.PointF]::new(41, 27),
    [System.Drawing.PointF]::new(38, 38),
    [System.Drawing.PointF]::new(26, 38),
    [System.Drawing.PointF]::new(23, 27)
)
$graphics.FillPolygon($panel, $centerPanel)
$graphics.DrawLine($seam, 32, 20, 32, 11)
$graphics.DrawLine($seam, 41, 27, 52, 24)
$graphics.DrawLine($seam, 38, 38, 44, 50)
$graphics.DrawLine($seam, 26, 38, 20, 50)
$graphics.DrawLine($seam, 23, 27, 12, 24)
$graphics.FillEllipse($shine, 17, 15, 8, 8)

$iconHandle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)
$stream = [System.IO.File]::Create($IconPath)
try {
    $icon.Save($stream)
} finally {
    $stream.Dispose()
    $icon.Dispose()
    [void][MatchLabNativeMethods]::DestroyIcon($iconHandle)
    $shine.Dispose()
    $seam.Dispose()
    $panel.Dispose()
    $ballOutline.Dispose()
    $ball.Dispose()
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
