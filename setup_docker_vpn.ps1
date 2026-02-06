# 以管理员身份运行此脚本
# 这个脚本会自动设置端口转发，让 Docker 访问本地 VPN

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Docker VPN 访问配置工具" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 错误：需要管理员权限！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请右键点击 PowerShell，选择'以管理员身份运行'，然后重新执行此脚本。" -ForegroundColor Yellow
    Write-Host ""
    Pause
    exit 1
}

Write-Host "✅ 管理员权限确认" -ForegroundColor Green
Write-Host ""

# 获取 WSL/Docker 使用的网卡IP
$dockerIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "172.*" } | Select-Object -First 1).IPAddress

if (-not $dockerIP) {
    Write-Host "❌ 未找到 Docker 网络接口 (172.x.x.x)" -ForegroundColor Red
    Write-Host "使用默认值 172.25.80.1" -ForegroundColor Yellow
    $dockerIP = "172.25.80.1"
}

Write-Host "检测到 Docker 宿主机 IP: $dockerIP" -ForegroundColor Cyan
Write-Host ""

# 清理可能存在的旧规则
Write-Host "清理旧的端口转发规则..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenaddress=$dockerIP listenport=7890 2>$null
Write-Host ""

# 添加新规则
Write-Host "添加端口转发规则: $dockerIP:7890 -> 127.0.0.1:7890" -ForegroundColor Cyan
$result = netsh interface portproxy add v4tov4 listenaddress=$dockerIP listenport=7890 connectaddress=127.0.0.1 connectport=7890

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 端口转发设置成功！" -ForegroundColor Green
}
else {
    Write-Host "❌ 设置失败！" -ForegroundColor Red
    Pause
    exit 1
}

Write-Host ""
Write-Host "当前所有端口转发规则：" -ForegroundColor Cyan
netsh interface portproxy show all

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor Yellow
Write-Host "1. 打开 http://localhost:5201 进入 Clove 设置"
Write-Host "2. 代理 URL 改为: http://$dockerIP:7890"
Write-Host "3. 保存设置"
Write-Host "4. 在普通 PowerShell 运行以下命令重启并测试："
Write-Host ""
Write-Host "   cd c:\Users\h\Desktop\zuoye1\clove" -ForegroundColor Cyan
Write-Host "   docker-compose restart" -ForegroundColor Cyan
Write-Host "   c:\Users\h\Desktop\zuoye1\clove\test_clove_api.ps1" -ForegroundColor Cyan
Write-Host ""
Pause
