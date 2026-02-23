# Ray Code Interpreter - Strands-Agents Implementation

## ✅ Proper Strands-Agents Framework Integration

The Ray Code Interpreter now uses **strands-agents** framework with proper tool-based agentic patterns.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Strands Agent (Claude 4.5)                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │  System Prompt: Ray Code Generation Expert       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Tool 1: get_data_sources(session_id)            │  │
│  │  - Returns CSV files and Glue tables available   │  │
│  │  - Provides S3 paths and table locations         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Tool 2: execute_ray_code(code)                  │  │
│  │  - Submits code to Ray cluster                   │  │
│  │  - Returns success/failure with output/errors    │  │
│  │  - Agent uses this to validate generated code    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Agent Workflow:                                        │
│  1. Call get_data_sources to see available data        │
│  2. Generate Ray code based on request + data sources  │
│  3. Call execute_ray_code to validate                  │
│  4. If fails, analyze error and regenerate             │
│  5. Repeat until success (max 5 iterations)            │
│  6. Return final working code                          │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Ray Cluster (ECS Fargate)                  │
│              Executes validated code                    │
└─────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Tool Definitions

```python
from strands import Agent, tool
from strands.models import BedrockModel

@tool
def execute_ray_code(code: str) -> dict:
    """
    Execute Ray code on the remote Ray cluster and return results.
    Use this tool to validate generated code before returning it to the user.
    
    Args:
        code: Python code using Ray Data APIs to execute
        
    Returns:
        dict with 'success' (bool), 'output' (str), and 'error' (str if failed)
    """
    # Submits job to Ray cluster, polls for completion, returns results
    ...

@tool
def get_data_sources(session_id: str) -> dict:
    """
    Get available data sources (CSV files and Glue tables) for the current session.
    Use this to understand what data is available before generating code.
    
    Args:
        session_id: The session identifier
        
    Returns:
        dict with 'csv' (dict or None) and 'tables' (list of dicts)
    """
    # Returns session data sources with S3 paths and table locations
    ...
```

### 2. Agent Initialization

```python
def initialize_agent():
    global ray_code_agent
    
    model = BedrockModel(
        model_id='us.anthropic.claude-sonnet-4-5-20250929-v1:0'
    )
    
    system_prompt = """You are an expert Ray data processing code generator.

WORKFLOW:
1. First, use get_data_sources tool to check available CSV files and Glue tables
2. Generate Python code using Ray Data APIs based on the user's request and available data
3. Use execute_ray_code tool to validate your generated code
4. If execution fails, analyze the error and generate corrected code
5. Repeat validation until code executes successfully (max 5 attempts)
6. Return ONLY the final working Python code

CODE REQUIREMENTS:
- Use ray.init(address='auto') to connect to cluster
- Use Ray Data operations: ray.data.range(), ray.data.read_*, map(), filter(), groupby()
- For CSV: use EXACT S3 path from get_data_sources
- For Glue tables: use EXACT database.table names from get_data_sources
- map() functions MUST return dict, never scalar values
- Use take() or take_all() to retrieve results
- Add print statements for output
- NO simulated output in comments
- NO infinite loops

Return ONLY executable Python code, no markdown or explanations."""
    
    ray_code_agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[execute_ray_code, get_data_sources],
        name="RayCodeGenerator"
    )
```

### 3. Agent Invocation

```python
@app.post("/generate")
async def generate_ray_code(request: GenerateRequest):
    # Build prompt with session context
    prompt = f"Session ID: {request.session_id}\n\nUser Request: {request.prompt}"
    
    # Agent automatically uses tools to:
    # 1. Get data sources
    # 2. Generate code
    # 3. Validate with execute_ray_code
    # 4. Iterate until success
    response = await ray_code_agent.invoke_async(prompt)
    
    # Extract final validated code
    code = extract_code(response)
    
    # Execute on cluster and return results
    ...
```

## Key Features

### Agentic Behavior
- **Autonomous Tool Usage**: Agent decides when to call tools
- **Iterative Refinement**: Agent validates and fixes code automatically
- **Context Awareness**: Agent retrieves data sources before generating code
- **Error Recovery**: Agent analyzes failures and regenerates

### Tool-Based Validation
- **execute_ray_code**: Runs code on actual Ray cluster
- **Real Execution**: No simulation, validates against real data
- **Error Feedback**: Returns actual errors for agent to fix

### Data Source Discovery
- **get_data_sources**: Agent queries available CSV/Glue tables
- **Exact Paths**: Agent uses real S3 paths and table names
- **Session Isolation**: Each session has its own data sources

## Verification

Run the test to verify strands-agents integration:

```bash
python3 test_strands_agent.py
```

Expected output:
```
✓ Using strands-agents framework
✓ Using AWS region: us-east-1
✅ Ray code generation agent initialized with tools
Testing strands-agents integration...

✓ Agent initialized
✓ Agent has tool_registry
✓ Agent has 2 tool(s) registered
  Tools: execute_ray_code, get_data_sources
  ✓ execute_ray_code tool registered
  ✓ get_data_sources tool registered

✅ Strands-agents integration verified!
   - Agent uses BedrockModel (Claude Sonnet 4.5)
   - Agent has execute_ray_code tool for validation
   - Agent has get_data_sources tool for context
   - Agent will iteratively validate code before returning
```

## Comparison with Previous Implementation

| Aspect | Before | After |
|--------|--------|-------|
| Framework | Basic Agent | **Strands-Agents with Tools** |
| Validation | Manual iteration loop | **Agent uses execute_ray_code tool** |
| Data Discovery | Manual context building | **Agent uses get_data_sources tool** |
| Error Handling | Hardcoded retry logic | **Agent-driven refinement** |
| Agentic | Prompt-only | **True agentic with tool calling** |

## Benefits

1. **True Agentic Pattern**: Agent autonomously uses tools to solve problems
2. **Self-Validation**: Agent validates its own code before returning
3. **Context Discovery**: Agent discovers data sources dynamically
4. **Error Recovery**: Agent analyzes and fixes errors automatically
5. **No Simulation**: All validation uses real Ray cluster execution
6. **Extensible**: Easy to add more tools (e.g., query Athena, check schemas)

## Future Tool Extensions

Potential additional tools:
- `query_athena(sql)` - Preview data before generating code
- `get_table_schema(database, table)` - Get column details
- `validate_s3_path(path)` - Check if S3 path exists
- `estimate_data_size(source)` - Get row counts for optimization

## Summary

✅ **Proper strands-agents implementation**
✅ **Tool-based agentic pattern**
✅ **Real execution validation (no simulation)**
✅ **Autonomous error recovery**
✅ **Context-aware code generation**
✅ **Production-ready**

The implementation follows strands-agents best practices with proper tool definitions, agent initialization, and agentic workflows.
