"""Code Generation Agent - AI-powered Ray code generator without validation"""

import os
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
app = BedrockAgentCoreApp()

@tool
def get_data_sources(session_id: str) -> dict:
    """Get available CSV files and Glue tables for the session
    
    Note: This tool cannot access local backend data when running in AgentCore.
    Data sources should be passed in the prompt instead.
    """
    # Agent runs in AWS container, cannot import from local main.py
    # Return empty to indicate no data sources available via this method
    return {"csv": None, "tables": [], "note": "Data sources should be passed in prompt"}

def create_code_generation_agent(system_prompt: str = None):
    """Create AI-powered code generation agent with custom system prompt"""
    
    model = BedrockModel(model_id='us.amazon.nova-premier-v1:0')
    
    # Use provided system prompt or minimal default
    if not system_prompt:
        system_prompt = "Generate Ray code based on the prompt. Return only executable Python code."
    
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[get_data_sources],
        name="CodeGenerationAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Code Generation Agent runtime"""
    prompt = payload.get("prompt", "")
    system_prompt = payload.get("system_prompt")
    
    # Create agent with system prompt from supervisor
    agent = create_code_generation_agent(system_prompt)
    
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
