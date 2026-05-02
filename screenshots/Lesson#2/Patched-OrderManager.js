const { LambdaClient, InvokeCommand } = require("@aws-sdk/client-lambda");
const { CognitoIdentityProviderClient, AdminGetUserCommand } = require("@aws-sdk/client-cognito-identity-provider");
const jose = require('node-jose');
const https = require('https');

// Cache JWKS to avoid fetching on every invocation
let cachedJwks = null;
const jwksUri = `https://cognito-idp.eu-north-1.amazonaws.com/eu-north-1_Df1mGs7NK/.well-known/jwks.json`;

async function getJwks() {
    if (cachedJwks) return cachedJwks;
    return new Promise((resolve, reject) => {
        https.get(jwksUri, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    const jwks = JSON.parse(data);
                    cachedJwks = jwks;
                    resolve(jwks);
                } catch (err) { reject(err); }
            });
        }).on('error', reject);
    });
}

async function verifyToken(token) {
    const parts = token.split('.');
    if (parts.length !== 3) throw new Error('Invalid token format');
    const header = JSON.parse(Buffer.from(parts[0], 'base64').toString());
    const kid = header.kid;
    if (!kid) throw new Error('No kid in header');
    const jwks = await getJwks();
    const key = jwks.keys.find(k => k.kid === kid);
    if (!key) throw new Error('No matching public key found');
    const publicKey = await jose.JWK.asKey(key);
    const verified = await jose.JWS.createVerify(publicKey).verify(token);
    return JSON.parse(verified.payload.toString());
}

exports.handler = async (event, context, callback) => {
    // --- SAFE JSON PARSING (replaces node-serialize) ---
    let req;
    try {
        req = JSON.parse(event.body);
    } catch (e) {
        return callback(null, {
            statusCode: 400,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Invalid JSON body" })
        });
    }
    const headers = event.headers;

    // --- EXTRACT AND VERIFY JWT ---
    const auth_header = headers.Authorization || headers.authorization;
    if (!auth_header || !auth_header.startsWith('Bearer ')) {
        return callback(null, {
            statusCode: 401,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Missing or invalid Authorization header" })
        });
    }
    const token = auth_header.split(' ')[1];
    let verifiedPayload;
    try {
        verifiedPayload = await verifyToken(token);
    } catch (err) {
        console.error("JWT verification failed:", err);
        return callback(null, {
            statusCode: 401,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Invalid token signature" })
        });
    }

    // Use verified username
    const user = verifiedPayload.username;
    let isAdmin = false;

    // --- FETCH USER ADMIN STATUS FROM COGNITO ---
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
    } catch (err) {
        console.error("Failed to fetch user attributes:", err);
        return callback(null, {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "Internal server error" })
        });
    }

    // --- ORIGINAL BUSINESS LOGIC (switch cases) ---
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
        try {
            const resp = await lambda.send(invokeCmd);
            const data = JSON.parse(Buffer.from(resp.Payload).toString());
            const successResp = {
                statusCode: 200,
                headers: { "Access-Control-Allow-Origin": "*" },
                body: JSON.stringify(data)
            };
            return callback(null, successResp);
        } catch (err) {
            console.error("Lambda invocation failed:", err);
            return callback(null, {
                statusCode: 500,
                headers: { "Access-Control-Allow-Origin": "*" },
                body: JSON.stringify({ status: "err", msg: "Internal server error" })
            });
        }
    } else {
        const unknownResp = {
            statusCode: 200,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ status: "err", msg: "unknown action" })
        };
        return callback(null, unknownResp);
    }
};