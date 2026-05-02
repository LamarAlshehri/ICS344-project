$REGION = "eu-north-1"

# Fix 1 — Remove AmazonCognitoPowerUser from ORDER-MANAGER
aws iam detach-role-policy `
  --role-name "serverlessrepo-OWASP-DVSA-OrderManagerFunctionRole-sWDhca9tvoX9" `
  --policy-arn "arn:aws:iam::aws:policy/AmazonCognitoPowerUser"

# Fix 2 — Remove AmazonDynamoDBFullAccess from ADMIN-GET-ORDERS
aws iam detach-role-policy `
  --role-name "serverlessrepo-OWASP-DVSA-AdminGetOrdersRole-drgaI77NTJQl" `
  --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"

# Fix 3 — Remove AWSLambda_FullAccess from ADMIN-GET-ORDERS
aws iam detach-role-policy `
  --role-name "serverlessrepo-OWASP-DVSA-AdminGetOrdersRole-drgaI77NTJQl" `
  --policy-arn "arn:aws:iam::aws:policy/AWSLambda_FullAccess"

# Fix 4 — Remove AmazonDynamoDBFullAccess from ADMIN-UPDATE-ORDERS
aws iam detach-role-policy `
  --role-name "serverlessrepo-OWASP-DVSA-AdminUpdateOrdersFunction-YVUaFpXZV1Ug" `
  --policy-arn "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"

# Fix 5 — Remove AWSLambda_FullAccess from ADMIN-UPDATE-ORDERS
aws iam detach-role-policy `
  --role-name "serverlessrepo-OWASP-DVSA-AdminUpdateOrdersFunction-YVUaFpXZV1Ug" `
  --policy-arn "arn:aws:iam::aws:policy/AWSLambda_FullAccess"

Write-Host "Policies detached. Running verification..." -ForegroundColor Green

# Verification — re-run Phase 1 scan to confirm fixes
$functions = @("DVSA-ORDER-MANAGER","DVSA-ADMIN-GET-ORDERS","DVSA-ADMIN-UPDATE-ORDERS")
foreach ($fn in $functions) {
    $roleArn  = aws lambda get-function-configuration --function-name $fn --region $REGION --query 'Role' --output text
    $roleName = $roleArn.Split('/')[-1]
    Write-Host ""
    Write-Host "=== $fn ===" -ForegroundColor Cyan
    aws iam list-attached-role-policies --role-name $roleName --output json
}