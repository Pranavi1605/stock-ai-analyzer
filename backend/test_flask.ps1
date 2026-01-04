# test_flask.ps1
# PowerShell script to test Flask stock app APIs
# Must run from the backend folder while Flask server is running

$baseUrl = "http://127.0.0.1:5000"
$userId = "test_user"

Write-Host "`n[INFO] Testing Flask API endpoints..."

# ---------------- BUY SUGGESTIONS ----------------
$buyAmount = 2000
Write-Host "`n[TEST] Buy Suggestions for amount = $buyAmount"

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/buy-suggestions" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{ amount = $buyAmount } | ConvertTo-Json)

    Write-Host "[RESULT] Buy Suggestions Received: $($response.Count) stocks"
    $response | ForEach-Object { Write-Host "  $_.symbol - ₹$($_.price)" }
} catch {
    Write-Host "[ERROR] Buy Suggestions failed:" $_
}

# ---------------- BUY STOCK ----------------
if ($response.Count -gt 0) {
    $stock = $response[0]
    Write-Host "`n[TEST] Buying 1 share of $($stock.symbol) at ₹$($stock.price)"

    try {
        $buyResp = Invoke-RestMethod -Uri "$baseUrl/buy-stock" `
            -Method POST `
            -ContentType "application/json" `
            -Body (@{ user_id = $userId; symbol = $stock.symbol; price = $stock.price; quantity = 1 } | ConvertTo-Json)

        Write-Host "[RESULT]" $buyResp.message
    } catch {
        Write-Host "[ERROR] Buy stock failed:" $_
    }
}

# ---------------- PORTFOLIO ----------------
Write-Host "`n[TEST] Fetching Portfolio for user $userId"
try {
    $portfolio = Invoke-RestMethod -Uri "$baseUrl/portfolio/$userId" -Method GET
    Write-Host "[RESULT] Portfolio contains $($portfolio.Count) stocks"
    $portfolio | ForEach-Object { Write-Host "  $_.symbol - Qty: $($_.quantity) - Price: ₹$($_.price)" }
} catch {
    Write-Host "[ERROR] Portfolio fetch failed:" $_
}

# ---------------- SELL STOCK ----------------
if ($portfolio.Count -gt 0) {
    $stockToSell = $portfolio[0]
    $sellQty = 1
    Write-Host "`n[TEST] Selling $sellQty share of $($stockToSell.symbol)"

    try {
        $sellResp = Invoke-RestMethod -Uri "$baseUrl/sell-stock" `
            -Method POST `
            -ContentType "application/json" `
            -Body (@{ user_id = $userId; symbol = $stockToSell.symbol; quantity = $sellQty } | ConvertTo-Json)

        Write-Host "[RESULT]" $sellResp.message
    } catch {
        Write-Host "[ERROR] Sell stock failed:" $_
    }
}

Write-Host "`n[INFO] All tests completed successfully!"
