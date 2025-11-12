"""Supervisor Agent Runtime - Orchestrates Code Generation Agent + AgentCore Gateway"""

import os
import json
import base64
import boto3
import requests
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway_config import GATEWAY_URL, CLIENT_ID, TOKEN_URL, USER_POOL_ID, CODE_GEN_AGENT_ARN, RAY_CLUSTER_IP

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
app = BedrockAgentCoreApp()

def get_cognito_client_secret():
    """Get Cognito client secret from AWS"""
    client = boto3.client("cognito-idp")
    response = client.describe_user_pool_client(
        UserPoolId=USER_POOL_ID,
        ClientId=CLIENT_ID
    )
    return response["UserPoolClient"]["ClientSecret"]

def get_gateway_client():
    """Create authenticated MCP client for AgentCore Gateway"""
    client_secret = get_cognito_client_secret()
    
    # Get access token
    creds_response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {base64.b64encode(f'{CLIENT_ID}:{client_secret}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"}
    )
    
    access_token = creds_response.json()['access_token']
    
    # Create MCP client with auth
    return MCPClient(lambda: streamablehttp_client(
        GATEWAY_URL, 
        headers={"Authorization": f"Bearer {access_token}"}
    ))

def get_full_tools_list(client):
    """List all tools with pagination support"""
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            pagination_token = tmp_tools.pagination_token
    return tools

@tool
def validate_ray_code(code: str) -> str:
    """Validate Ray code using AgentCore Gateway"""
    if code.startswith("AGENT_ERROR:") or code.startswith("EXTRACTION_ERROR:"):
        return f"VALIDATION_SKIPPED: {code}"
    
    try:
        import uuid
        gateway_client = get_gateway_client()
        with gateway_client:
            # Call validation tool directly
            result = gateway_client.call_tool_sync(
                tool_use_id=f"validate-{uuid.uuid4().hex}",
                name="ray-code-validation-execution___validate_ray_code",
                arguments={
                    "code": code,
                    "ray_cluster_ip": RAY_CLUSTER_IP
                }
            )
            
            # Result is a dict with 'content' key
            if isinstance(result, dict) and 'content' in result:
                result_str = result['content'][0]['text']
            else:
                result_str = str(result)
            
            # Parse JSON response
            try:
                result_data = json.loads(result_str)
                if result_data.get('success'):
                    return f"✅ VALIDATED: Job {result_data.get('job_id')} {result_data.get('status')}"
                else:
                    return f"❌ VALIDATION_FAILED: {result_data.get('error', result_str)}"
            except json.JSONDecodeError:
                if "success" in result_str.lower():
                    return f"✅ VALIDATED: {result_str}"
                else:
                    return f"❌ VALIDATION_FAILED: {result_str}"
                
    except Exception as e:
        return f"VALIDATION_ERROR: {e}"

@tool
def execute_ray_code(code: str) -> str:
    """Execute Ray code using AgentCore Gateway"""
    try:
        import uuid
        gateway_client = get_gateway_client()
        with gateway_client:
            # Call validation tool (it also executes and returns output)
            result = gateway_client.call_tool_sync(
                tool_use_id=f"execute-{uuid.uuid4().hex}",
                name="ray-code-validation-execution___validate_ray_code",
                arguments={
                    "code": code,
                    "ray_cluster_ip": RAY_CLUSTER_IP
                }
            )
            
            # Result is a dict with 'content' key
            if isinstance(result, dict) and 'content' in result:
                result_str = result['content'][0]['text']
            else:
                result_str = str(result)
            
            # Parse JSON and extract output
            try:
                result_data = json.loads(result_str)
                return result_data.get('output', result_str)
            except json.JSONDecodeError:
                return result_str
                
    except Exception as e:
        return f"EXECUTION_ERROR: {e}"

@tool
def call_code_generation_agent(prompt: str, session_id: str) -> str:
    """Call Code Generation Agent Runtime using boto3"""
    agentcore_client = boto3.client(
        'bedrock-agentcore', 
        region_name='us-east-1',
        config=boto3.session.Config(read_timeout=45, connect_timeout=10)
    )
    
    ray_system_prompt = """You are a Ray distributed computing code generation specialist.

WORKFLOW:
1. Extract data sources from the prompt (CSV files and Glue tables)
2. Extract CSV schema from preview if provided
3. Generate Ray code based on the user request and available data sources
4. ALWAYS include print() statements to display ALL results
5. Return ONLY the Python code without explanations

RAY CODE REQUIREMENTS:
- Always start with: import ray; ray.init()
- Use @ray.remote decorator for distributed functions
- For CSV files: ray.data.read_csv("s3://exact-path-from-prompt")
- For CSV files: Use EXACT column names from Schema/Preview
- ALWAYS include print() statements with descriptive labels for ALL results

GLUE TABLE READING (PRIORITY ORDER):
For Glue table "database.table at s3://location/":

1. FIRST TRY: Use awswrangler to query via Athena (PREFERRED):
```python
import awswrangler as wr
df = wr.athena.read_sql_query("SELECT * FROM database.table", database="database")
ds = ray.data.from_pandas(df)
```

2. IF awswrangler unavailable, try PyAthena:
```python
from pyathena import connect
import pandas as pd
conn = connect(s3_staging_dir='s3://aws-athena-query-results-...')
df = pd.read_sql("SELECT * FROM database.table", conn)
ds = ray.data.from_pandas(df)
```

3. FALLBACK: Read directly from S3 (detect format from path):
- If path ends with .parquet or contains /parquet/: ray.data.read_parquet("s3://location/")
- If path ends with .csv or contains /csv/: ray.data.read_csv("s3://location/")
- If path ends with .json: ray.data.read_json("s3://location/")
- Otherwise try: ray.data.read_parquet("s3://location/")

OUTPUT REQUIREMENTS:
- Every computation result MUST be printed
- Use descriptive print statements: print("Description:", value)
- For lists: iterate and print each item
- For aggregations: print final value with label

CSV SCHEMA:
If prompt shows CSV preview like:
```
name,age,city
John,30,NYC
```
Use columns: name, age, city (exact case and spelling)

RETURN FORMAT:
Return ONLY executable Python code (no markdown, no explanations)."""
    
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=CODE_GEN_AGENT_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({
                "prompt": prompt,
                "system_prompt": ray_system_prompt
            })
        )
        
        response_body = response["response"].read()
        if response_body:
            try:
                result = json.loads(response_body.decode("utf-8"))
                return str(result) if not isinstance(result, str) else result
            except json.JSONDecodeError:
                return response_body.decode("utf-8")
        return "AGENT_ERROR: No response from code generation agent"
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "throttling" in error_msg.lower():
            return f"AGENT_ERROR: Code generation agent unavailable - {error_msg}"
        return f"AGENT_ERROR: Code generation failed - {error_msg}"

@tool
def extract_ray_code(response_text: str) -> str:
    """Extract Ray code from agent response"""
    import re
    
    # Check for agent errors first
    if response_text.startswith("AGENT_ERROR:"):
        return response_text  # Pass through error
    
    # Look for code blocks
    code_block_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # Look for import ray statements
    lines = response_text.split('\n')
    code_lines = []
    in_code = False
    
    for line in lines:
        if 'import ray' in line:
            in_code = True
        if in_code and line.strip():
            code_lines.append(line)
    
    extracted_code = '\n'.join(code_lines) if code_lines else ""
    
    # If no code found, return error
    if not extracted_code or len(extracted_code.strip()) < 10:
        return f"EXTRACTION_ERROR: No valid Ray code found in response: {response_text[:200]}..."
    
    return extracted_code

@tool
def extract_code_from_execute_prompt(prompt: str) -> str:
    """Extract code from EXECUTE_ONLY prompt"""
    # EXECUTE_ONLY format: "EXECUTE_ONLY: Run this code and return the execution output:\n\n{code}"
    if not prompt.startswith("EXECUTE_ONLY:"):
        return "ERROR: Not an EXECUTE_ONLY prompt"
    
    # Split by the marker and get everything after the double newline
    parts = prompt.split("\n\n", 1)
    if len(parts) < 2:
        return "ERROR: Invalid EXECUTE_ONLY format"
    
    return parts[1].strip()

def create_supervisor_agent():
    """Create supervisor agent that orchestrates code generation and validation"""
    model = BedrockModel(model_id='us.amazon.nova-premier-v1:0')
    
    agent = Agent(
        model=model,
        system_prompt="""You handle two types of requests:

TYPE 1: EXECUTE_ONLY (when prompt starts with "EXECUTE_ONLY:")
- Call extract_code_from_execute_prompt(prompt) to get the code
- Call execute_ray_code(code) ONCE with the extracted code
- Return the execution output directly

TYPE 2: GENERATE AND VALIDATE (all other prompts)
- Iterate up to 5 times to get validated Ray code
- STEP 1: Call call_code_generation_agent(prompt, session_id)
- STEP 2: Call extract_ray_code(response)
- STEP 3: Call validate_ray_code(code)
- STEP 4: Check validation result:
  * If "✅ VALIDATED" → STOP and return the code
  * If "❌ VALIDATION_FAILED" or "VALIDATION_ERROR" → GO TO STEP 5
  * If "AGENT_ERROR" or "EXTRACTION_ERROR" → GO TO STEP 5
- STEP 5: Retry with error feedback (max 5 attempts total)
  * Modify prompt: "Previous attempt failed: [error]. Fix and regenerate."
  * GO BACK TO STEP 1

CRITICAL RULES:
- For EXECUTE_ONLY: Use extract_code_from_execute_prompt() then execute_ray_code()
- For generation: MUST attempt validation at least once
- MUST retry up to 5 times if validation fails
- ONLY stop early if you see "✅ VALIDATED"
- After 5 failed attempts, return: "ERROR: Failed after 5 attempts: [last error]"
- Session ID format: supervisor-<uuid>

RETURN FORMAT:
- Execution: Return the execution output only
- Success: Return the validated Python code only
- Failure: Return "ERROR: Failed after 5 attempts: [details]" """,
        tools=[call_code_generation_agent, extract_ray_code, validate_ray_code, execute_ray_code, extract_code_from_execute_prompt],
        name="SupervisorAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Supervisor Agent runtime"""
    try:
        prompt = payload.get("prompt", "")
        # Generate proper session ID with required 33+ characters
        import uuid
        session_id = f"supervisor-{uuid.uuid4().hex}"  # 43 characters
        
        print(f"🚀 Supervisor Agent processing: {prompt}")
        
        # Create supervisor agent
        agent = create_supervisor_agent()
        
        # Invoke agent
        response = agent(f"Generate and validate Ray code: {prompt}")
        
        # Extract text content
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            content_text = ""
            for block in response.message.content:
                if hasattr(block, 'text'):
                    content_text += block.text
            return content_text
        elif hasattr(response, 'content'):
            return response.content
        else:
            return str(response)
            
    except Exception as e:
        print(f"❌ Supervisor Agent error: {e}")
        return f"Supervisor Agent error: {e}"

if __name__ == "__main__":
    app.run()
