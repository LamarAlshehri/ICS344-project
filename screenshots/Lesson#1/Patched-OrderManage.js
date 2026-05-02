// const serialize = require('node-serialize');  // REMOVED – insecure
const { LambdaClient, InvokeCommand } = require("@aws-sdk/client-lambda");
const { CognitoIdentityProviderClient, AdminGetUserCommand } = require("@aws-sdk/client-cognito-identity-provider");
const jose = require('node-jose');

exports.handler = async (event, context, callback) => {
    // SAFE: Parse body using JSON.parse
    let req;
    try {
        req = JSON.parse(event.body);
    } catch (e) {
        const response = {
            statusCode: 400,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Invalid JSON body" })
        };
        return callback(null, response);
    }
    // Headers are already an object – no need to deserialize
    const headers = event.headers;

    const auth_header = headers.Authorization || headers.authorization;
    if (!auth_header || !auth_header.startsWith('Bearer ')) {
        const response = {
            statusCode: 401,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Missing or invalid Authorization header" })
        };
        return callback(null, response);
    }
    const token = auth_header.split(' ')[1];
    const token_sections = token.split('.');
    const auth_data = jose.util.base64url.decode(token_sections[1]);
    const tokenPayload = JSON.parse(auth_data);
    const user = tokenPayload.username;
    let isAdmin = false;

    const params = {
        UserPoolId: process.env.userpoolid,
        Username: user
    };

    try {
        const cognito = new CognitoIdentityProviderClient();
        const command = new AdminGetUserCommand(params);
        const userData = await cognito.send(command);
        const attrs = userData.UserAttributes;
        for (let i = 0; i < attrs.length; i++) {
            if (attrs[i].Name === "custom:is_admin") {
                isAdmin = attrs[i].Value === "true";
                break;
            }
        }
        const action = req.action;
        let isOk = true;
        let payload = {};
        let functionName = "";

        switch (action) {
            case "new":
                payload = { user, cartId: req["cart-id"], items: req["items"] };
                functionName = "DVSA-ORDER-NEW";
                break;
            case "update":
                payload = { user, orderId: req["order-id"], items: req["items"] };
                functionName = "DVSA-ORDER-UPDATE";
                break;
            case "cancel":
                payload = { user, orderId: req["order-id"] };
                functionName = "DVSA-ORDER-CANCEL";
                break;
            case "get":
                payload = { user, orderId: req["order-id"], isAdmin };
                functionName = "DVSA-ORDER-GET";
                break;
            case "orders":
                payload = { user };
                functionName = "DVSA-ORDER-ORDERS";
                break;
            case "account":
                payload = { user };
                functionName = "DVSA-USER-ACCOUNT";
                break;
            case "profile":
                payload = { user, profile: req["data"] };
                functionName = "DVSA-USER-PROFILE";
                break;
            case "shipping":
                payload = { user, orderId: req["order-id"], shipping: req["data"] };
                functionName = "DVSA-ORDER-SHIPPING";
                break;
            case "billing":
                payload = { user, orderId: req["order-id"], billing: req["data"] };
                functionName = "DVSA-ORDER-BILLING";
                break;
            case "complete":
                payload = { orderId: req["order-id"] };
                functionName = "DVSA-ORDER-COMPLETE";
                break;
            case "inbox":
                payload = { action: "inbox", user };
                functionName = "DVSA-USER-INBOX";
                break;
            case "message":
                payload = { action: "get", user, msgId: req["msg-id"], type: req["type"] };
                functionName = "DVSA-USER-INBOX";
                break;
            case "delete":
                payload = { action: "delete", user, msgId: req["msg-id"] };
                functionName = "DVSA-USER-INBOX";
                break;
            case "upload":
                payload = { user, file: req["attachment"] };
                functionName = "DVSA-FEEDBACK-UPLOADS";
                break;
            case "feedback":
                const feedbackResp = {
                    statusCode: 200,
                    headers: { "Access-Control-Allow-Origin": "*" },
                    body: JSON.stringify({ status: "ok", message: `Thank you ${req["data"]["name"]}.` })
                };
                return callback(null, feedbackResp);
            case "admin-orders":
                if (isAdmin) {
                    payload = { user, data: req["data"] };
                    functionName = "DVSA-ADMIN-GET-ORDERS";
                    break;
                } else {
                    const forbiddenResp = {
                        statusCode: 403,
                        headers: { "Access-Control-Allow-Origin": "*" },
                        body: JSON.stringify({ status: "err", message: "Unauthorized" })
                    };
                    return callback(null, forbiddenResp);
                }
            default:
                isOk = false;
        }

        if (isOk) {
            const lambda = new LambdaClient();
            const invokeCmd = new InvokeCommand({
                FunctionName: functionName,
                InvocationType: 'RequestResponse',
                Payload: JSON.stringify(payload)
            });
            const resp = await lambda.send(invokeCmd);
            const data = JSON.parse(Buffer.from(resp.Payload).toString());
            const successResp = {
                statusCode: 200,
                headers: { "Access-Control-Allow-Origin": "*" },
                body: JSON.stringify(data)
            };
            return callback(null, successResp);
        } else {
            const unknownResp = {
                statusCode: 200,
                headers: { "Access-Control-Allow-Origin": "*" },
                body: JSON.stringify({ status: "err", msg: "unknown action" })
            };
            return callback(null, unknownResp);
        }
    } catch (err) {
        console.error(err);
        const errorResp = {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Internal server error" })
        };
        return callback(null, errorResp);
    }
};