# Model Update to Claude Sonnet 4.5

## Status: Code Updated, Deployment Pending

The code has been updated to use Claude Sonnet 4.5 as the default model. You need to redeploy both the agent and wrapper Lambda.

## Changes Made

### 1. Spark Supervisor Agent ✅
**File**: `agent-code/spark-supervisor-agent/spark_supervisor_agent.py`

**Change**: Added default model_id instead of raising error

```python
# Before
if not model_id:
    raise ValueError("❌ ERROR: No model_id found in runtime configuration...")

# After
if not model_id:
    model_id = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
    print(f"ℹ️  No model_id provided, using default: {model_id}")
```

### 2. Wrapper Lambda ✅
**File**: `agent-wrapper/agent_wrapper.py`

**Change**: Updated model_id to Claude Sonnet 4.5

```python
# Before
'model_id': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',

# After
'model_id': 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
```

## Deployment Steps

### Quick Deploy (Both Components)

```bash
# After refreshing AWS credentials
./scripts/redeploy-with-new-model.sh
```

This script will:
1. Deploy Spark Supervisor Agent with updated code
2. Deploy Wrapper Lambda with updated code
3. Save agent ARN to config
4. Verify both deployments

### Manual Deploy (Step by Step)

#### Step 1: Deploy Spark Supervisor Agent ⚠️ REQUIRED

The agent code was modified and MUST be redeployed.

**Option A: Using bedrock-agentcore CLI**
```bash
cd agent-code/spark-supervisor-agent
bedrock-agentcore deploy
```

**Option B: Via AWS Console**
1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/agents
2. Find agent: `spark_supervisor_agent-kSQUxI8Tqu`
3. Click "Edit"
4. Update the agent code with: `agent-code/spark-supervisor-agent/spark_supervisor_agent.py`
5. Save and deploy

#### Step 2: Deploy Wrapper Lambda ⚠️ REQUIRED

The wrapper Lambda was also modified and MUST be redeployed.

```bash
zip -j /tmp/agent_wrapper_updated.zip agent-wrapper/agent_wrapper.py

aws lambda update-function-code \
  --function-name dev-spark-agent-wrapper \
  --zip-file fileb:///tmp/agent_wrapper_updated.zip \
  --region us-east-1
```

**Or use the deployment script**:
```bash
./scripts/deploy-agent-wrapper.sh
```

## Testing After Deployment

### Test Wrapper Lambda
```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"what is 7*10"}' \
  --region us-east-1 \
  /tmp/test_model.json

# Wait 60 seconds
sleep 60

# Check response
cat /tmp/test_model.json | jq '.body' -r | jq '.'
```

### Expected Behavior
- ✅ No more "No model_id found" error
- ✅ Agent uses Claude Sonnet 4.5 by default
- ✅ Wrapper Lambda passes Claude Sonnet 4.5 explicitly
- ✅ Complete flow works end-to-end

## Model Information

**Model ID**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

**Model Name**: Claude Sonnet 4.5

**Benefits**:
- Latest Claude model
- Better performance
- Higher rate limits
- Improved code generation

## CloudFormation Update

The CloudFormation template should also be updated to reflect the new default model:

**File**: `cloudformation/spark-complete-stack.yml`

```yaml
Parameters:
  BedrockModel:
    Type: String
    Default: us.anthropic.claude-sonnet-4-5-20250929-v1:0  # Updated
    Description: Bedrock model ID (Claude Sonnet 4.5)
```

This change is optional since the code now has defaults, but it's good for documentation.

## Verification Checklist

After deployment:

- [ ] Wrapper Lambda updated (check Last Modified timestamp)
- [ ] Spark Supervisor Agent updated
- [ ] Test with simple calculation: "what is 7*10"
- [ ] Check CloudWatch logs for model_id
- [ ] Verify no "No model_id found" errors
- [ ] Test S3 write functionality
- [ ] Verify session-based S3 structure

## Quick Commands

### Update Wrapper Lambda
```bash
# After refreshing credentials
zip -j /tmp/agent_wrapper.zip agent-wrapper/agent_wrapper.py
aws lambda update-function-code \
  --function-name dev-spark-agent-wrapper \
  --zip-file fileb:///tmp/agent_wrapper.zip \
  --region us-east-1
```

### Test
```bash
./scripts/test-calculation.sh "what is 7*10"
```

### Check Logs
```bash
# Wrapper Lambda logs
aws logs tail /aws/lambda/dev-spark-agent-wrapper --follow

# Spark Lambda logs
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

## Summary

**Code Changes**: ✅ Complete (both files modified)
**Spark Supervisor Agent Deployment**: ⏳ Pending - REQUIRED
**Wrapper Lambda Deployment**: ⏳ Pending - REQUIRED

**BOTH components need redeployment** because both were modified:
1. Spark Supervisor Agent - Added default model_id fallback
2. Wrapper Lambda - Updated to pass Claude Sonnet 4.5

Once you refresh your AWS credentials:
```bash
./scripts/redeploy-with-new-model.sh
```

Or manually:
1. Deploy Spark Supervisor Agent: `cd agent-code/spark-supervisor-agent && bedrock-agentcore deploy`
2. Deploy Wrapper Lambda: `./scripts/deploy-agent-wrapper.sh`
3. Test: `./scripts/test-calculation.sh "what is 7*10"`

---

**Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
**Status**: Ready for deployment
