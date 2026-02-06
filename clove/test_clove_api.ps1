# 测试 Clove API 的真实请求格式
# 用 curl 精确复现 Claude SDK 的请求

$headers = @{
    "x-api-key"         = "huakai12345"
    "anthropic-version" = "2023-06-01"
    "content-type"      = "application/json"
}

$body = @{
    model      = "claude-3-5-sonnet-20240620"
    max_tokens = 20
    messages   = @(
        @{
            role    = "user"
            content = "Say hello"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Testing Clove /v1/messages endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5201/v1/messages" -Method POST -Headers $headers -Body $body -UseBasicParsing
    Write-Host "✅ Success! Status: $($response.StatusCode)"
    Write-Host "Response:"
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "❌ Failed!"
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "Body: $($reader.ReadToEnd())"
    }
}
