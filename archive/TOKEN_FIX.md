# Fix for "Invalid Bearer token" Error

## The Problem

You're getting this error:
```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "error": {
    "code": -32001,
    "message": "Invalid Bearer token"
  }
}
```

## Why This Happens

The Gateway is configured to accept **ID tokens** (from user authentication), but the scripts were sending **access tokens** (from OAuth2 client credentials).

### Token Types:

| Token Type | Use Case | Audience | Works with Gateway? |
|------------|----------|----------|---------------------|
| **ID Token** | User authentication | Client ID | ✅ YES |
| **Access Token** | Service-to-service | Resource server | ❌ NO |

The Gateway's JWT configuration expects:
- **Audience**: Your Cognito App Client ID
- **Issuer**: Cognito User Pool
- **Token Type**: ID Token (JWT with user claims)

## The Fix

Use **user authentication** instead of client credentials.

### Updated Scripts:

1. ✅ **`test-with-user-token.sh`** - NEW! Uses ID token
2. ✅ **`simple-test.sh`** - FIXED! Now uses ID token

## How to Test Now

### Option 1: Quick Test (Recommended)

```bash
cd scripts
./test-with-user-token.sh
```

This will:
1. Create a test user automatically
2. Get an ID token
3. Send "what is 5+5" to the Gateway
4. Show the response

### Option 2: Simple Test

```bash
cd scripts
./simple-test.sh
```

### Option 3: Custom Prompt

```bash
cd scripts
./test-with-user-token.sh "create a dataframe with 10 rows"
```

## Manual Testing

If you want to test manually:

```bash
# 1. Get configuration
USER_POOL_ID="your-user-pool-id"
CLIENT_ID="your-client-id"
GATEWAY_URL="your-gateway-url"

# 2. Create test user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --password "TestPass123!" \
  --permanent

# 3. Get ID token
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=test@example.com,PASSWORD=TestPass123!)

ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')

# 4. Send request
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "invoke_agent",
      "arguments": {
        "prompt": "what is 5+5"
      }
    }
  }'
```

## What Changed

### Before (Wrong):
```bash
# Getting access token (OAuth2 client credentials)
TOKEN=$(curl -X POST "$TOKEN_ENDPOINT" \
  -H "Authorization: Basic $AUTH_HEADER" \
  -d "grant_type=client_credentials" \
  -d "scope=spark-api/spark.execute" | jq -r '.access_token')
```

### After (Correct):
```bash
# Getting ID token (user authentication)
ID_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USER,PASSWORD=$PASS \
  | jq -r '.AuthenticationResult.IdToken')
```

## Token Comparison

### Access Token (OAuth2 - Doesn't Work):
```json
{
  "sub": "client-id",
  "token_use": "access",
  "scope": "spark-api/spark.execute",
  "aud": "spark-api",  // ❌ Wrong audience
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123"
}
```

### ID Token (User Auth - Works):
```json
{
  "sub": "user-uuid",
  "email": "test@example.com",
  "token_use": "id",
  "aud": "your-client-id",  // ✅ Correct audience
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_ABC123"
}
```

## Alternative: Update Gateway Configuration

If you want to use client credentials (access tokens), you would need to update the Gateway configuration to accept them. However, this requires changing the `AllowedAudience` to match the resource server identifier.

**Current Gateway Config:**
```yaml
AllowedAudience:
  - !Ref CognitoUserPoolClient  # Expects client ID
```

**For Access Tokens (would need):**
```yaml
AllowedAudience:
  - spark-api  # Resource server identifier
```

But for now, **using ID tokens (user authentication) is the correct approach**.

## Summary

✅ **Use**: `./test-with-user-token.sh`  
❌ **Don't use**: Client credentials access tokens  
✅ **Token type**: ID Token from user authentication  
✅ **Audience**: Cognito App Client ID  

---

**Ready to test?**
```bash
cd scripts
./test-with-user-token.sh
```

This should now work without the "Invalid Bearer token" error! 🎉
