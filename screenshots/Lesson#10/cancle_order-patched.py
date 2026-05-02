import json
import boto3
import os
import decimal

def lambda_handler(event, context):
    print(json.dumps(event))
    
    # ========== INPUT VALIDATION ==========
    if "orderId" not in event:
        return {
            "status": "err",
            "msg": "Missing required field: orderId"
        }
    if "user" not in event:
        return {
            "status": "err",
            "msg": "Missing required field: user"
        }
    
    try:
        orderId = event["orderId"]
        userId = event["user"]

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ["ORDERS_TABLE"])
        
        # Check if order exists and is cancellable
        response = table.get_item(
            Key={"orderId": orderId, "userId": userId},
            AttributesToGet=['orderStatus']
        )
        if 'Item' not in response:
            return {"status": "err", "msg": "could not find order"}

        if response["Item"]["orderStatus"] > 110:
            return {"status": "err", "msg": "order already paid"}

        # Delete the order
        delete_resp = table.delete_item(Key={"orderId": orderId, "userId": userId})
        if delete_resp['ResponseMetadata']['HTTPStatusCode'] == 200:
            return {"status": "ok", "msg": "order cancelled"}
        else:
            return {"status": "err", "msg": "could not cancel order"}
            
    except Exception as e:
        print(f"Internal error: {str(e)}")
        return {"status": "err", "msg": "Internal server error"}