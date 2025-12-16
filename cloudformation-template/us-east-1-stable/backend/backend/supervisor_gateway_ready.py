"""Supervisor Agent ready for AgentCore Gateway integration"""

import os
import json
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
app = BedrockAgentCoreApp()

# AgentCore Gateway configuration (to be updated with actual ARN)
GATEWAY_ARN = 'arn:aws:bedrock-agentcore-gateway:us-east-1:025523569182:gateway/ray-validation-gateway'
TARGET_NAME = 'ray-validation-lambda'

@tool
def get_data_sources(session_id: str) -> dict:
    """Get available CSV files and Glue tables"""
    try:
        from main import prompt_sessions
        if session_id not in prompt_sessions:
            return {"csv": None, "tables": []}
        prompt_data = prompt_sessions[session_id]
        return {"csv": prompt_data['csv'], "tables": prompt_data['tables']}
    except ImportError:
        return {"csv": None, "tables": []}

@tool
def generate_ray_code(prompt: str, session_id: str, data_sources: dict) -> str:
    """Generate Ray code based on prompt and available data sources"""
    
    csv_info = data_sources.get('csv')
    tables_info = data_sources.get('tables', [])
    
    # Enhanced code generation with better prompt parsing
    if "sum" in prompt.lower() and "filter" in prompt.lower():
        if "odd" in prompt.lower():
            filter_condition = "x[\"id\"] % 2 == 1"
        elif "even" in prompt.lower():
            filter_condition = "x[\"id\"] % 2 == 0"
        else:
            filter_condition = "x[\"id\"] > 0"
        
        # Extract range from prompt
        if "1 to 50" in prompt or "1-50" in prompt:
            end_range = 51
        elif "1 to 100" in prompt or "1-100" in prompt:
            end_range = 101
        else:
            end_range = 11
        
        code = f"""import ray

ds = ray.data.range(1, {end_range})
filtered_ds = ds.filter(lambda x: {filter_condition})
result = filtered_ds.sum("id")
print(f"Result: {{result}}")"""
        
    elif csv_info:
        code = f"""import ray

ds = ray.data.read_csv("{csv_info['s3_path']}")
result = ds.take_all()
print(f"CSV rows: {{len(result)}}")
for row in result[:3]:
    print(row)"""
        
    else:
        code = f"""import ray

ds = ray.data.range(1, 11)
result = ds.take_all()
print(f"Generated data: {{result}}")"""
    
    return code

@tool
def validate_via_agentcore_gateway(code: str, ray_cluster_ip: str = "100.27.32.218") -> dict:
    """Validate Ray code using AgentCore Gateway with Cognito EZ Auth"""
    try:
        # Use AgentCore SDK for Gateway authentication
        from bedrock_agentcore.gateway import GatewayClient
        
        # Initialize Gateway client with Cognito EZ Auth
        gateway_client = GatewayClient(
            gateway_arn=GATEWAY_ARN,
            auth_type="COGNITO_EZ_AUTH"
        )
        
        # Prepare payload
        payload = {
            "code": code,
            "ray_cluster_ip": ray_cluster_ip
        }
        
        # Invoke Gateway target
        response = gateway_client.invoke_target(
            target_name=TARGET_NAME,
            payload=json.dumps(payload),
            content_type="application/json"
        )
        
        # Parse response
        if response.get('statusCode') == 200:
            result = json.loads(response.get('body', '{}'))
            return result
        else:
            return {
                "success": False,
                "error": f"Gateway error: {response.get('statusCode')} - {response.get('body', 'Unknown error')}"
            }
        
    except ImportError:
        # Fallback: Direct Lambda invocation (temporary)
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        try:
            payload = {"code": code, "ray_cluster_ip": ray_cluster_ip}
            response = lambda_client.invoke(
                FunctionName='ray-code-validation',
                Payload=json.dumps(payload)
            )
            result = json.loads(response['Payload'].read())
            return json.loads(result.get('body', '{}'))
        except Exception as e:
            return {"success": False, "error": f"Lambda fallback failed: {e}"}
        
    except Exception as e:
        return {"success": False, "error": f"Gateway validation failed: {e}"}

model = BedrockModel(model_id='us.anthropic.claude-sonnet-4-5-20250929-v1:0')

supervisor_agent = Agent(
    model=model,
    system_prompt="""You are a Supervisor Agent that orchestrates Ray code generation and validation via AgentCore Gateway.

WORKFLOW:
1. Extract session_id from user prompt (format: "Session ID: xxx")
2. Call get_data_sources(session_id) to get available data
3. Use generate_ray_code(prompt, session_id, data_sources) to generate code
4. Use validate_via_agentcore_gateway(code) to validate via Gateway
5. If validation fails, generate improved code and validate again
6. Repeat up to 5 times total or until validation succeeds
7. Return the final validated code

RULES:
- Always get data sources first and pass to code generation
- Always validate via AgentCore Gateway after generation
- If validation succeeds (success=True), return that code immediately
- If validation fails, analyze error and improve code generation
- Maximum 5 attempts total
- Use available CSV/table data when present

RESPONSE FORMAT:
Return ONLY the validated Python code that passed Gateway validation.""",
    tools=[get_data_sources, generate_ray_code, validate_via_agentcore_gateway],
    name="SupervisorAgentWithGateway"
)

@app.entrypoint
def invoke(payload):
    prompt = payload.get("prompt")
    ray_cluster_ip = payload.get("ray_cluster_ip", "100.27.32.218")
    
    enhanced_prompt = f"{prompt}\nRay Cluster IP: {ray_cluster_ip}"
    response = supervisor_agent(enhanced_prompt)
    
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

if __name__ == "__main__":
    app.run()
