param(
    [string]$OutputDir = "..\backend\hero_web_app"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $ProjectRoot

Write-Host "Building Hero Web for /app-exam ..."
$env:VITE_BASE_PATH = "/app-exam/"
npm run build

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "Copying dist -> $OutputDir"
Remove-Item -Recurse -Force "$OutputDir\*" -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force "dist\*" $OutputDir

Write-Host "Done. Serve at http://127.0.0.1:8000/app-exam"
