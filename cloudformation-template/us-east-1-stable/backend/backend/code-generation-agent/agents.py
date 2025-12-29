"""Code Generation Agent - AI-powered Ray code generator without validation"""

import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# Get region from boto3 session
session = boto3.Session()
AWS_REGION = session.region_name or 'us-east-1'

def create_code_generation_agent(model_id=None):
    """Create AI-powered code generation agent"""
    
    model = BedrockModel(model_id=model_id)
    
    agent = Agent(
        model=model,
        system_prompt="""You are a Ray distributed computing code generation specialist.

WORKFLOW:
1. Look for data sources in the prompt (CSV files and Glue tables)
2. Generate Ray code based on the user request and available data sources
3. Return ONLY the Python code without explanations

DATA SOURCES IN PROMPT:
The prompt will contain available data sources in this format:

CSV Files:
  Available CSV file:
    - Filename: sales.csv
    - S3 Path: s3://bucket/sessions/abc/csv/sales.csv

Glue Tables:
  Available Glue tables:
    - database_name.table_name at s3://bucket/path/to/data

RAY OPERATIONS:
- ray.init() - Initialize Ray
- @ray.remote - Decorator for remote functions
- ray.data.read_csv(s3_path) - Read CSV from S3
- ray.data.read_sql(sql, connection_uri) - Read from SQL query (use for Glue tables)
- .map(lambda x: {...}) - Transform data (return dict)
- .filter(lambda x: condition) - Filter data
- .take_all() - Get results
- ray.get() - Get results from remote functions
- print() - Output results

CRITICAL RULES:
- NEVER use pandas
- Always include ray.init()
- Use @ray.remote for distributed functions
- Include print() statements for output
- For CSV files: Use exact S3 path from "S3 Path:" line with ray.data.read_csv()
- For Glue tables: Use ray.data.read_sql() with SQL query like "SELECT * FROM database.table"
- Generate proper distributed Ray code for the requested task

GLUE TABLE PATTERN:
For Glue table "database.table":
ds = ray.data.read_sql("SELECT * FROM database.table", connection_uri="awsathena://")

RETURN FORMAT:
Return ONLY the Python code (no markdown, no explanations).""",
        tools=[],
        name="CodeGenerationAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Code Generation Agent runtime"""
    prompt = payload.get("prompt", "")
    system_prompt = payload.get("system_prompt", None)
    model_id = payload.get("model_id")
    
    if not model_id:
        raise ValueError("❌ ERROR: No model_id provided to code generation agent. Please ensure model_id is passed from supervisor agent.")
    
    print(f"🔧 Code Gen Agent using model: {model_id}")
    
    # Create code generation agent with custom or default system prompt
    if system_prompt:
        model = BedrockModel(model_id=model_id)
        agent = Agent(
            model=model,
            system_prompt=system_prompt,
            tools=[],
            name="CodeGenerationAgent"
        )
    else:
        agent = create_code_generation_agent(model_id)
    
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
