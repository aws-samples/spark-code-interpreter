# Dependency Fix - Removed Agent Import from Local Backend

## Issue
The code generation agent (`agents.py`) was importing `prompt_sessions` from `main.py`:
```python
from main import prompt_sessions
```

This created an invalid dependency where:
- Agent code (deployed to AWS AgentCore container) tried to import from local FastAPI backend
- This cannot work because the agent runs in a separate AWS environment
- The import would fail at runtime in the deployed agent

## Architecture Violation

**Correct Architecture:**
```
Frontend → main.py (FastAPI) → Supervisor Agent Runtime (AWS)
                                      ↓
                                Code Gen Agent Runtime (AWS)
                                      ↓
                                MCP Gateway → Lambda → Ray Cluster
```

**What Was Wrong:**
```
Code Gen Agent (AWS) → import from main.py (Local) ❌
```

Agents deployed to AgentCore run in isolated AWS containers and cannot import from local backend files.

## Solution

### 1. Removed Invalid Import
**File:** `backend/agents.py`

**Before:**
```python
@tool
def get_data_sources(session_id: str) -> dict:
    """Get available CSV files and Glue tables for the session"""
    try:
        from main import prompt_sessions  # ❌ Invalid import
        if session_id not in prompt_sessions:
            return {"csv": None, "tables": []}
        prompt_data = prompt_sessions[session_id]
        return {"csv": prompt_data['csv'], "tables": prompt_data['tables']}
    except ImportError:
        return {"csv": None, "tables": []}
```

**After:**
```python
@tool
def get_data_sources(session_id: str) -> dict:
    """Get available CSV files and Glue tables for the session
    
    Note: This tool cannot access local backend data when running in AgentCore.
    Data sources should be passed in the prompt instead.
    """
    # Agent runs in AWS container, cannot import from local main.py
    return {"csv": None, "tables": [], "note": "Data sources should be passed in prompt"}
```

### 2. Pass Data in Prompt Instead
**File:** `backend/main.py`

**Before:**
```python
# Just pass session ID, expect agent to fetch data
prompt_with_context = f"Session ID: {session_id}\n\n{request.prompt}"
```

**After:**
```python
# Embed data sources directly in prompt
prompt_parts = [f"Session ID: {session_id}"]

if csv_data:
    prompt_parts.append(f"\nAvailable CSV file:")
    prompt_parts.append(f"  - Filename: {csv_data['filename']}")
    prompt_parts.append(f"  - S3 Path: {csv_data['s3_path']}")

if tables_data:
    prompt_parts.append(f"\nAvailable Glue tables:")
    for table in tables_data:
        prompt_parts.append(f"  - {table['database']}.{table['table']} at {table['location']}")

prompt_parts.append(f"\n{request.prompt}")
prompt_with_context = "\n".join(prompt_parts)
```

### 3. Updated Agent System Prompt
**File:** `backend/agents.py`

**Before:**
```
WORKFLOW:
1. Extract session_id from user prompt if provided
2. Call get_data_sources(session_id) to discover available data
3. Generate Ray code...
```

**After:**
```
WORKFLOW:
1. Look for data sources in the prompt (CSV files and Glue tables)
2. Generate Ray code based on the user request and available data sources
3. Return ONLY the Python code...

DATA SOURCES IN PROMPT:
The prompt will contain available data sources in this format:
- CSV: "Filename: x.csv" and "S3 Path: s3://bucket/path"
- Glue: "database.table at s3://location"
```

## Example Flow

### Before Fix (Broken):
```
1. User uploads CSV → stored in main.py's prompt_sessions
2. User generates code
3. Backend calls Supervisor Agent
4. Supervisor calls Code Gen Agent
5. Code Gen Agent tries: from main import prompt_sessions ❌
6. Import fails (main.py not in AWS container)
7. Agent generates code with placeholder path
```

### After Fix (Working):
```
1. User uploads CSV → stored in main.py's prompt_sessions
2. User generates code
3. Backend builds prompt with CSV data:
   "Session ID: abc123
    
    Available CSV file:
      - Filename: sales.csv
      - S3 Path: s3://strands-ray-data/sessions/abc123/csv/sales.csv
    
    Analyze the sales data"
4. Backend calls Supervisor Agent with enriched prompt
5. Supervisor calls Code Gen Agent with same prompt
6. Code Gen Agent extracts S3 path from prompt ✅
7. Agent generates code with correct path ✅
```

## Dependencies After Fix

### main.py (FastAPI Backend)
**Imports:**
- Standard libraries (json, time, typing)
- FastAPI, boto3, requests
- Local config.py
- ❌ NO imports from agents.py or supervisor_agents.py

**Calls:**
- Supervisor Agent Runtime via boto3 (ARN-based invocation)
- No direct Python imports of agent code

### agents.py (Code Generation Agent)
**Imports:**
- strands framework
- BedrockModel
- BedrockAgentCoreApp
- ❌ NO imports from main.py

**Data Access:**
- Reads data sources from prompt text
- No direct access to backend variables

### supervisor_agents.py (Supervisor Agent)
**Imports:**
- strands framework
- boto3
- ❌ NO imports from main.py or agents.py

**Calls:**
- Code Gen Agent Runtime via boto3 (ARN-based invocation)
- MCP Gateway via HTTP requests

## Verification

✅ **No circular dependencies**
✅ **No imports between main.py and agent files**
✅ **Agents are self-contained and deployable to AWS**
✅ **Data passed via prompts, not Python imports**
✅ **Proper separation of concerns**

## Architecture Compliance

✅ **Frontend** → HTTP → **Backend (main.py)**
✅ **Backend** → boto3 → **Supervisor Agent Runtime (AWS)**
✅ **Supervisor** → boto3 → **Code Gen Agent Runtime (AWS)**
✅ **Supervisor** → HTTP → **MCP Gateway (AWS)**
✅ **MCP Gateway** → invoke → **Lambda (AWS)**
✅ **Lambda** → HTTP → **Ray Cluster (AWS)**

All communication happens via:
- HTTP/HTTPS requests
- boto3 SDK calls (AgentCore Runtime invocations)
- No Python imports across deployment boundaries

## Summary

Removed the invalid import of `prompt_sessions` from `main.py` in the code generation agent. Data sources are now passed directly in the prompt text, maintaining proper separation between the local FastAPI backend and the deployed AWS agents.

This ensures:
- Agents can be deployed independently to AWS
- No runtime import errors
- Clean architecture with proper boundaries
- Data flows through prompts and API calls, not Python imports
