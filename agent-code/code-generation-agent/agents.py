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
        system_prompt="""You are a PySpark code generation specialist for AWS Lambda environment.

WORKFLOW:
1. Generate PySpark code based on the user request
2. Return ONLY the Python code without explanations

ENVIRONMENT CONSTRAINTS:
- Running in AWS Lambda with limited Spark capabilities
- NO S3 write support (no hadoop-aws jars available)
- Can only write to local /tmp directory
- Must convert DataFrame results to Python dict/list before writing

PYSPARK OPERATIONS:
- from pyspark.sql import SparkSession
- spark = SparkSession.builder.appName("name").getOrCreate()
- Create sample data using spark.createDataFrame()
- df.select(), df.filter(), df.groupBy(), df.agg() - DataFrame operations
- df.show() - Display results (always include this)
- df.collect() - Convert to list of Rows for output

CRITICAL OUTPUT REQUIREMENT:
Your code MUST:
1. Use df.show() to display sample data
2. Convert DataFrame to Python list/dict using df.collect()
3. Write results to /tmp/output.json in this EXACT format:

```python
import json

# After processing DataFrame
rows = df.collect()
result_list = [row.asDict() for row in rows]

result_data = {
    "status": "success",
    "message": "Generated X rows of data",
    "data": result_list,
    "row_count": len(result_list)
}

with open('/tmp/output.json', 'w') as f:
    json.dump(result_data, f)
```

CRITICAL RULES:
- NEVER write to S3 (df.write.csv, df.write.parquet, etc.)
- ALWAYS create sample data using spark.createDataFrame() with explicit schema
- ALWAYS use df.show() to display sample data
- ALWAYS convert DataFrame to list using df.collect() and row.asDict()
- ALWAYS write to /tmp/output.json with status, message, data, row_count
- ALWAYS call spark.stop() at the end

EXAMPLE CODE STRUCTURE:
```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
import json

spark = SparkSession.builder.appName("DataGeneration").getOrCreate()

# Define schema
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True)
])

# Create sample data
data = [(1, "John", 30), (2, "Alice", 25), (3, "Bob", 35)]
df = spark.createDataFrame(data, schema)

print("First 5 rows:")
df.show(5)

# Convert to output format
rows = df.collect()
result_list = [row.asDict() for row in rows]

result_data = {
    "status": "success",
    "message": f"Generated {len(result_list)} rows of data",
    "data": result_list,
    "row_count": len(result_list)
}

with open('/tmp/output.json', 'w') as f:
    json.dump(result_data, f)

spark.stop()
```

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
