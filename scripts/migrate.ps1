param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("dev", "test", "prod")]
    [string]$Environment = "dev",

    [Parameter(Mandatory = $false)]
    [ValidateSet("upgrade", "downgrade", "current", "history")]
    [string]$Action = "upgrade",

    [Parameter(Mandatory = $false)]
    [string]$Revision = "head"
)

$ErrorActionPreference = "Stop"

switch ($Environment) {
    "dev"  { $dbName = "telegram_copier_dev" }
    "test" { $dbName = "telegram_copier_test" }
    "prod" { $dbName = "telegram_copier_prod" }
    default { throw "Unsupported environment: $Environment" }
}

if (-not $env:PGUSER) { $env:PGUSER = "8n8user" }
if (-not $env:PGPASSWORD) { throw "PGPASSWORD is required. Set it in your shell before running." }
if (-not $env:PGHOST) { $env:PGHOST = "localhost" }
if (-not $env:PGPORT) { $env:PGPORT = "5432" }

$encodedPassword = [System.Uri]::EscapeDataString($env:PGPASSWORD)
$env:DB_BACKEND = "postgres"
$env:DATABASE_URL = "postgresql+asyncpg://$($env:PGUSER):$encodedPassword@$($env:PGHOST):$($env:PGPORT)/$dbName"

Write-Host "Environment: $Environment ($dbName)"
Write-Host "Action: $Action $Revision"

switch ($Action) {
    "upgrade" {
        .\.venv\Scripts\python -m alembic upgrade $Revision
        break
    }
    "downgrade" {
        .\.venv\Scripts\python -m alembic downgrade $Revision
        break
    }
    "current" {
        .\.venv\Scripts\python -m alembic current
        break
    }
    "history" {
        .\.venv\Scripts\python -m alembic history --verbose
        break
    }
}
