# Deploy one multi-env stack on Windows (PowerShell) using local or GHCR images.
#
# Examples:
#   # Build local image, then deploy dev with host bind mounts (no GHCR):
#   .\deploy\scripts\deploy-env.ps1 -Environment dev -LocalBuild -BindMounts
#
#   # Pull from GHCR (after CI publish):
#   .\deploy\scripts\deploy-env.ps1 -Environment uat -ImageTag latest
#
# Prerequisites: Docker Desktop running; deploy/env/docker.env.<env> filled in.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "tst", "uat", "prod")]
    [string]$Environment,

    [string]$ImageTag = "latest",

    [string]$BackendImage = "",

    [switch]$LocalBuild,
    [switch]$SkipPull,
    [switch]$BindMounts,
    [switch]$NoMongo,

    [string]$HostDataRoot = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$EnvFile = Join-Path $Root "deploy\env\docker.env.$Environment"
if (-not (Test-Path $EnvFile)) {
    throw "Missing $EnvFile — copy from deploy\env\docker.env.$Environment.example and fill secrets."
}

if ($LocalBuild) {
    Write-Host "==> Building local unified image (SPA + API)..."
    docker build -f Dockerfile.backend -t "local/tgc-backend:$Environment" .
    if ($LASTEXITCODE -ne 0) { throw "backend build failed" }
    $BackendImage = "local/tgc-backend:$Environment"
    $SkipPull = $true
}

$OwnerRepo = if ($env:GHCR_OWNER_REPO) { $env:GHCR_OWNER_REPO } else { "sammirzagharcheh/pytelegramclientcopier" }
if (-not $BackendImage) { $BackendImage = "ghcr.io/$OwnerRepo/backend:$ImageTag" }

$env:BACKEND_IMAGE = $BackendImage
$env:IMAGE_TAG = $ImageTag
$env:COMPOSE_ENV = $Environment
$env:PULL_POLICY = if ($SkipPull) { "missing" } else { "always" }

if (-not $HostDataRoot) {
    $HostDataRoot = Join-Path $Root "data\docker-envs"
}
$env:HOST_DATA_ROOT = ($HostDataRoot -replace "\\", "/")

$Project = "tgc-$Environment"
$ComposeArgs = @(
    "-p", $Project,
    "-f", "deploy/compose/docker-compose.yml",
    "-f", "deploy/compose/docker-compose.$Environment.yml"
)
if ($NoMongo) { $ComposeArgs += @("-f", "deploy/compose/docker-compose.no-mongo.yml") }
if ($BindMounts) {
    New-Item -ItemType Directory -Force -Path (Join-Path $HostDataRoot "$Environment\app"), (Join-Path $HostDataRoot "$Environment\mongo") | Out-Null
    $ComposeArgs += @("-f", "deploy/compose/docker-compose.bind-mounts.yml")
}
$ComposeArgs += @("--env-file", "deploy/env/docker.env.$Environment")

Write-Host "==> Environment : $Environment"
Write-Host "==> Project     : $Project"
Write-Host "==> Image       : $BackendImage"
Write-Host "==> Env file    : $EnvFile"
if ($BindMounts) {
    Write-Host "==> Data mode   : bind mounts under $HostDataRoot\$Environment\"
} else {
    Write-Host "==> Data mode   : named volumes ${Project}_app_data / ${Project}_mongo_data"
}

if (-not $SkipPull) {
    & docker compose @ComposeArgs pull
    if ($LASTEXITCODE -ne 0) { throw "compose pull failed" }
} else {
    Write-Host "==> Skipping image pull"
}

& docker compose @ComposeArgs up -d --remove-orphans
if ($LASTEXITCODE -ne 0) { throw "compose up failed" }

& docker compose @ComposeArgs ps

Write-Host ""
Write-Host "Panel:  http://localhost:$(switch ($Environment) { 'dev' {8080} 'tst' {8081} 'uat' {8082} 'prod' {80} })"
Write-Host "Create admin:"
Write-Host ("  docker compose {0} exec backend tg-copier db create-admin you@example.com 'YourPassword'" -f ($ComposeArgs -join ' '))
