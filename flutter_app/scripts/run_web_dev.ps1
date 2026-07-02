# 本地 Web 开发：Chrome + 固定端口 8080（需后端 CORS 允许 127.0.0.1:8080）
param(
    [string]$ApiBase = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$FlutterApp = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "flutter_app"

. (Join-Path $PSScriptRoot "setup_flutter_env.ps1")

Push-Location $FlutterApp
try {
    flutter pub get
    flutter run -d chrome `
        --web-port=8080 `
        --web-hostname=127.0.0.1 `
        --dart-define=PRODUCTION=false `
        --dart-define=API_BASE=$ApiBase
} finally {
    Pop-Location
}
