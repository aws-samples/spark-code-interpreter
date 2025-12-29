"""Code Generation Agent - Only generates Ray code without validation"""

import os
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
app = BedrockAgentCoreApp()

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
    
    # Handle prime numbers
    if "prime" in prompt.lower():
        if "first 10" in prompt.lower() or "10 prime" in prompt.lower():
            count = 10
        elif "first 20" in prompt.lower() or "20 prime" in prompt.lower():
            count = 20
        else:
            count = 10
            
        code = f"""import ray

@ray.remote
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

@ray.remote
def find_primes(start, end):
    primes = []
    for num in range(start, end):
        if ray.get(is_prime.remote(num)):
            primes.append(num)
    return primes

ray.init()

# Find first {count} prime numbers
primes = []
start = 2
batch_size = 100

while len(primes) < {count}:
    batch_primes = ray.get(find_primes.remote(start, start + batch_size))
    primes.extend(batch_primes)
    start += batch_size

primes = primes[:{count}]
print(f"First {count} prime numbers: {{primes}}")"""
        
    elif "sum" in prompt.lower() and "filter" in prompt.lower():
        if "odd" in prompt.lower():
            filter_condition = "x[\"id\"] % 2 == 1"
        elif "even" in prompt.lower():
            filter_condition = "x[\"id\"] % 2 == 0"
        else:
            filter_condition = "x[\"id\"] > 0"
        
        if "1 to 50" in prompt or "1-50" in prompt:
            end_range = 51
        elif "1 to 100" in prompt or "1-100" in prompt:
            end_range = 101
        elif "1 to 20" in prompt or "1-20" in prompt:
            end_range = 21
        elif "1 to 10" in prompt or "1-10" in prompt:
            end_range = 11
        else:
            end_range = 11
        
        code = f"""import ray

ds = ray.data.range({end_range})
filtered_ds = ds.filter(lambda x: {filter_condition})
result = filtered_ds.sum("id")
print(f"Result: {{result}}")"""
        
    elif csv_info:
        code = f"""import ray

ds = ray.data.read_csv("{csv_info['s3_path']}")
result = ds.take_all()
print(f"CSV rows: {{len(result)}}")"""
        
    else:
        code = f"""import ray

ds = ray.data.range(11)
result = ds.take_all()
print(f"Data: {{result}}")"""
    
    return code

def create_code_generation_agent():
    """Create code generation agent that only generates code"""
    
    model = BedrockModel(model_id='us.anthropic.claude-sonnet-4-5-20250929-v1:0')
    
    agent = Agent(
        model=model,
        system_prompt="""You are a Code Generation Agent that generates Ray code only.

WORKFLOW:
1. Extract session_id from user prompt
2. Call get_data_sources(session_id) to get available data
3. Use generate_ray_code(prompt, session_id, data_sources) to generate code
4. Return ONLY the generated Python code

RULES:
- Only generate code, do NOT validate
- Return ONLY Python code without explanations
- Use available CSV/table data when present
- Keep responses minimal to avoid token limits

RESPONSE FORMAT:
Return ONLY the Python code without markdown, explanations, or additional text.""",
        tools=[get_data_sources, generate_ray_code],
        name="CodeGenerationAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Code Generation Agent runtime"""
    prompt = payload.get("prompt", "")
    
    # Create code generation agent
    agent = create_code_generation_agent()
    
    # Invoke agent
    response = agent(prompt)
    
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
