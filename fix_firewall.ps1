# 需要以管理员身份运行此脚本
# 此脚本用于允许 Docker 访问 VPN 代理端口 (7890)

Write-Host "正在添加防火墙规则..." -ForegroundColor Yellow

$ruleName = "Allow Docker VPN Proxy"
$port = 7890

# 检查规则是否已存在
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existing) {
    Write-Host "✅ 规则已存在，无需重复添加。" -ForegroundColor Green
}
else {
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow -Profile Any | Out-Null
        Write-Host "✅ 防火墙规则添加成功！" -ForegroundColor Green
        Write-Host "已允许 TCP 端口: $port" -ForegroundColor Cyan
    }
    catch {
        Write-Host "❌ 添加失败！" -ForegroundColor Red
        Write-Host "请确保您已右键选择 '以管理员身份运行'！" -ForegroundColor Yellow
        Write-Host "错误详情: $($_.Exception.Message)"
        Pause
        exit 1
    }
}

Write-Host ""
Write-Host "正在测试端口连通性..." -ForegroundColor Yellow
$dockerIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "172.*" } | Select-Object -First 1).IPAddress
Write-Host "Docker 宿主机 IP: $dockerIP"

try {
    # 尝试连接本地转发端口
    $tcp = New-Object System.Net.Sockets.TcpClient
    $connect = $tcp.BeginConnect("127.0.0.1", 7890, $null, $null)
    $wait = $connect.AsyncWaitHandle.WaitOne(2000, $false)
    if ($wait) {
        Write-Host "✅ 端口 7890 监听正常！" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️ 警告：端口 7890 似乎未开启监听。" -ForegroundColor Red
        Write-Host "请确保您的 VPN 软件已经开启！" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠️ 检测出错: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "按任意键完成..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
