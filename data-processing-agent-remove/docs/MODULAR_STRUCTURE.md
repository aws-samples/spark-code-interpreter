# Modular Structure - Agents and Tools Separation

## Overview

The agent and tool definitions have been separated from `main.py` into a dedicated `agents.py` module for better reusability, maintainability, and deployment.

## File Structure

```
backend/
├── main.py          # FastAPI application and endpoints
├── agents.py        # Agent and tool definitions (NEW)
└── requirements.txt
```

## agents.py

Contains all strands-agents related code:

### Tools

**1. execute_ray_code(code: str) -> dict**
- Executes Ray code on remote cluster
- Returns success/failure with output/errors
- Used by agent for validation

**2. get_data_sources(session_id: str) -> dict**
- Returns available CSV files and Glue tables
- Used by agent to discover data context

### Agent Factory

**create_ray_code_agent() -> Agent**
- Creates and configures the Ray code generation agent
- Registers tools
- Sets system prompt
- Returns configured agent instance

## main.py

Contains FastAPI application logic:
- API endpoints
- Session management
- Request/response handling
- Imports agent from `agents.py`

## Benefits

### 1. Reusability
```python
# Easy to reuse in other projects
from agents import create_ray_code_agent, execute_ray_code

agent = create_ray_code_agent()
result = execute_ray_code("import ray; print('test')")
```

### 2. Testability
```python
# Test tools independently
from agents import execute_ray_code, get_data_sources

def test_execute_tool():
    result = execute_ray_code("print('hello')")
    assert result['success']
```

### 3. Deployment
- Cleaner separation of concerns
- Easier to package and distribute
- Can deploy agents module separately
- Simpler dependency management

### 4. Maintainability
- Agent logic isolated from API logic
- Easier to update prompts and tools
- Clear module boundaries
- Better code organization

## Usage

### In main.py
```python
from agents import create_ray_code_agent

# Initialize agent
ray_code_agent = create_ray_code_agent()

# Use agent
response = await ray_code_agent.invoke_async(prompt)
```

### Standalone Usage
```python
from agents import create_ray_code_agent, execute_ray_code

# Create agent
agent = create_ray_code_agent()

# Use tools directly
result = execute_ray_code("import ray; ds = ray.data.range(10)")
print(result['output'])
```

## Testing

```bash
python3 test_strands_agent.py
```

Expected output:
```
✓ Agent initialized
✓ Agent has tool_registry
✓ Agent has 2 tool(s) registered
  Tools: execute_ray_code, get_data_sources
  ✓ execute_ray_code tool registered
  ✓ get_data_sources tool registered
✓ Tools are callable functions

✅ Strands-agents integration verified!
   - Tools defined in agents.py for reusability
```

## Migration Notes

### What Changed
- ✅ Moved `@tool` decorated functions to `agents.py`
- ✅ Moved `create_ray_code_agent()` factory to `agents.py`
- ✅ Updated imports in `main.py`
- ✅ Updated test to import from `agents.py`

### What Stayed the Same
- ✅ All API endpoints unchanged
- ✅ All functionality preserved
- ✅ Session management unchanged
- ✅ Frontend unchanged

## Example: Adding New Tools

```python
# In agents.py

@tool
def query_athena(sql: str) -> dict:
    """Execute Athena query and return results"""
    # Implementation
    ...

def create_ray_code_agent():
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            execute_ray_code, 
            get_data_sources,
            query_athena  # ← Add new tool
        ],
        name="RayCodeGenerator"
    )
    return agent
```

## Example: Using in Other Projects

```python
# In another project
from ray_backend.agents import create_ray_code_agent

# Create agent instance
my_agent = create_ray_code_agent()

# Use for code generation
response = await my_agent.invoke_async("Generate Ray code for data processing")
```

## Summary

✅ **Modular structure with agents.py**
✅ **Tools and agent separated from API logic**
✅ **Improved reusability and testability**
✅ **Easier deployment and maintenance**
✅ **All functionality preserved**
✅ **Clean separation of concerns**

The modular structure makes the codebase more maintainable, testable, and reusable while preserving all existing functionality.
