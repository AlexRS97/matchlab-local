param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Target = Join-Path $Root ".env"
$Template = Join-Path $Root ".env.example"

if ((Test-Path -LiteralPath $Target) -and -not $Force) {
    throw ".env ya existe. Usa -Force solo si entiendes que cambiar credenciales puede desconectar una base existente."
}

function New-UrlSafeSecret {
    param([int]$Bytes = 32)

    $Buffer = [byte[]]::new($Bytes)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($Buffer)
    return [Convert]::ToBase64String($Buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

# Both occurrences of the database marker must receive exactly the same value.
$AppSecret = New-UrlSafeSecret -Bytes 48
$DatabasePassword = New-UrlSafeSecret -Bytes 32
$Content = Get-Content -Raw -Encoding utf8 -LiteralPath $Template
$Content = $Content.Replace("CHANGE_ME_APP_SECRET", $AppSecret)
$Content = $Content.Replace("CHANGE_ME_DB_PASSWORD", $DatabasePassword)

[System.IO.File]::WriteAllText($Target, $Content, [System.Text.UTF8Encoding]::new($false))
Write-Host ".env creado sin mostrar secretos en pantalla." -ForegroundColor Green
