# 需要以管理员身份运行此脚本
# 右键点击 PowerShell → 以管理员身份运行，然后执行本脚本

Write-Host "正在设置端口转发，让 Docker 容器能访问 VPN..." -ForegroundColor Yellow

# 添加端口转发规则
netsh interface portproxy add v4tov4 listenaddress=172.25.80.1 listenport=7890 connectaddress=127.0.0.1 connectport=7890

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 端口转发设置成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "已创建规则：172.25.80.1:7890 -> 127.0.0.1:7890" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "查看当前所有转发规则："
    netsh interface portproxy show all
}
else {
    Write-Host "❌ 设置失败！请确保：" -ForegroundColor Red
    Write-Host "1. 以管理员身份运行 PowerShell"
    Write-Host "2. VPN 正在运行"
}

Write-Host ""
Write-Host "按任意键继续..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
