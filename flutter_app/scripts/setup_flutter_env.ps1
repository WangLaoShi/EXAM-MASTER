# 将项目内 Flutter SDK 加入当前 PowerShell 会话 PATH
$FlutterBin = "D:\EXAM-MASTER\tools\flutter\bin"
if (-not (Test-Path "$FlutterBin\flutter.bat")) {
    Write-Error "未找到 Flutter SDK，请先执行: git clone -b stable --depth 1 https://github.com/flutter/flutter.git D:\EXAM-MASTER\tools\flutter"
    exit 1
}
$env:PATH = "$FlutterBin;" + $env:PATH
Write-Host "Flutter: $(flutter --version 2>&1 | Select-Object -First 1)"
Write-Host "已加入 PATH（仅当前终端有效）。永久添加请把 $FlutterBin 写入系统环境变量。"
