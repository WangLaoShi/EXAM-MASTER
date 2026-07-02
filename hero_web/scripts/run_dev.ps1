$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $ProjectRoot

Write-Host "Hero Web dev server: http://127.0.0.1:5173"
Write-Host "Ensure backend is running: cd backend; python run.py"
npm run dev
