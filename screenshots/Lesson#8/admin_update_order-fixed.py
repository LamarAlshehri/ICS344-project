import json
import boto3
import os
import uuid
import time
import base64
import decimal
import jsonpickle

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ["ORDERS_TABLE"])

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def is_admin(username):
    cognito = boto3.client('cognito-idp')
    try:
        user_data = cognito.admin_get_user(
            UserPoolId=os.environ['userpoolid'],
            Username=username
        )
    except Exception as e:
        print(f"Error fetching user: {e}")
        return False
    for attr in user_data['UserAttributes']:
        if attr['Name'] == 'custom:is_admin' and attr['Value'] == 'true':
            return True
    return False

def lambda_handler(event, context):
    # Extract authorization header
    if "authorization" in event["headers"]:
        auth_header = event["headers"]["authorization"]
    elif "Authorization" in event["headers"]:
        auth_header = event["headers"]["Authorization"]
    else:
        return {"status": "err", "msg": "Unknown user. Are you an admin?"}
        
    token_sections = auth_header.split('.')
    try:
        auth_data = base64.b64decode(token_sections[1])
    except TypeError:
        try:
            auth_data = base64.b64decode(token_sections[1] + "=")
        except TypeError:
            try:
                auth_data = base64.b64decode(token_sections[1] + "==")
            except TypeError:
                return {"status": "err", "msg": "Could not parse authorization header"}
            
    token = json.loads(auth_data)
    user = token["username"]

    # Check if user is admin
    if not is_admin(user):
        return {"status": "err", "msg": "Unauthorized – admin privileges required"}

    # Parse request body
    if isinstance(event['body'], str):
        body = json.loads(event['body'])
    else:
        body = event['body']
    
    action = body.get('action')
    orderId = body.get('order-id')
    item = body.get('item')
    ts = int(time.time())

    if action == "add":
        # ========== FIX: Only add if order doesn't exist? Not needed for race condition ==========
        res = addItem(user, item, ts)
    elif action == "delete":
        res = deleteItem(orderId, user)
    elif action == "update":
        # ========== FIX: Conditional update – only update if order status is 100 ==========
        try:
            # First get current status
            get_response = table.get_item(Key={"orderId": orderId, "userId": user})
            if 'Item' not in get_response:
                return {"status": "err", "msg": "Order not found"}
            
            current_status = get_response['Item'].get('orderStatus', 0)
            
            # Only allow update if status is 100 (open)
            if current_status != 100:
                return {"status": "err", "msg": f"Cannot update order with status {current_status} – must be 100 (open)"}
            
            # Perform update with condition
            update_expr = 'SET itemList = :itemList, orderStatus = :orderStatus, address = :address, confirmationToken = :token, paymentTS = :ts, totalAmount = :total'
            response = table.update_item(
                Key={"orderId": orderId, "userId": user},
                UpdateExpression=update_expr,
                ConditionExpression='orderStatus = :expected_status',
                ExpressionAttributeValues={
                    ':itemList': item['itemList'],
                    ':orderStatus': item['status'],
                    ':address': item['address'],
                    ':token': item['token'],
                    ':ts': item['ts'],
                    ':total': item['total'],
                    ':expected_status': 100
                }
            )
            return {"status": "ok", "msg": "order updated"}
        except Exception as e:
            print(f"Update failed: {e}")
            return {"status": "err", "msg": "Order cannot be updated – status changed"}
    else:
        return {"status": "err", "msg": "unknown command"}

# Helper functions (keep from original)
def addItem(user, obj, ts):
    id = str(uuid.uuid4())
    response = table.put_item(
        Item={
            'orderId': id,
            'userId': obj['userId'],
            'orderStatus': obj['status'],
            'itemList': obj['itemList'],
            'address': obj['address'],
            'confirmationToken': obj['token'],
            'paymentTS': ts,
            'totalAmount': obj['total']
        }
    )
    return {"status": "ok", "msg": id}

def deleteItem(orderId, user):
    key = {"orderId": orderId}
    response = table.delete_item(Key=key)
    return {"status": "ok", "msg": "order deleted"}