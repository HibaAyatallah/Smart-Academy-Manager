param([Parameter(Mandatory=$true)][string]$InputFile)

if (-not (Test-Path -LiteralPath $InputFile)) { throw "Backup not found: $InputFile" }

Get-Content -LiteralPath $InputFile -Raw | docker compose exec -T -e MYSQL_PWD=${env:DB_PASSWORD} db mysql `
    --user=${env:DB_USER} `
    --default-character-set=utf8mb4 `
    ${env:DB_NAME}

if ($LASTEXITCODE -ne 0) { throw "MySQL restore failed." }
Write-Output "MySQL restore completed."
