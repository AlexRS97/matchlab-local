param([switch]$Setup,[switch]$NoBuild,[switch]$NoBrowser)
& (Join-Path $PSScriptRoot 'scripts\start.ps1') -Setup:$Setup -NoBuild:$NoBuild -NoBrowser:$NoBrowser
exit $LASTEXITCODE
