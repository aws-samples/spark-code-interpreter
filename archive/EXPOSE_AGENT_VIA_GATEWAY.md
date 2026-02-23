# How to Expose Agent via Gateway for Natural Language Queries

## The Problem

Currently: Gateway → Lambda (requires PySpark code)
You want: Gateway → Agent → Lambda (accepts natural language)

## The Challenge

Gateway Targets have limitations:
- ✅ **Lambda targets**: Work, but require PySpark code input
- ❌ **Agent targets**: Not supported in Gateway Target API
- ⚠️ **MCP Server targets**: Require OAuth credentials (complex setup)

## Recommended Solutions

### Option 1: Create a Wrapper Lambda (Simplest)

Create a new Lambda function that:
1. Accepts natural language input
2. Calls the Spark Supervisor Agent
3. Returns the result

This Lambda becomes your Gateway Target.

**Pros:**
- Simple to implement
- Works with existing Gateway setup
- No OAuth configuration needed

**Cons:**
- Extra Lambda function to maintain

### Option 2: Use Gateway's Built-in Agent Integration (If Available)

Some AWS Console versions may have a direct "Agent" target type in the UI that's not exposed via CLI.

**Try this:**
1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/gateways
2. Click gateway: `dev-spark-gateway-0y5eyw5mag`
3. Targets tab → Add target
4. Look for target type options:
   - If you see "Agent" or "Bedrock Agent": Use that!
   - Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu`

**If this works**, you're done! The Gateway will accept natural language.

### Option 3: Configure MCP Server with OAuth (Complex)

If you want to expose the agent as an MCP server target, you need:
1. OAuth provider (Cognito already set up)
2. Agent MCP endpoint with OAuth
3. Gateway Target with OAuth credentials

This is complex and may not be necessary.

---

## Recommended: Option 1 - Wrapper Lambda

Let me create a simple wrapper Lambda for you:

### Lambda Function Code

```python
import json
import boto3

bedrock_agent = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    """
    Wrapper Lambda that accepts natural language and calls Spark Supervisor Agent
    """
    try:
        # Extract prompt from event
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            prompt = body.get('prompt', body.get('query', ''))
        else:
            prompt = event.get('prompt', event.get('query', ''))
        
        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing prompt or query parameter'})
            }
        
        # Agent ARN
        agent_arn = 'arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu'
        agent_id = agent_arn.split('/')[-1]
        
        # Create session
        session_response = bedrock_agent.create_agent_session(
            agentId=agent_id
        )
        session_id = session_response['sessionId']
        
        # Invoke agent
        response = bedrock_agent.invoke_agent(
            agentId=agent_id,
            sessionId=session_id,
            inputText=prompt
        )
        
        # Parse response (this is a streaming response)
        result = []
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    result.append(chunk['bytes'].decode('utf-8'))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'result': ''.join(result),
                'prompt': prompt
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Deploy Wrapper Lambda

1. Create file: `wrapper_lambda.py` with code above
2. Create deployment package:
   ```bash
   zip wrapper_lambda.zip wrapper_lambda.py
   ```
3. Create Lambda function:
   ```bash
   aws lambda create-function \
     --function-name dev-spark-agent-wrapper \
     --runtime python3.11 \
     --role arn:aws:iam::817323390093:role/dev-spark-lambda-role \
     --handler wrapper_lambda.lambda_handler \
     --zip-file fileb://wrapper_lambda.zip \
     --timeout 300 \
     --region us-east-1
   ```

4. Add Gateway Target for this Lambda:
   - Go to Console → Gateway → Add Target
   - Type: Lambda
   - Lambda ARN: (from above command output)
   - Tool Schema:
     ```json
     [
       {
         "name": "ask_agent",
         "description": "Ask Spark Supervisor Agent a natural language question",
         "inputSchema": {
           "type": "object",
           "properties": {
             "prompt": {
               "type": "string",
               "description": "Natural language query"
             }
           },
           "required": ["prompt"]
         }
       }
     ]
     ```

### Test

```bash
./ask-gateway.sh "what is 5+5"
```

This will now work with natural language!

---

## Alternative: Keep Current Setup

Your current Lambda target actually works fine if you:
1. Use it for direct PySpark execution (programmatic use)
2. Have your external application generate PySpark code
3. Or use the agent separately (not through Gateway)

The Gateway is just one way to expose functionality. You can also:
- Call the agent directly via SDK
- Call the Lambda directly with generated code
- Use both: Gateway for some use cases, direct calls for others

---

## Summary

**Easiest path forward:**
1. Check AWS Console for direct "Agent" target type (Option 2)
2. If not available, create wrapper Lambda (Option 1)
3. Or keep current setup and call agent separately

**Current working setup:**
- Gateway → Lambda (PySpark code input) ✅
- Direct agent calls (natural language) ✅

You have both options available, just not combined yet.

---

## Next Steps

Let me know which option you prefer:
1. I can create the wrapper Lambda for you
2. You can try the Console for direct Agent target
3. Or we can explore other architectures

What works best for your use case?
