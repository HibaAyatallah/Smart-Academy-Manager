param([string]$Output = ".\backups\smart-academy-mysql-$(Get-Date -Format yyyyMMdd-HHmmss).sql")

$directory = Split-Path -Parent $Output
if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }

docker compose exec -T -e MYSQL_PWD=${env:DB_PASSWORD} db mysqldump `
    --user=${env:DB_USER} `
    --single-transaction `
    --routines `
    --triggers `
    --set-gtid-purged=OFF `
    --default-character-set=utf8mb4 `
    ${env:DB_NAME} > $Output

if ($LASTEXITCODE -ne 0) { throw "MySQL backup failed." }
Write-Output "MySQL backup created: $Output"
