# Test Custom Model via New API
$NewApiUrl = "http://localhost:3001/v1/chat/completions"
# Use the root token we set in docker-compose, or a key you created in UI
$ApiKey = "123456" 

$Body = @{
    model = "opus4.5"
    messages = @(
        @{
            role = "user"
            content = "If you can see this, the custom model connection is working! Reply with 'Connection Success'"
        }
    )
    stream = $false
} | ConvertTo-Json

try {
    Write-Host "Sending request to New API testing model 'opus4.5'..."
    $response = Invoke-RestMethod -Uri $NewApiUrl -Method POST -Headers @{"Authorization"="Bearer $ApiKey"; "Content-Type"="application/json"} -Body $Body -ErrorAction Stop
    
    Write-Host "✅ Success! Response:" -ForegroundColor Green
    Write-Host $response.choices[0].message.content
} catch {
    Write-Host "❌ Failed. Server response:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host $reader.ReadToEnd()
    }
    
    Write-Host "`n💡 Common fixes:"
    Write-Host "1. Ensure 'opus4.5' is added to the Channel in New API."
    Write-Host "2. Ensure 'opus4.5' has a price set in Operation Settings (e.g. 'opus4.5:10') OR 'Self Use Mode' is on."
}
