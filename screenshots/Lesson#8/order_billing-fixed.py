import json
import urllib3
import boto3
import os
import time
import decimal
from decimal import Decimal
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print(json.dumps(event))
    
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                if o % 1 > 0:
                    return float(o)
                else:
                    return int(o)
            return super(DecimalEncoder, self).default(o)

    orderId = event["orderId"]
    userId = event["user"]
    http = urllib3.PoolManager()
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ["ORDERS_TABLE"])
    
    # ========== CRITICAL FIX: Use atomic conditional update ==========
    # First, try to reserve the order (set a temporary status or check)
    # We'll use a conditional update to change status from 100 to 200 (processing)
    # This prevents multiple concurrent billing attempts
    
    try:
        # Attempt to mark order as "processing" (200) only if it's currently "open" (100)
        processing_response = table.update_item(
            Key={"orderId": orderId, "userId": userId},
            UpdateExpression='SET orderStatus = :processing',
            ConditionExpression='orderStatus = :open',
            ExpressionAttributeValues={
                ':processing': 200,
                ':open': 100
            },
            ReturnValues='UPDATED_NEW'
        )
        print("Order reserved for billing")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {"status": "err", "msg": "Order already processed – race condition prevented"}
        else:
            raise e
    
    # Now proceed with billing (order is now status 200 – processing)
    response = table.get_item(
        Key={"orderId": orderId, "userId": userId},
        AttributesToGet=['orderId', 'orderStatus', 'itemList']
    )
    if 'Item' not in response:
        return {"status": "err", "msg": "could not find order"}
    
    # Calculate cart total
    data_dict = []
    for key, value in response["Item"]['itemList'].items():
        data_dict.append({"itemId": key, "quantity": int(value)})
    data = json.dumps(data_dict, cls=DecimalEncoder)
    
    url = os.environ["GET_CART_TOTAL"]
    req = http.request("POST", url, body=data, headers={'Content-Type': 'application/json'})
    res = json.loads(req.data)
    cartTotal = float(res['total'])
    missings = res.get("missing", {})
    
    # Process payment
    url = os.environ["PAYMENT_PROCESS_URL"]
    billing_data = json.dumps(event["billing"])
    req = http.request("POST", url, body=billing_data, headers={'Content-Type': 'application/json'})
    res = json.loads(req.data)
    ts = int(time.time())
    
    if res['status'] == 110:
        # Payment failed – revert status to 100 (open) or 110 (payment-failed)
        table.update_item(
            Key={"orderId": orderId, "userId": userId},
            UpdateExpression='SET orderStatus = :failed',
            ExpressionAttributeValues={':failed': 110}
        )
        return {"status": "err", "msg": "invalid payment details"}
    
    if res['status'] == 120:
        # Payment succeeded – update to paid (120)
        update_expression = 'SET orderStatus = :orderstatus, paymentTS = :paymentTS, totalAmount = :total, confirmationToken = :token'
        expression_attributes = {
            ':orderstatus': 120,
            ':paymentTS': ts,
            ':total': Decimal(cartTotal).quantize(Decimal('0.01')),
            ':token': res['confirmation_token']
        }
        
        if missings:
            new_item_list = {}
            items = response["Item"].get("itemList", {})
            for item in items:
                new_item_list[item] = items[item] - missings[item] if missings.get(item) else items[item]
            expression_attributes[":il"] = new_item_list
            update_expression += ', itemList = :il'
        
        table.update_item(
            Key={"orderId": orderId, "userId": userId},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attributes
        )
        
        # Send SQS message
        sqs = boto3.client('sqs')
        sqs.send_message(
            QueueUrl=os.environ["SQS_URL"],
            MessageBody=json.dumps({"orderId": orderId, "userId": userId}),
            DelaySeconds=10
        )
        return {"status": "ok", "amount": float(cartTotal), "token": res['confirmation_token'], "missing": missings}
    else:
        # Unknown payment status – revert to 110
        table.update_item(
            Key={"orderId": orderId, "userId": userId},
            UpdateExpression='SET orderStatus = :failed',
            ExpressionAttributeValues={':failed': 110}
        )
        return {"status": "err", "msg": "could not process payment"}