# 构建 Flutter Web 并部署到 backend/web_app（供 /app-web 访问）
param(
    [switch]$Production,
    [string]$ApiBase = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$FlutterApp = Join-Path $Root "flutter_app"
$WebOut = Join-Path $FlutterApp "build\web"
$DeployDir = Join-Path $Root "backend\web_app"

. (Join-Path $PSScriptRoot "setup_flutter_env.ps1")

Push-Location $FlutterApp
try {
    flutter pub get

    $defineArgs = @()
    if ($Production) {
        $defineArgs += "--dart-define=PRODUCTION=true"
    } else {
        $defineArgs += "--dart-define=PRODUCTION=false"
        $defineArgs += "--dart-define=API_BASE=$ApiBase"
    }

    flutter build web --base-href=/app-web/ @defineArgs

    if (-not (Test-Path $WebOut)) {
        throw "构建失败：未找到 $WebOut"
    }

    if (Test-Path $DeployDir) {
        Remove-Item $DeployDir\* -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path $DeployDir -Force | Out-Null
    }
    Copy-Item -Path (Join-Path $WebOut "*") -Destination $DeployDir -Recurse -Force

    Write-Host ""
    Write-Host "部署完成: $DeployDir"
    Write-Host "启动后端后访问: http://127.0.0.1:8000/app-web"
} finally {
    Pop-Location
}
