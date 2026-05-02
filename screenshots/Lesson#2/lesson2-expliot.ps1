# verify-forged-token.ps1
$forged = "eyJraWQiOiI1bk5mTE5tUXlPNmhWaStGbHBheEkyb09ldUxZMmR2c3h0cDR0OXo1MDFBPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5MDJjMzk1Yy1lMGUxLTcwOTQtNGIwNi0zZDkyYjNkNzkwMGIiLCJpc3MiOiJodHRwczovL2NvZ25pdG8taWRwLmV1LW5vcnRoLTEuYW1hem9uYXdzLmNvbS9ldS1ub3J0aC0xX0RmMW1HczdOSyIsImNsaWVudF9pZCI6IjcyOG1iZ2RzbmxjZ2tlYXFrMTE4am1obGQ3Iiwib3JpZ2luX2p0aSI6IjE4OTM0ODczLThiMmYtNGQ0Yi1hN2ViLWFkNTIwNDE1NTNhZCIsImV2ZW50X2lkIjoiZDNiZDQ0MjMtMGZmMy00OGM1LWI1NDItMWQwMWJkNDFiMTk5IiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsImF1dGhfdGltZSI6MTc3Njg2NzQzNSwiZXhwIjoxNzc2OTMzNzM3LCJpYXQiOjE3NzY5MzAxMzcsImp0aSI6IjRmNDk4ZDc3LTRlNDMtNGYzOC05Mjc1LTgzNDY5YTI5NDJhZCIsInVzZXJuYW1lIjoiOTAyYzM5NWMtZTBlMS03MDk0LTRiMDYtM2Q5MmIzZDc5MDBiIn0.iAEX6hu8gafhAcb-YXRurPg-FLW2x2CX1HgipDl7B47wIU1RHO5p7K4LOZ58MyJjWnIIyIiyBw550CtOi0DPm-eUUdHhWvTxjKE2oX5BZqdyL2VIP5vruPAcU5_QAkmqafONyTK67nW5B2NTUTnkrE5wfQxdE5glcCkrA3n6Heq9PLjfnOMdqWYCEPLN-UiNBasl_sMxr7Zl3PCqFtcojO5JQb7Bjjtd7GxyFdiO3IBJH0c_jwO52cwKb80abLftK5o6PDMGbAiTTR7-S6_G4YLCLzuJIsPtJcTiNopUmvyP4Egq0kHKAew3v2ykuGPgLUiFWMoE3bWNZNVOZixqeg"
$headers = @{ Authorization = "Bearer $forged"; "Content-Type" = "application/json" }
$body = '{"action":"account"}'
try {
    $resp = Invoke-RestMethod -Uri "https://gfxvwxy0n4.execute-api.eu-north-1.amazonaws.com/dvsa/order" -Method POST -Headers $headers -Body $body
    Write-Host "Response: $($resp | ConvertTo-Json -Depth 5)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host " Forged token correctly rejected (401 Unauthorized)" -ForegroundColor Green
    }
}