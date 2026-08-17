param([Parameter(Mandatory=$true)][string]$InputFile)
if (-not (Test-Path -LiteralPath $InputFile)) { throw "Backup not found: $InputFile" }
Get-Content -LiteralPath $InputFile -AsByteStream | docker compose exec -T db pg_restore --clean --if-exists -U ${env:POSTGRES_USER} -d ${env:POSTGRES_DB}
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL restore failed." }
Write-Output "Restore completed."
