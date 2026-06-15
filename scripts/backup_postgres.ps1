param(
    [string]$BackupDir = "./backups/postgres",
    [string]$RetentionDays = "30",
    [string]$DbHost = "localhost",
    [string]$DbPort = "5432",
    [string]$DbName = "colegio_db",
    [string]$DbUser = "colegio_user"
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupDir "${DbName}_${timestamp}.dump"

if (-not $env:PGPASSWORD) {
    Write-Error "PGPASSWORD no esta definido. Exporta la password antes de ejecutar el backup."
}

pg_dump --format=custom --host=$DbHost --port=$DbPort --username=$DbUser --file=$backupFile $DbName

Get-ChildItem $BackupDir -Filter "*.dump" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-[int]$RetentionDays) } |
    Remove-Item -Force

Write-Output "Backup generado: $backupFile"
