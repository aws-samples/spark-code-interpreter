# Multi-Agent System - Quick Reference

## System Overview

**4 Agents:** 1 Supervisor + 3 Specialists

```
SupervisorAgent
├── DataDiscoveryAgent (get_data_sources)
├── CodeGeneratorAgent (pure LLM)
└── CodeValidatorAgent (execute_ray_code)
```

## The Agents

| Agent | Role | Tools | Purpose |
|-------|------|-------|---------|
| **SupervisorAgent** | Orchestrator | discover_data, generate_code, validate_code | Coordinates workflow |
| **DataDiscoveryAgent** | Data Discovery | get_data_sources | Finds CSV/Glue tables |
| **CodeGeneratorAgent** | Code Generation | None | Generates Ray code |
| **CodeValidatorAgent** | Validation | execute_ray_code | Tests on Ray cluster |

## Supervisor Workflow

1. **Discover** → Call `discover_data(session_id)`
2. **Generate** → Call `generate_code(requirements + data)`
3. **Validate** → Call `validate_code(code)`
4. **Iterate** → If fails, regenerate with error feedback
5. **Return** → Final validated code

## Testing

```bash
# Test multi-agent system
python3 test_strands_agent.py

# Expected output
✅ MULTI-AGENT SYSTEM VERIFIED
Total Agents: 4 (1 supervisor + 3 specialists)
```

## Usage (No Changes Needed)

```python
# In main.py (unchanged)
from agents import create_ray_code_agent

agent = create_ray_code_agent()  # Returns SupervisorAgent
response = await agent.invoke_async(prompt)
```

## Adding New Agents

```python
# 1. Create specialist agent
def create_my_new_agent():
    @tool
    def my_tool(param: str) -> dict:
        return {"result": "value"}
    
    return Agent(
        model=model,
        system_prompt="...",
        tools=[my_tool],
        name="MyNewAgent"
    )

# 2. Add wrapper to supervisor
def create_supervisor_agent():
    my_agent = create_my_new_agent()
    
    @tool
    def use_my_agent(param: str) -> str:
        result = my_agent.invoke(param)
        return str(result.message)
    
    supervisor = Agent(
        tools=[discover_data, generate_code, validate_code, use_my_agent],
        ...
    )
```

## Key Files

- `agents.py` - All 4 agents + tools
- `main.py` - FastAPI app (unchanged)
- `test_strands_agent.py` - Multi-agent verification

## Benefits

✅ Separation of concerns
✅ Specialized agents
✅ Modular architecture
✅ Easy to extend
✅ Backward compatible
