# Fix for SECRET_HASH Error

## The Error

```
An error occurred (NotAuthorizedException) when calling the InitiateAuth operation: 
Client 4iv8rvt7r5ido99kg5is8sff6j is configured with secret but SECRET_HASH was not received
```

## Why This Happens

When you set `GenerateSecret: true` on the Cognito User Pool Client (which we did for service-to-service auth), Cognito requires a `SECRET_HASH` parameter for **all** authentication requests, including user password authentication.

## What is SECRET_HASH?

SECRET_HASH is a cryptographic hash calculated as:

```
SECRET_HASH = Base64(HMAC-SHA256(username + clientId, clientSecret))
```

## The Fix

All scripts have been updated to calculate and include the SECRET_HASH.

### Updated Scripts:

✅ `ask-gateway.sh` - Fixed  
✅ `test-with-user-token.sh` - Fixed  
✅ `simple-test.sh` - Fixed  
✅ `get-user-token.sh` - NEW! Helper to get tokens with SECRET_HASH  

## How to Test Now

### Option 1: Quick Test (Simplest)

```bash
cd scripts
./ask-gateway.sh "what is 5+5"
```

### Option 2: Get Token First

```bash
cd scripts
./get-user-token.sh

# Then use the token
TOKEN=$(cat /tmp/id_token.txt)
curl -X POST $GATEWAY_URL \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"invoke_agent","arguments":{"prompt":"what is 5+5"}}}'
```

### Option 3: Full Test

```bash
cd scripts
./test-with-user-token.sh
```

## Manual SECRET_HASH Calculation

If you need to calculate SECRET_HASH manually:

```bash
# Get your values
USERNAME="test@example.com"
CLIENT_ID="your-client-id"
CLIENT_SECRET="your-client-secret"

# Calculate SECRET_HASH
SECRET_HASH=$(echo -n "${USERNAME}${CLIENT_ID}" | \
  openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | \
  base64)

# Use in authentication
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters \
    USERNAME=$USERNAME,\
    PASSWORD=$PASSWORD,\
    SECRET_HASH=$SECRET_HASH
```

## Example: Complete Flow

```bash
# 1. Get configuration
USER_POOL_ID="us-east-1_ABC123"
CLIENT_ID="4iv8rvt7r5ido99kg5is8sff6j"
USERNAME="test@example.com"
PASSWORD="TestPass123!"

# 2. Get client secret
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text)

# 3. Calculate SECRET_HASH
SECRET_HASH=$(echo -n "${USERNAME}${CLIENT_ID}" | \
  openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | \
  base64)

# 4. Authenticate
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters \
    USERNAME=$USERNAME,\
    PASSWORD=$PASSWORD,\
    SECRET_HASH=$SECRET_HASH
```

## Why We Need This

We enabled `GenerateSecret: true` to support **OAuth2 client credentials** for service-to-service authentication. This is required for:

- ✅ Service-to-service authentication (access tokens)
- ✅ Secure client identification
- ✅ OAuth2 compliance

**Side effect:** Now user authentication also requires SECRET_HASH.

## Alternative: Separate Clients

If you want to avoid SECRET_HASH for user auth, you could create two separate clients:

1. **User Client** - No secret, for user authentication
2. **Service Client** - With secret, for service-to-service

But for now, using SECRET_HASH works fine for both use cases.

## Verification

To verify your SECRET_HASH is correct:

```bash
cd scripts
./get-user-token.sh

# Should show:
# ✅ Tokens obtained successfully!
# ID Token: eyJraWQiOiJ...
```

## Common Issues

### Issue 1: "SECRET_HASH was not received"
**Solution:** Make sure you're calculating and passing SECRET_HASH

### Issue 2: "Invalid SECRET_HASH"
**Solution:** Verify the calculation:
- Input must be: `username + clientId` (concatenated, no separator)
- HMAC key must be: `clientSecret`
- Algorithm: SHA-256
- Output: Base64 encoded

### Issue 3: "Client secret not found"
**Solution:** Make sure CloudFormation update completed successfully

## Test Commands

```bash
# Test 1: Get token
./scripts/get-user-token.sh

# Test 2: Ask a question
./scripts/ask-gateway.sh "what is 5+5"

# Test 3: Full test
./scripts/test-with-user-token.sh
```

## Summary

✅ **Problem:** Client has secret, requires SECRET_HASH  
✅ **Solution:** Calculate SECRET_HASH = Base64(HMAC-SHA256(username+clientId, secret))  
✅ **Scripts:** All updated to include SECRET_HASH  
✅ **Test:** `./ask-gateway.sh "what is 5+5"`  

---

**Ready to test?**

```bash
cd scripts
./ask-gateway.sh "what is 5+5"
```

This should now work! 🎉
