param([string]$Output = ".\backups\smart-academy-$(Get-Date -Format yyyyMMdd-HHmmss).dump")
$directory = Split-Path -Parent $Output
if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
docker compose exec -T db pg_dump -U ${env:POSTGRES_USER} -d ${env:POSTGRES_DB} -Fc > $Output
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL backup failed." }
Write-Output "Backup created: $Output"
