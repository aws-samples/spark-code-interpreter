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

app = BedrockAgentCoreApp()

# Get region from boto3 session
session = boto3.Session()
AWS_REGION = session.region_name or 'us-east-1'

# Global variables to store runtime configuration
CURRENT_MODEL_ID = None
CURRENT_GATEWAY_URL = None
CURRENT_CODE_GEN_ARN = None

def make_signed_mcp_request(payload):
    """Make signed request to MCP Gateway"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=CURRENT_GATEWAY_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', AWS_REGION).add_auth(request)
    
    response = requests.post(
        CURRENT_GATEWAY_URL,
        data=request.body,
        headers=dict(request.headers),
        timeout=300
    )
    
    return response

@tool
def validate_ray_code(code: str, ray_cluster_ip: str = "172.31.80.237") -> str:
    """Validate Ray code using MCP Gateway - returns the validated code if successful"""
    if code.startswith("AGENT_ERROR:") or code.startswith("EXTRACTION_ERROR:"):
        return f"VALIDATION_SKIPPED: {code}"
    
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
                    "ray_cluster_ip": ray_cluster_ip
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
                content_array = result['result']['content']
                if content_array is None or len(content_array) == 0:
                    return f"VALIDATION_ERROR: MCP Gateway returned empty content array"
                
                content = content_array[0]['text']
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
def execute_ray_code(code: str, ray_cluster_ip: str = "172.31.80.237") -> str:
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
                    "ray_cluster_ip": ray_cluster_ip
                }
            }
        }
        
        response = make_signed_mcp_request(tool_request)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'result' in result and 'content' in result['result']:
                content_array = result['result']['content']
                if content_array is None or len(content_array) == 0:
                    return f"EXECUTION_ERROR: MCP Gateway returned empty content array"
                
                content = content_array[0]['text']
                
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

# Global variable to store model_id for tools
CURRENT_MODEL_ID = None

@tool
def call_code_generation_agent(prompt: str, session_id: str) -> str:
    """Call Code Generation Agent Runtime using boto3"""
    agentcore_client = boto3.client(
        'bedrock-agentcore', 
        region_name=AWS_REGION,
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    # Ray-specific system prompt
    ray_system_prompt = """You are a Ray distributed computing code generation specialist.

CRITICAL: Generate Ray code for distributed processing. Use Ray Dataset API as the primary interface.

Generate Python code using Ray for distributed data processing.

DATA SOURCES IN PROMPT:
Look for data sources in the prompt:
- CSV: "Filename: x.csv" and "S3 Path: s3://..."
- Glue: "database.table at s3://..."

RAY OPERATIONS:
- ray.init() - Initialize Ray (REQUIRED at start)
- ray.data.read_csv(s3_path) - Read CSV files
- ray.data.read_sql(sql, connection_uri="awsathena://") - Read from Glue tables
- .map(lambda x: {...}) - Transform data (return dict)
- .map_batches(fn) - Transform batches (can use pandas inside)
- .filter(lambda x: ...) - Filter data
- .take_all() - Get results
- .count() - Count rows
- .show() - Display data
- @ray.remote - Decorator for remote functions
- print() - Output results

PANDAS USAGE:
- You CAN use pandas, but ONLY within Ray's distributed context
- Use pandas inside .map_batches() for batch processing
- Use pandas inside @ray.remote functions for distributed operations
- DO NOT use standalone pandas operations outside Ray context
- Example: ds.map_batches(lambda batch: batch.groupby('col').sum())

CRITICAL RULES:
1. ALWAYS use ray.init() at the start
2. Use Ray Dataset API (ray.data) as the primary interface
3. For data loading: Use ray.data.read_csv() or ray.data.read_sql()
4. For distributed processing: Use Ray operations (.map, .map_batches, .filter)
5. Pandas is allowed INSIDE Ray operations (map_batches, @ray.remote functions)
6. Ensure proper distributed processing with Ray
7. Include print() statements for output

EXAMPLE RAY CODE WITH PANDAS:
```python
import ray
import pandas as pd

ray.init()

# Read data using Ray
ds = ray.data.read_csv("s3://bucket/file.csv")

# Use pandas within Ray's distributed context
def process_batch(batch: pd.DataFrame) -> pd.DataFrame:
    return batch.groupby('category').agg({'value': 'sum'})

result = ds.map_batches(process_batch).take_all()
print(result)
```

Return ONLY Python code using Ray for distributed processing, no markdown, no explanations."""
    
    try:
        # Include session_id in prompt so code gen agent can call get_data_sources
        prompt_with_session = f"Session ID: {session_id}\n\n{prompt}"
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=CURRENT_CODE_GEN_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({
                "prompt": prompt_with_session,
                "system_prompt": ray_system_prompt,
                "model_id": CURRENT_MODEL_ID
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

def create_supervisor_agent(model_id=None):
    """Create supervisor agent that orchestrates code generation and validation"""
    # Use provided model_id or raise error if missing
    if not model_id:
        raise ValueError("❌ ERROR: No model_id provided to Ray supervisor agent. Please ensure model_id is passed from backend context.")
    
    model = BedrockModel(model_id=model_id, max_tokens=16000)
    
    agent = Agent(
        model=model,
        system_prompt="""You are a Supervisor Agent that orchestrates Ray code generation and validation with iterative refinement.

RAY CLUSTER IP: The ray_cluster_ip will be provided in the context. Use it when calling validate_ray_code and execute_ray_code.

REQUEST TYPES:
1. EXECUTE_ONLY: If prompt starts with "EXECUTE_ONLY:", extract the code and call execute_ray_code(code, ray_cluster_ip). Return ONLY the raw output from execute_ray_code with NO additional text, commentary, or formatting.
2. GENERATE: For all other prompts, follow the generation workflow below.

MANDATORY GENERATION WORKFLOW - YOU MUST FOLLOW ALL STEPS:
1. Call call_code_generation_agent(prompt, session_id) to generate Ray code
2. Call extract_ray_code(response) to extract clean Python code  
3. MANDATORY: Call validate_ray_code(code, ray_cluster_ip) to validate on Ray cluster - YOU MUST DO THIS STEP
4. If validation succeeds, validate_ray_code returns the validated code - return it
5. If validation fails, analyze the error and retry from step 1 with error feedback
6. Maximum 5 attempts - return last error if all attempts fail

CRITICAL: YOU MUST ALWAYS CALL validate_ray_code AFTER EXTRACTING CODE. NEVER SKIP VALIDATION.

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
- When validate_ray_code returns code, return that exact code with nothing else
- NEVER return code without validation - validation is MANDATORY""",
        tools=[call_code_generation_agent, extract_ray_code, validate_ray_code, execute_ray_code],
        name="SupervisorAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Supervisor Agent runtime"""
    try:
        prompt = payload.get("prompt", "")
        model_id = payload.get("model_id")  # Extract model_id from payload
        gateway_url = payload.get("gateway_url")  # Extract gateway_url from payload
        code_gen_agent_arn = payload.get("code_gen_agent_arn")  # Extract code_gen_agent_arn from payload
        # Generate proper session ID with required 33+ characters
        import uuid
        session_id = f"supervisor-{uuid.uuid4().hex}"  # 43 characters
        ray_cluster_ip = payload.get("ray_cluster_ip", "172.31.80.237")
        
        # Set global variables for tools to use - no fallbacks, use exactly what's passed
        global CURRENT_MODEL_ID, CURRENT_GATEWAY_URL, CURRENT_CODE_GEN_ARN
        CURRENT_MODEL_ID = model_id
        CURRENT_GATEWAY_URL = gateway_url
        CURRENT_CODE_GEN_ARN = code_gen_agent_arn
        
        print(f"🚀 Supervisor Agent processing: {prompt}")
        print(f"🔧 Using model: {model_id}")
        print(f"🌐 Using gateway: {gateway_url}")
        print(f"🤖 Using code gen ARN: {code_gen_agent_arn}")
        print(f"   Ray Cluster IP: {ray_cluster_ip}")
        
        # Create supervisor agent
        agent = create_supervisor_agent(model_id)
        
        # Invoke agent with ray_cluster_ip in context
        context = f"Ray Cluster IP: {ray_cluster_ip}\n\nGenerate and validate Ray code: {prompt}"
        response = agent(context)
        
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
