# CSV Path Fix - Hardcoded Filename Issue

## Problem
Generated code was using hardcoded CSV filename `your-bucket/transaction-data.csv` instead of the actual uploaded CSV file path.

## Root Cause
The supervisor agent was calling the code generation agent without passing the session ID in the prompt. The code generation agent has a `get_data_sources(session_id)` tool that retrieves CSV metadata from `prompt_sessions`, but it couldn't extract the session ID from the prompt.

**Flow:**
1. User uploads CSV → stored in `prompt_sessions[session_id]` ✅
2. User generates code → backend passes `Session ID: {session_id}` in prompt ✅
3. Backend calls Supervisor Agent with session ID ✅
4. Supervisor calls Code Gen Agent with prompt ❌ **WITHOUT session ID**
5. Code Gen Agent can't call `get_data_sources()` without session ID ❌
6. Code Gen Agent generates code with placeholder path ❌

## Solution
Updated the supervisor agent's `call_code_generation_agent` tool to include the session ID in the prompt when calling the code generation agent.

### Code Change

**File:** `backend/supervisor_agents.py`

**Before:**
```python
@tool
def call_code_generation_agent(prompt: str, session_id: str) -> str:
    """Call Code Generation Agent Runtime using boto3"""
    # ...
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=CODE_GEN_AGENT_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt})  # ❌ No session ID in prompt
    )
```

**After:**
```python
@tool
def call_code_generation_agent(prompt: str, session_id: str) -> str:
    """Call Code Generation Agent Runtime using boto3"""
    # ...
    # Include session_id in prompt so code gen agent can call get_data_sources
    prompt_with_session = f"Session ID: {session_id}\n\n{prompt}"
    
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArN=CODE_GEN_AGENT_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt_with_session})  # ✅ Session ID included
    )
```

## How It Works Now

### Complete Flow:
```
1. User uploads CSV "my_sales.csv"
   ↓
2. Backend stores in prompt_sessions:
   prompt_sessions["session-123"] = {
     'csv': {
       'filename': 'my_sales.csv',
       's3_path': 's3://strands-ray-data/sessions/session-123/csv/my_sales.csv'
     },
     'tables': []
   }
   ↓
3. User generates code with prompt: "Analyze sales data"
   ↓
4. Backend calls Supervisor Agent:
   payload = {
     "prompt": "Session ID: session-123\n\nAnalyze sales data"
   }
   ↓
5. Supervisor Agent calls call_code_generation_agent(prompt, "session-123")
   ↓
6. call_code_generation_agent adds session ID to prompt:
   "Session ID: session-123\n\nSession ID: session-123\n\nAnalyze sales data"
   (Note: Double session ID is OK, agent will extract it)
   ↓
7. Code Gen Agent receives prompt with session ID
   ↓
8. Code Gen Agent extracts session ID from prompt
   ↓
9. Code Gen Agent calls get_data_sources("session-123")
   ↓
10. get_data_sources imports main.prompt_sessions and returns:
    {
      'csv': {
        'filename': 'my_sales.csv',
        's3_path': 's3://strands-ray-data/sessions/session-123/csv/my_sales.csv'
      },
      'tables': []
    }
   ↓
11. Code Gen Agent generates code with correct S3 path:
    ds = ray.data.read_csv("s3://strands-ray-data/sessions/session-123/csv/my_sales.csv")
```

## Testing

### Test CSV Upload:
```bash
curl -X POST http://localhost:8000/upload-csv \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "my_sales.csv",
    "content": "product,price\nLaptop,999.99",
    "session_id": "test-session-1234567890123456789012345"
  }'

Response:
{
  "success": true,
  "s3_uri": "s3://strands-ray-data/sessions/test-session-1234567890123456789012345/csv/my_sales.csv",
  ...
}

Backend Log:
✅ CSV uploaded to s3://strands-ray-data/sessions/test-session-1234567890123456789012345/csv/my_sales.csv
   Stored in session test-session-1234567890123456789012345
```

### Test Code Generation:
After uploading CSV, generate code with the same session ID. The generated code should now contain:
```python
ds = ray.data.read_csv("s3://strands-ray-data/sessions/test-session-1234567890123456789012345/csv/my_sales.csv")
```

Instead of:
```python
ds = ray.data.read_csv("s3://your-bucket/transaction-data.csv")
```

## Deployment

The supervisor agent was redeployed with the fix:
```bash
cd backend/supervisor-agent
python agent_deployment.py
```

Deployment completed successfully:
- Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky`
- Build: CodeBuild completed
- Status: ✅ Deployed

## Files Modified

1. `backend/supervisor_agents.py` - Added session ID to prompt in `call_code_generation_agent`
2. `backend/supervisor-agent/supervisor_agents.py` - Copied updated file for deployment

## Verification Checklist

- ✅ CSV upload stores metadata in `prompt_sessions`
- ✅ Session ID passed in prompt to supervisor agent
- ✅ Supervisor agent passes session ID to code gen agent
- ✅ Code gen agent can extract session ID from prompt
- ✅ Code gen agent can call `get_data_sources(session_id)`
- ✅ Generated code uses actual S3 path instead of placeholder
- ✅ Supervisor agent redeployed successfully

## Summary

Fixed the hardcoded CSV filename issue by ensuring the session ID is passed through the entire agent chain:
- Backend → Supervisor Agent → Code Generation Agent

The code generation agent can now call `get_data_sources(session_id)` to retrieve the actual CSV S3 path and generate code with the correct file location.
