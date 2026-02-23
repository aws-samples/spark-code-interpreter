# Multi-Agent System Architecture

## Overview

The Ray Code Interpreter now uses a **multi-agent system** with a **supervisor agent** orchestrating three specialized agents.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                          │
│                    (Orchestrator)                           │
│                                                             │
│  Coordinates workflow and delegates to specialized agents  │
│                                                             │
│  Tools (Agent Wrappers):                                   │
│  • discover_data(session_id)                               │
│  • generate_code(requirements)                             │
│  • validate_code(code)                                     │
└──────────────┬──────────────┬──────────────┬───────────────┘
               │              │              │
               ▼              ▼              ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Agent 1    │  │   Agent 2    │  │   Agent 3    │
    │              │  │              │  │              │
    │    Data      │  │    Code      │  │    Code      │
    │  Discovery   │  │  Generator   │  │  Validator   │
    │              │  │              │  │              │
    │ Tool:        │  │ No tools     │  │ Tool:        │
    │ • get_data_  │  │ (pure LLM)   │  │ • execute_   │
    │   sources    │  │              │  │   ray_code   │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## Agents

### 1. SupervisorAgent (Orchestrator)

**Role:** Coordinates the multi-agent workflow

**Responsibilities:**
- Receives user requests
- Delegates tasks to specialized agents
- Manages workflow: discover → generate → validate → iterate
- Returns final validated code

**Tools (Agent Wrappers):**
- `discover_data(session_id)` → Invokes DataDiscoveryAgent
- `generate_code(requirements)` → Invokes CodeGeneratorAgent
- `validate_code(code)` → Invokes CodeValidatorAgent

**Workflow:**
1. Call `discover_data` to get available CSV/Glue tables
2. Call `generate_code` with user request + data sources
3. Call `validate_code` to test code on Ray cluster
4. If validation fails, call `generate_code` again with error feedback
5. Repeat steps 3-4 until success (max 5 iterations)
6. Return final working code

### 2. DataDiscoveryAgent (Specialist)

**Role:** Discovers and provides data source information

**Responsibilities:**
- Retrieves available CSV files from session
- Retrieves selected Glue tables from session
- Provides S3 paths and table locations

**Tool:**
- `get_data_sources(session_id)` - Queries session for data sources

**Output:**
- CSV file information (filename, S3 path, preview)
- Glue table information (database, table, location)

### 3. CodeGeneratorAgent (Specialist)

**Role:** Generates Ray data processing code

**Responsibilities:**
- Generates Python code using Ray Data APIs
- Uses exact S3 paths and table names provided
- Follows Ray best practices
- Returns clean, executable code

**Tools:** None (pure LLM generation)

**Specialization:**
- Ray Data API expertise
- Proper map() function patterns (returns dict)
- Error-free code generation
- No simulated output

### 4. CodeValidatorAgent (Specialist)

**Role:** Validates code by executing on Ray cluster

**Responsibilities:**
- Executes code on remote Ray cluster
- Captures execution results
- Analyzes errors
- Provides fix recommendations

**Tool:**
- `execute_ray_code(code)` - Submits job to Ray cluster, polls for results

**Output:**
- Success/failure status
- Execution output (filtered logs)
- Error messages with traceback
- Fix suggestions

## Workflow Example

### User Request
"Create a dataset with 1000 rows and calculate squared values"

### Supervisor Orchestration

**Step 1: Discover Data**
```
SupervisorAgent → discover_data(session_id)
                → DataDiscoveryAgent.invoke()
                → get_data_sources tool
                → Returns: {"csv": null, "tables": []}
```

**Step 2: Generate Code**
```
SupervisorAgent → generate_code("User wants 1000 rows with squared values. No data sources available.")
                → CodeGeneratorAgent.invoke()
                → Returns: Python code using ray.data.range(1000)
```

**Step 3: Validate Code**
```
SupervisorAgent → validate_code(generated_code)
                → CodeValidatorAgent.invoke()
                → execute_ray_code tool
                → Submits to Ray cluster
                → Returns: {"success": true, "output": "..."}
```

**Step 4: Return Result**
```
SupervisorAgent → Returns validated code to user
```

### If Validation Fails

**Step 3b: Validation Error**
```
SupervisorAgent → validate_code(generated_code)
                → Returns: {"success": false, "error": "map() must return dict"}
```

**Step 4b: Regenerate with Feedback**
```
SupervisorAgent → generate_code("Previous code failed: map() must return dict. Fix the code.")
                → CodeGeneratorAgent.invoke()
                → Returns: Corrected code
```

**Step 5b: Validate Again**
```
SupervisorAgent → validate_code(corrected_code)
                → Returns: {"success": true, "output": "..."}
```

## Benefits of Multi-Agent System

### 1. Separation of Concerns
- Each agent has a single, well-defined responsibility
- Data discovery separate from code generation
- Validation separate from generation

### 2. Specialization
- DataDiscoveryAgent: Expert in session data
- CodeGeneratorAgent: Expert in Ray code
- CodeValidatorAgent: Expert in debugging

### 3. Modularity
- Easy to replace or upgrade individual agents
- Can add new specialized agents (e.g., SchemaInspectorAgent)
- Independent testing of each agent

### 4. Scalability
- Supervisor can manage more agents as needed
- Agents can be distributed across services
- Parallel execution possible

### 5. Maintainability
- Clear agent boundaries
- Easier to debug (know which agent failed)
- Simpler to update prompts per agent

## Code Structure

### agents.py
```python
# Agent 1: Data Discovery
def create_data_discovery_agent() -> Agent:
    # Tool: get_data_sources
    ...

# Agent 2: Code Generator
def create_code_generator_agent() -> Agent:
    # No tools, pure generation
    ...

# Agent 3: Code Validator
def create_code_validator_agent() -> Agent:
    # Tool: execute_ray_code
    ...

# Supervisor: Orchestrator
def create_supervisor_agent() -> Agent:
    # Tools: discover_data, generate_code, validate_code
    # (wrappers around sub-agents)
    ...

# Factory (backward compatible)
def create_ray_code_agent() -> Agent:
    return create_supervisor_agent()
```

## Verification

```bash
python3 -c "
from agents import create_supervisor_agent

supervisor = create_supervisor_agent()
print(f'Agent: {supervisor.name}')
print(f'Tools: {supervisor.tool_names}')
"
```

**Expected Output:**
```
Agent: SupervisorAgent
Tools: ['discover_data', 'generate_code', 'validate_code']
```

## Future Extensions

### Potential Additional Agents

1. **SchemaInspectorAgent**
   - Inspects Glue table schemas
   - Provides column names and types
   - Helps with query generation

2. **DataPreviewAgent**
   - Queries Athena for data samples
   - Shows first N rows
   - Helps understand data structure

3. **OptimizationAgent**
   - Analyzes generated code
   - Suggests performance improvements
   - Recommends partitioning strategies

4. **DocumentationAgent**
   - Generates code documentation
   - Explains what the code does
   - Provides usage examples

## Summary

✅ **Multi-agent system with supervisor**
✅ **4 specialized agents (1 supervisor + 3 workers)**
✅ **Clear separation of concerns**
✅ **Supervisor orchestrates workflow**
✅ **Agents communicate through supervisor**
✅ **Modular and extensible architecture**
✅ **All functionality preserved**

The multi-agent system provides better organization, maintainability, and extensibility while preserving all existing functionality.
