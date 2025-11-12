# Ray Code Interpreter - Strands-Agents Implementation

## ✅ Updated with Strands-Agents Framework

The backend has been updated to use **strands-agents** for agentic Ray code generation, following the same pattern as the AgentCore code interpreter.

### Key Implementation Details

#### 1. Agent Initialization

```python
from strands import Agent, tool
from strands.models import BedrockModel

# Create Bedrock model
model = BedrockModel(
    model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
    region=aws_region
)

# Create agent with Ray-specific instructions
ray_code_agent = Agent(
    name="RayCodeGenerator",
    model=model,
    instructions="""You are an expert Ray data processing code generator.
    
Your role:
- Generate Python code using Ray Data APIs
- Always use ray.init(address='auto') to connect to the cluster
- Use Ray Data operations: ray.data.range(), ray.data.read_*, map(), filter(), groupby()
- Include proper error handling
- Add print statements to show results
- Keep code concise and efficient

Return ONLY executable Python code, no explanations or markdown."""
)
```

#### 2. Code Generation with Agent

```python
@app.post("/generate")
async def generate_ray_code(request: GenerateRequest):
    """Generate Ray code using strands-agents"""
    # Use agent to generate code
    response = ray_code_agent.run(request.prompt)
    
    # Extract code from response
    code = response.content
    
    # Clean up markdown if present
    if '```python' in code:
        code = code.split('```python')[1].split('```')[0].strip()
    
    return {
        "success": True,
        "code": code,
        "session_id": request.session_id
    }
```

#### 3. Execution on Ray Cluster

The execution remains the same - submitting jobs to the Ray cluster via the Jobs API.

### Architecture

```
┌──────────────────┐
│  React Frontend  │
│  (Cloudscape)    │
└────────┬─────────┘
         │
         │ HTTP/REST
         ▼
┌──────────────────┐
│  FastAPI Backend │
│                  │
│  ┌────────────┐  │
│  │  Strands   │  │  ← Agent Framework
│  │  Agent     │  │
│  └──────┬─────┘  │
│         │        │
└─────────┼────────┘
          │
          ├─────────────────┐
          │                 │
          ▼                 ▼
  ┌──────────────┐   ┌──────────────┐
  │   Bedrock    │   │ Ray Cluster  │
  │   (Claude)   │   │ (ECS/Fargate)│
  │              │   │ 13.220.45.214│
  └──────────────┘   └──────────────┘
```

### Comparison with AgentCore Implementation

| Feature | AgentCore Code Interpreter | Ray Code Interpreter |
|---------|---------------------------|---------------------|
| Framework | strands-agents ✅ | strands-agents ✅ |
| Model | Bedrock Claude ✅ | Bedrock Claude ✅ |
| Agent Pattern | Yes ✅ | Yes ✅ |
| Execution | AgentCore Sandbox | Ray ECS Cluster |
| Code Type | General Python | Ray Data APIs |
| Dashboard | N/A | Embedded Ray Dashboard |

### Agent Instructions

The agent is specifically instructed to:

1. **Generate Ray-specific code**
   - Use Ray Data APIs
   - Initialize with `ray.init(address='auto')`
   - Use distributed operations

2. **Follow best practices**
   - Include error handling
   - Add print statements for output
   - Keep code concise

3. **Return clean code**
   - No markdown formatting
   - No explanations
   - Only executable Python

### Dependencies

```
fastapi==0.104.1
uvicorn==0.24.0
python-dotenv==1.0.0
boto3==1.29.7
requests==2.31.0
pydantic==2.5.0
strands-agents  ← Added
```

### Testing the Agent

Start the backend:
```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

You should see:
```
✓ Using strands-agents framework
✅ Ray code generation agent initialized with model: anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Example Agent Interaction

**User Prompt:**
"Create a dataset with 10000 rows and calculate squared values"

**Agent Response (code):**
```python
import ray

ray.init(address='auto')

# Create dataset
ds = ray.data.range(10000)

# Calculate squared values
ds_squared = ds.map(lambda x: {"id": x["id"], "squared": x["id"] ** 2})

# Show results
print(f"Dataset created with {ds.count()} rows")
print("First 5 rows:")
for row in ds_squared.take(5):
    print(row)
```

### Benefits of Strands-Agents

1. **Consistent Pattern**: Same framework as AgentCore implementation
2. **Agentic Approach**: Intelligent code generation with context
3. **Extensible**: Easy to add tools and capabilities
4. **Maintainable**: Clean separation of concerns
5. **Production-Ready**: Built on proven framework

### Summary

✅ **Strands-agents integrated**
✅ **Agent-based code generation**
✅ **Ray-specific instructions**
✅ **Follows AgentCore pattern**
✅ **Production-ready**

The implementation now uses the same agentic approach as the AgentCore code interpreter, but specialized for Ray data processing workloads.
