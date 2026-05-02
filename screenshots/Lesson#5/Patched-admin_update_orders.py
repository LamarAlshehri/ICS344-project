import json
import boto3
import os
import uuid
import time
import base64
import decimal
import jsonpickle
from botocore.exceptions import ClientError

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

# ========== HELPER: CHECK ADMIN STATUS VIA COGNITO ==========
def is_admin(username):
    cognito = boto3.client('cognito-idp')
    try:
        user_data = cognito.admin_get_user(
            UserPoolId=os.environ['userpoolid'],   # environment variable set by SAM
            Username=username
        )
    except Exception as e:
        print(f"Error fetching user: {e}")
        return False
    for attr in user_data['UserAttributes']:
        if attr['Name'] == 'custom:is_admin' and attr['Value'] == 'true':
            return True
    return False

# ========== ORIGINAL HELPER FUNCTIONS (unchanged) ==========
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

def getItem(orderId, user):
    key = {"orderId": orderId}
    response = table.get_item(Key=key)
    unpickled = jsonpickle.decode(json.dumps(response["Item"], cls=DecimalEncoder))
    return {"status": "ok", "msg": unpickled}

def updateItem(orderId, user, obj, ts):
    update_expr = 'SET itemList = :itemList, orderStatus = :orderStatus, address = :address, confirmationToken = :token, paymentTS = :ts, totalAmount = :total'
    response = table.update_item(
        Key={"orderId": orderId, "userId": user},
        UpdateExpression=update_expr,
        ExpressionAttributeValues={
            ':itemList': obj['itemList'],
            ':orderStatus': obj['status'],
            ':address': obj['address'],
            ':token': obj['token'],
            ':ts': obj['ts'],
            ':total': obj['total']
        }
    )
    return {"status": "ok", "msg": "order updated"}

# ========== MAIN HANDLER WITH ADMIN CHECK ==========
def lambda_handler(event, context):
    # Extract authorization header
    if "authorization" in event["headers"]:
        auth_header = event["headers"]["authorization"]
    elif "Authorization" in event["headers"]:
        auth_header = event["headers"]["Authorization"]
    else:
        return {"status": "err", "msg": "Unknown user. Are you an admin?"}

    # Decode JWT (handle potential missing padding)
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

    # ========== ADMIN CHECK – FIX FOR LESSON #5 ==========
    if not is_admin(user):
        return {
            "status": "err",
            "msg": "Unauthorized – admin privileges required"
        }

    # Proceed with original logic (only admin reaches here)
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
        res = addItem(user, item, ts)
    elif action == "delete":
        res = deleteItem(orderId, user)
    elif action == "update":
        res = updateItem(orderId, user, item, ts)
    else:
        res = {"status": "err", "msg": "unknown command"}

    return res