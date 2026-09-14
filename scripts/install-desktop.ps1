param(
    [switch]$Launch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$TrayScript = Join-Path $PSScriptRoot "matchlab-tray.ps1"
$ApplicationDirectory = Join-Path $env:LOCALAPPDATA "MatchLab"
$IconPath = Join-Path $ApplicationDirectory "MatchLab.ico"
$LogoPath = Join-Path $Root "assets\matchlab-logo.png"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

New-Item -ItemType Directory -Path $ApplicationDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $LogoPath)) {
    throw "No se encuentra el logotipo de MatchLab: $LogoPath"
}

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class MatchLabNativeMethods {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

$source = [System.Drawing.Image]::FromFile($LogoPath)
$bitmap = [System.Drawing.Bitmap]::new(256, 256)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
$graphics.Clear([System.Drawing.Color]::Black)
$graphics.DrawImage($source, 0, 0, 256, 256)

$iconHandle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)
$stream = [System.IO.File]::Create($IconPath)
try {
    $icon.Save($stream)
} finally {
    $stream.Dispose()
    $icon.Dispose()
    [void][MatchLabNativeMethods]::DestroyIcon($iconHandle)
    $graphics.Dispose()
    $bitmap.Dispose()
    $source.Dispose()
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

$stopShortcutPath = Join-Path $desktop "Detener MatchLab.lnk"
$stopShortcut = $shell.CreateShortcut($stopShortcutPath)
$stopShortcut.TargetPath = $PowerShell
$stopShortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $Root 'scripts\stop.ps1') + '"'
$stopShortcut.WorkingDirectory = $Root
$stopShortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,27"
$stopShortcut.Description = "Cierra MatchLab y sus trabajos antes de jugar; conserva datos y modelos"
$stopShortcut.WindowStyle = 7
$stopShortcut.Save()

Write-Host "Acceso directo creado: $shortcutPath" -ForegroundColor Green
Write-Host "Acceso directo de cierre: $stopShortcutPath" -ForegroundColor Green
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
