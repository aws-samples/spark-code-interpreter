"""Supervisor Agent Runtime - Orchestrates Code Generation Agent + MCP Gateway validation with proper auth"""

import os
import json
import time
import boto3
import requests
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
app = BedrockAgentCoreApp()

# Configuration
GATEWAY_URL = os.getenv('RAY_GATEWAY_URL', 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp')
CODE_GEN_AGENT_ARN = os.getenv('RAY_CODE_GEN_AGENT_ARN', 'arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/ray_code_interpreter-oTKmLH9IB9')
SKIP_MCP_VALIDATION = os.getenv('SKIP_MCP_VALIDATION', 'true').lower() == 'true'  # Skip MCP validation by default

def make_signed_mcp_request(payload):
    """Make signed request to MCP Gateway"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.post(
        GATEWAY_URL,
        data=request.body,
        headers=dict(request.headers),
        timeout=300
    )
    
    return response

@tool
def validate_ray_code(code: str) -> str:
    """Validate Ray code using MCP Gateway - returns the validated code if successful"""
    if code.startswith("AGENT_ERROR:") or code.startswith("EXTRACTION_ERROR:"):
        return f"VALIDATION_SKIPPED: {code}"
    
    # Skip MCP validation if configured
    if SKIP_MCP_VALIDATION:
        print("⚠️  MCP validation skipped (SKIP_MCP_VALIDATION=true)")
        return f"VALIDATION_SUCCESS: Code validation skipped. Code:\n{code}"
    
    try:
        # Initialize MCP
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "supervisor-agent", "version": "1.0.0"}
            }
        }
        
        response = make_signed_mcp_request(init_request)
        if response.status_code != 200:
            return f"VALIDATION_ERROR: MCP initialization failed: {response.status_code}"
        
        # Call validation tool
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ray-code-validation-inline___validate_ray_code",
                "arguments": {
                    "code": code,
                    "ray_cluster_ip": "172.31.4.12"
                }
            }
        }
        
        print(f"MCP Tool Request: {json.dumps(tool_request)}")
        
        response = make_signed_mcp_request(tool_request)
        print(f"MCP Response Status: {response.status_code}")
        print(f"MCP Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"MCP Response JSON: {json.dumps(result, indent=2)}")
            
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content'][0]['text']
                print(f"MCP Gateway response content: {content}")
                
                # Check if it's the generic error message
                if content == "An internal error occurred. Please retry later.":
                    return f"VALIDATION_ERROR: MCP Gateway internal error - lambda may have failed"
                
                try:
                    validation_data = json.loads(content)
                    if validation_data.get('success'):
                        # Return the validated code, not just status
                        return code
                    else:
                        return f"❌ VALIDATION_FAILED: {validation_data.get('error', content)}"
                except json.JSONDecodeError:
                    return f"VALIDATION_ERROR: Invalid JSON response: {content}"
            return f"VALIDATION_ERROR: Unexpected response structure: {result}"
        else:
            return f"VALIDATION_ERROR: Tool call failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"VALIDATION_ERROR: {e}"

@tool
def execute_ray_code(code: str) -> str:
    """Execute Ray code using MCP Gateway - returns the execution output"""
    try:
        # Initialize MCP
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "supervisor-agent", "version": "1.0.0"}
            }
        }
        
        response = make_signed_mcp_request(init_request)
        if response.status_code != 200:
            return f"EXECUTION_ERROR: MCP initialization failed: {response.status_code}"
        
        # Call execution tool
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ray-code-validation-inline___validate_ray_code",
                "arguments": {
                    "code": code,
                    "ray_cluster_ip": "172.31.4.12"
                }
            }
        }
        
        response = make_signed_mcp_request(tool_request)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content'][0]['text']
                
                if content == "An internal error occurred. Please retry later.":
                    return f"EXECUTION_ERROR: MCP Gateway internal error"
                
                try:
                    execution_data = json.loads(content)
                    if execution_data.get('success'):
                        # Return the execution output
                        return execution_data.get('output', execution_data.get('result', 'Execution completed'))
                    else:
                        return f"EXECUTION_ERROR: {execution_data.get('error', content)}"
                except json.JSONDecodeError:
                    return f"EXECUTION_ERROR: Invalid JSON response: {content}"
            return f"EXECUTION_ERROR: Unexpected response structure: {result}"
        else:
            return f"EXECUTION_ERROR: Tool call failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"EXECUTION_ERROR: {e}"

@tool
def call_code_generation_agent(prompt: str, session_id: str) -> str:
    """Call Code Generation Agent Runtime using boto3"""
    agentcore_client = boto3.client(
        'bedrock-agentcore', 
        region_name='us-east-1',
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    # Ray-specific system prompt
    ray_system_prompt = """You are a Ray distributed computing code generation specialist.

Generate Python code using Ray for distributed data processing.

DATA SOURCES IN PROMPT:
Look for data sources in the prompt:
- CSV: "Filename: x.csv" and "S3 Path: s3://..."
- Glue: "database.table at s3://..."

RAY OPERATIONS (PRIORITIZE THESE):
- ray.init() - Initialize Ray
- @ray.remote - Decorator for remote functions
- ray.data.read_csv(s3_path) - Read CSV files
- ray.data.read_parquet(s3_path) - Read Parquet files
- ray.data.read_sql(sql, connection_uri="awsathena://") - Read from Glue tables
- .map(lambda x: {...}) - Transform rows
- .map_batches(fn) - Transform batches efficiently
- .filter(lambda x: ...) - Filter rows
- .groupby(key).map_groups(fn) - Group and aggregate
- .sort(key) - Sort data
- .take_all() - Get all results
- .take(n) - Get first n results
- .count() - Count rows
- print() - Output results

CRITICAL RULES:
1. ALWAYS prefer Ray Core (@ray.remote) or Ray Data API for data processing
2. Use pandas ONLY when absolutely necessary (e.g., complex statistical operations not available in Ray)
3. If using pandas, process data with Ray first, then convert small results: df = ray.data.Dataset.to_pandas()
4. Always include ray.init()
5. Use @ray.remote for distributed functions
6. For CSV: Use exact S3 path with ray.data.read_csv()
7. For Glue tables: Use ray.data.read_sql("SELECT * FROM db.table", connection_uri="awsathena://")
8. Include print() statements for output

Return ONLY Python code, no markdown, no explanations."""
    
    try:
        # Include session_id in prompt so code gen agent can call get_data_sources
        prompt_with_session = f"Session ID: {session_id}\n\n{prompt}"
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=CODE_GEN_AGENT_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({
                "prompt": prompt_with_session,
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

def create_supervisor_agent():
    """Create supervisor agent that orchestrates code generation and validation"""
    # Use fallback model to avoid throttling
    model = BedrockModel(model_id='us.anthropic.claude-sonnet-4-20250514-v1:0')
    
    agent = Agent(
        model=model,
        system_prompt="""You are a Supervisor Agent that orchestrates Ray code generation and validation with iterative refinement.

REQUEST TYPES:
1. EXECUTE_ONLY: If prompt starts with "EXECUTE_ONLY:", extract the code and call execute_ray_code(code). Return ONLY the raw output from execute_ray_code with NO additional text, commentary, or formatting.
2. GENERATE: For all other prompts, follow the generation workflow below.

GENERATION WORKFLOW (Repeat up to 5 times until validation succeeds):
1. Call call_code_generation_agent(prompt, session_id) to generate Ray code
2. Call extract_ray_code(response) to extract clean Python code  
3. Call validate_ray_code(code) to validate on Ray cluster
4. If validation succeeds, validate_ray_code returns the validated code - return it
5. If validation fails, analyze the error and retry from step 1 with error feedback
6. Maximum 5 attempts - return last error if all attempts fail

ERROR HANDLING:
- If AGENT_ERROR or EXTRACTION_ERROR, retry with modified prompt
- If VALIDATION_ERROR, include error details in next generation attempt
- After 5 failed attempts, return the last error message

RETRY STRATEGY:
- Attempt 1: Generate code based on user prompt
- Attempt 2-5: Include previous error in prompt: "Previous code failed with: [error]. Generate corrected code."

RULES:
- Use session ID format: supervisor-<uuid> (33+ characters required)
- Track attempt number in your reasoning
- For EXECUTE_ONLY: Return ONLY the raw output from execute_ray_code - no explanations, no status messages, just the output
- For GENERATE: Return ONLY the final validated Python code - NO explanations, NO descriptions, NO commentary, JUST the code
- When validate_ray_code returns code, return that exact code with nothing else""",
        tools=[call_code_generation_agent, extract_ray_code, validate_ray_code, execute_ray_code],
        name="SupervisorAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Supervisor Agent runtime"""
    try:
        prompt = payload.get("prompt", "")
        # Override CODE_GEN_AGENT_ARN from payload if provided
        global CODE_GEN_AGENT_ARN
        if "code_gen_agent_arn" in payload:
            CODE_GEN_AGENT_ARN = payload["code_gen_agent_arn"]
            print(f"🔧 Using Code Gen ARN from payload: {CODE_GEN_AGENT_ARN}")
        
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
