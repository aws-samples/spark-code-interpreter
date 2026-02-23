# Software Requirements Specification (SRS)
## VSCode Ray Code Interpreter Plugin

**Version**: 2.0  
**Date**: October 6, 2025  
**Based on**: Ray Code Interpreter Web Application

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for converting the Ray Code Interpreter web application into a Visual Studio Code extension. The plugin will enable users to execute Ray code on any Ray cluster, generate code using AI, and manage Ray jobs directly from VSCode.

### 1.2 Scope
The VSCode plugin will:
- Replace the React frontend with VSCode UI components
- Retain the existing FastAPI backend and strands-agents implementation
- Add VSCode-specific features (file execution, right-click context menus)
- Provide integrated Ray Dashboard viewing
- Enable natural language code generation via chat interface
- **Support any Ray cluster via configurable endpoints (no cluster deployment)**
- **Pass configuration settings to backend for dynamic agent initialization**
- **Support multiple Bedrock models and regions via configuration**

### 1.3 Out of Scope
- Ray cluster deployment and management
- AWS ECS infrastructure setup
- Cluster monitoring and scaling
- Package installation on clusters

### 1.4 Definitions
- **Ray Cluster**: Any Ray cluster (local, cloud, or managed) accessible via HTTP
- **Backend**: FastAPI server with strands-agents (modified for dynamic configuration)
- **Agent**: AI agent using AWS Bedrock for code generation
- **Session**: Isolated execution context for prompts
- **Configuration**: User-provided settings for cluster and Bedrock endpoints

---

## 2. System Architecture

### 2.1 Components

```
┌─────────────────────────────────────────────────────────────┐
│                    VSCode Extension                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Panel   │  │ Dashboard    │  │ Jobs Panel   │      │
│  │ (Webview)    │  │ (Webview)    │  │ (TreeView)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Extension Host (TypeScript)                   │   │
│  │  - Commands (Execute, Generate, Stop)                 │   │
│  │  - Context Menus (File, Editor)                       │   │
│  │  - Settings Management & Validation                   │   │
│  │  - Backend Communication (HTTP + Config Injection)    │   │
│  │  - Multi-Cluster Support                              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP (with config)
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Modified)                      │
├─────────────────────────────────────────────────────────────┤
│  - /generate (accepts config: cluster, bedrock)              │
│  - /execute (accepts config: cluster)                        │
│  - /ray/jobs?cluster_url= (dynamic cluster)                 │
│  - /ray/jobs/{id}/stop?cluster_url=                         │
│  - /upload-csv, /sessions/{id}/select-tables                │
│  - Dynamic agent initialization per request                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Strands-Agents (Modified)                            │
│  - create_ray_code_agent(config) - dynamic initialization   │
│  - BedrockModel(model_id, region, profile) - from config    │
│  - validate_code() - uses cluster from config               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Ray Cluster (User-Provided, Any Type)                │
│  - Local, AWS ECS, Kubernetes, or any Ray deployment        │
│  - Dashboard API (port 8265 by default)                     │
│  - Job submission endpoint                                   │
│  - Ray 2.x or higher                                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

**VSCode Extension**:
- Language: TypeScript
- Framework: VSCode Extension API
- UI: Webview API (for chat and dashboard)
- HTTP Client: axios or node-fetch
- Configuration: VSCode Settings API

**Backend** (Modified):
- FastAPI (Python) - modified to accept config per request
- strands-agents framework - modified for dynamic initialization
- AWS Bedrock - configured per request

**Ray Cluster** (External - Not Provided):
- Any Ray cluster with HTTP API access
- Ray 2.x or higher recommended

---

## 3. Functional Requirements

### 3.1 Configuration Settings

**REQ-CFG-001**: Plugin Settings  
The extension shall provide the following configurable settings:

| Setting | Type | Default | Required | Description |
|---------|------|---------|----------|-------------|
| `rayInterpreter.backendUrl` | string | `http://localhost:8000` | Yes | FastAPI backend URL |
| `rayInterpreter.rayClusterUrl` | string | `` | Yes | Ray cluster dashboard URL (e.g., http://cluster-ip:8265) |
| `rayInterpreter.bedrockModelId` | string | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Yes | AWS Bedrock model ID |
| `rayInterpreter.bedrockRegion` | string | `us-east-1` | Yes | AWS Bedrock region |
| `rayInterpreter.awsProfile` | string | `default` | No | AWS profile name |
| `rayInterpreter.autoExecute` | boolean | `true` | No | Auto-execute after generation |
| `rayInterpreter.sessionId` | string | `vscode-session` | No | Session identifier |

**REQ-CFG-002**: Settings Validation  
The extension shall validate settings on activation:
- `backendUrl` must be a valid HTTP/HTTPS URL
- `rayClusterUrl` must be a valid HTTP/HTTPS URL
- `bedrockModelId` must not be empty
- `bedrockRegion` must be a valid AWS region
- Display clear error messages for invalid configurations
- Prevent operations if required settings are missing

**REQ-CFG-003**: Settings UI  
Settings shall be accessible via:
- VSCode Settings UI under "Ray Interpreter" category
- Settings icon in chat panel
- Command: "Ray: Open Settings"

**REQ-CFG-004**: Configuration Passthrough  
Extension shall pass configuration to backend on each request:
```typescript
{
  prompt: "...",
  session_id: "...",
  config: {
    ray_cluster_url: "http://cluster:8265",
    bedrock_model_id: "us.anthropic.claude-sonnet-4-5...",
    bedrock_region: "us-east-1",
    aws_profile: "default"
  }
}
```

**REQ-CFG-005**: Multi-Cluster Support  
Extension shall support multiple cluster profiles:
```json
{
  "rayInterpreter.clusters": [
    {
      "name": "Production",
      "url": "http://prod-cluster:8265",
      "default": true
    },
    {
      "name": "Development",  
      "url": "http://dev-cluster:8265"
    },
    {
      "name": "Local",
      "url": "http://localhost:8265"
    }
  ]
}
```

**REQ-CFG-006**: Cluster Selection  
Extension shall provide cluster selector in:
- Status bar (click to switch active cluster)
- Chat panel header (dropdown)
- Command palette: "Ray: Switch Cluster"

---

### 3.2 Code Execution

**REQ-EXEC-001**: Execute Selected Code  
When user selects code in a Python file and invokes "Ray: Execute Selection":
1. Extract selected text
2. Get active cluster configuration
3. Send to backend `/execute` endpoint with config
4. Display execution results in Output panel
5. Show job ID and status

**REQ-EXEC-002**: Execute Entire File  
When user right-clicks a Python file and selects "Ray: Execute File":
1. Read entire file content
2. Get active cluster configuration
3. Send to backend `/execute` endpoint with config
4. Display results in Output panel
5. Update Jobs panel with new job

**REQ-EXEC-003**: Execute from File Explorer  
Right-click context menu in File Explorer shall include "Ray: Execute File" option for `.py` files.

**REQ-EXEC-004**: Execution Feedback  
During execution:
- Show progress notification with cluster name
- Display "Executing on [cluster]..." status in status bar
- Stream logs to Output panel if available
- Show cancel button for long-running jobs

**REQ-EXEC-005**: Execution Results  
After execution:
- Display success/failure notification
- Show execution output in dedicated Output channel
- Highlight errors in red
- Provide "View in Dashboard" link
- Show execution time and cluster used

---

### 3.3 Code Generation (Chat Interface)

**REQ-GEN-001**: Chat Panel  
The extension shall provide a chat panel (Webview) for natural language code generation:
- Located in Activity Bar (sidebar)
- Persistent across sessions
- Scrollable message history
- Shows active cluster in header

**REQ-GEN-002**: Message Input  
Chat panel shall include:
- Text input field for prompts
- Send button
- Clear history button
- Data source selection (CSV/Tables)
- Cluster selector dropdown
- Settings icon

**REQ-GEN-003**: Code Generation Flow  
When user submits a prompt:
1. Get active cluster and Bedrock configuration
2. Send to backend `/generate` endpoint with config
3. Display "Generating with [model]..." indicator
4. Show agent's validation attempts (optional)
5. Display generated code in chat
6. Provide "Insert to Editor" button
7. Provide "Execute on [cluster]" button

**REQ-GEN-004**: Agent Integration  
The backend agent workflow shall use provided configuration:
1. Backend receives config (cluster URL, Bedrock model)
2. Backend creates agent with BedrockModel(model_id, region, profile)
3. Agent calls `get_data_sources(session_id)`
4. Agent generates Ray code
5. Agent calls `validate_code(code)` on configured cluster (up to 3 times)
6. Agent returns validated code
7. Backend auto-executes on configured cluster if enabled

**REQ-GEN-005**: Code Display  
Generated code shall be displayed with:
- Syntax highlighting (Python)
- Copy button
- Insert to editor button
- Execute button with cluster name
- Edit and re-execute option
- Validation status indicator

**REQ-GEN-006**: Session Isolation  
Each prompt shall create an isolated session:
- Unique session ID per prompt: `{base_session}_{timestamp}`
- No context overlap between prompts
- Data sources snapshot per prompt
- Enable re-execution from history

**REQ-GEN-007**: Conversation History  
Chat panel shall display:
- User prompts
- Generated code
- Execution results
- Timestamps
- Cluster and model used
- Data sources used

---

### 3.4 Ray Dashboard Integration

**REQ-DASH-001**: Dashboard Panel  
The extension shall provide a Ray Dashboard panel:
- Located in bottom panel (alongside Terminal, Debug Console)
- Implemented as Webview
- Loads dashboard URL from active cluster configuration
- Updates when cluster is switched

**REQ-DASH-002**: Dashboard Tab  
Dashboard shall appear as a tab named "Ray Dashboard ([cluster])" in the bottom panel.

**REQ-DASH-003**: Dashboard Features  
The dashboard panel shall:
- Display full Ray dashboard UI from configured cluster
- Support all dashboard interactions
- Auto-refresh on job submission
- Provide "Open in Browser" button
- Show connection status

**REQ-DASH-004**: Dashboard Link  
All execution results shall include a "View in Dashboard" link that:
- Opens Dashboard panel if closed
- Focuses Dashboard tab
- Optionally navigates to specific job

**REQ-DASH-005**: Multi-Cluster Dashboard  
When user switches clusters:
- Dashboard URL updates automatically
- Panel reloads with new cluster's dashboard
- Tab name updates to show current cluster

---

### 3.5 Job Management

**REQ-JOB-001**: Jobs Panel  
The extension shall provide a Jobs TreeView panel showing:
- Jobs grouped by cluster
- Running jobs
- Completed jobs (last 10)
- Failed jobs (last 10)
- Job ID, status, start time, cluster name

**REQ-JOB-002**: Job List Refresh  
Jobs panel shall:
- Auto-refresh every 5 seconds when jobs are running
- Query all configured clusters
- Provide manual refresh button
- Show loading indicator during refresh
- Handle cluster connection failures gracefully

**REQ-JOB-003**: Job Actions  
Right-click context menu on job shall provide:
- "Stop Job" (for running jobs)
- "View Logs"
- "View in Dashboard"
- "Copy Job ID"
- "Re-execute Code"

**REQ-JOB-004**: Stop Job  
When user stops a job:
1. Identify job's cluster from metadata
2. Send request to `/ray/jobs/{id}/stop?cluster_url={url}`
3. Show confirmation dialog
4. Update job status in panel
5. Display notification on success/failure

**REQ-JOB-005**: Job Status Icons  
Jobs shall display status icons:
- 🟢 Running
- ✅ Succeeded
- ❌ Failed
- ⏸️ Stopped
- ⏳ Pending
- 🔴 Cluster Unreachable

**REQ-JOB-006**: Job Details  
Clicking a job shall show details in Output panel:
- Job ID
- Cluster name and URL
- Status
- Start time
- Duration
- Code executed
- Logs (if available)

---

### 3.6 Data Source Management

**REQ-DATA-001**: CSV Upload  
Chat panel shall provide "Upload CSV" button:
1. Open file picker
2. Upload to backend `/upload-csv`
3. Display uploaded file name
4. Associate with current session

**REQ-DATA-002**: Table Selection  
Chat panel shall provide "Select Tables" button:
1. Fetch databases from backend `/glue/databases`
2. Show table picker dialog
3. Send selection to `/sessions/{id}/select-tables`
4. Display selected tables

**REQ-DATA-003**: Data Source Display  
Chat panel shall show current data sources:
- CSV file name (if uploaded)
- Selected tables list
- Clear buttons for each

**REQ-DATA-004**: Session Data Isolation  
Data sources shall be isolated per prompt:
- Snapshot on prompt submission
- Clear after prompt execution
- Preserve for re-execution from history

---

### 3.7 Commands

**REQ-CMD-001**: Command Palette  
The extension shall register the following commands:

| Command | ID | Description |
|---------|-----|-------------|
| Ray: Execute Selection | `rayInterpreter.executeSelection` | Execute selected code on active cluster |
| Ray: Execute File | `rayInterpreter.executeFile` | Execute current file on active cluster |
| Ray: Generate Code | `rayInterpreter.generateCode` | Open chat panel |
| Ray: Open Dashboard | `rayInterpreter.openDashboard` | Open dashboard for active cluster |
| Ray: Switch Cluster | `rayInterpreter.switchCluster` | Switch active Ray cluster |
| Ray: Refresh Jobs | `rayInterpreter.refreshJobs` | Refresh jobs from all clusters |
| Ray: Stop Job | `rayInterpreter.stopJob` | Stop selected job |
| Ray: Clear Chat | `rayInterpreter.clearChat` | Clear chat history |
| Ray: Upload CSV | `rayInterpreter.uploadCsv` | Upload CSV file |
| Ray: Select Tables | `rayInterpreter.selectTables` | Select Glue tables |
| Ray: Open Settings | `rayInterpreter.openSettings` | Open extension settings |
| Ray: Test Connection | `rayInterpreter.testConnection` | Test cluster and backend connectivity |

**REQ-CMD-002**: Keybindings  
Default keybindings:
- `Ctrl+Shift+R` (Cmd+Shift+R on Mac): Execute Selection
- `Ctrl+Shift+G` (Cmd+Shift+G on Mac): Generate Code
- `Ctrl+Shift+D` (Cmd+Shift+D on Mac): Open Dashboard

---

## 4. Backend Requirements (Modified)

### 4.1 API Endpoints (Modified)

The existing FastAPI backend shall be modified to accept configuration parameters:

**Code Generation**:
- `POST /generate` - Generate code with agent
  - **Input**: 
    ```json
    {
      "prompt": "Create a dataset...",
      "session_id": "vscode-session-123",
      "config": {
        "ray_cluster_url": "http://cluster:8265",
        "bedrock_model_id": "us.anthropic.claude-sonnet-4-5...",
        "bedrock_region": "us-east-1",
        "aws_profile": "default"
      }
    }
    ```
  - **Output**: `{code, execution_result, job_id}`
  - **Behavior**: Agent initialized with provided config

**Code Execution**:
- `POST /execute` - Execute code on cluster
  - **Input**: 
    ```json
    {
      "code": "import ray...",
      "session_id": "vscode-session-123",
      "config": {
        "ray_cluster_url": "http://cluster:8265"
      }
    }
    ```
  - **Output**: `{result, job_id, success}`
  - **Behavior**: Uses provided Ray cluster endpoint

**Job Management** (Modified):
- `GET /ray/jobs?cluster_url={url}` - List all jobs from specified cluster
- `GET /ray/jobs/{id}?cluster_url={url}` - Get job details
- `POST /ray/jobs/{id}/stop?cluster_url={url}` - Stop job
- `GET /ray/jobs/{id}/logs?cluster_url={url}` - Get job logs

**Data Sources** (No changes):
- `POST /upload-csv` - Upload CSV file
- `GET /glue/databases` - List Glue databases
- `GET /glue/databases/{db}/tables` - List tables
- `POST /sessions/{id}/select-tables` - Select tables

**Session Management** (No changes):
- `GET /history/{session_id}` - Get session history
- `POST /sessions/{id}/reset` - Reset session

**Health Check** (New):
- `GET /health` - Backend health status
- `POST /test-connection` - Test cluster and Bedrock connectivity
  - **Input**: `{config: {...}}`
  - **Output**: `{cluster_reachable, bedrock_accessible, errors}`

### 4.2 Request Models (New)

```python
from pydantic import BaseModel, HttpUrl
from typing import Optional

class ClusterConfig(BaseModel):
    ray_cluster_url: HttpUrl
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_region: str = "us-east-1"
    aws_profile: Optional[str] = "default"

class GenerateRequest(BaseModel):
    prompt: str
    session_id: str
    config: ClusterConfig

class ExecuteRequest(BaseModel):
    code: str
    session_id: str
    config: ClusterConfig
```

### 4.3 Agent Implementation (Modified)

The strands-agents implementation shall be modified to accept dynamic configuration:

**Agent Factory** (`agents.py`):
```python
def create_ray_code_agent(config: dict):
    """Create agent with dynamic configuration
    
    Args:
        config: {
            'ray_cluster_url': str,  # e.g., 'http://cluster-ip:8265'
            'bedrock_model_id': str,
            'bedrock_region': str,
            'aws_profile': str
        }
    
    Returns:
        Agent: Configured Ray code agent
    """
    # Extract Ray cluster endpoint
    RAY_DASHBOARD_URL = config['ray_cluster_url']
    RAY_JOBS_API = f"{RAY_DASHBOARD_URL}/api/jobs/"
    
    # Initialize Bedrock model with provided config
    model = BedrockModel(
        model_id=config['bedrock_model_id'],
        region=config['bedrock_region'],
        profile=config.get('aws_profile', 'default')
    )
    
    @tool
    def get_data_sources(session_id: str) -> dict:
        """Get available CSV files and Glue tables for the isolated prompt session"""
        from main import prompt_sessions
        
        if session_id not in prompt_sessions:
            return {"csv": None, "tables": []}
        
        prompt_data = prompt_sessions[session_id]
        return {
            "csv": prompt_data['csv'],
            "tables": prompt_data['tables']
        }
    
    @tool
    def validate_code(code: str) -> dict:
        """Validate Ray code by executing on configured cluster"""
        try:
            # Remove any existing ray.init() calls
            test_code = re.sub(r'ray\.init\([^)]*\)\s*\n?', '', code)
            script = f"import ray\nray.init(address='auto')\n{test_code}"
            encoded = base64.b64encode(script.encode()).decode()
            
            # Submit to configured cluster
            job_data = {
                "entrypoint": f"python -c \"import base64; exec(base64.b64decode('{encoded}').decode())\""
            }
            response = requests.post(RAY_JOBS_API, json=job_data, timeout=5)
            response.raise_for_status()
            job_id = response.json()['job_id']
            
            # Poll for completion (2 min timeout for validation)
            start_time = time.time()
            while time.time() - start_time < 120:
                status_response = requests.get(f"{RAY_JOBS_API}{job_id}")
                status_data = status_response.json()
                
                if status_data['status'] == 'SUCCEEDED':
                    return {"success": True, "error": None}
                elif status_data['status'] == 'FAILED':
                    logs_response = requests.get(f"{RAY_JOBS_API}{job_id}/logs")
                    logs = logs_response.json().get('logs', '')
                    error_lines = [l for l in logs.split('\n') 
                                 if 'Error' in l or 'Exception' in l or 'Traceback' in l]
                    error = '\n'.join(error_lines[-5:]) if error_lines else logs[-300:]
                    return {"success": False, "error": error}
                
                time.sleep(1)
            
            return {"success": False, "error": "Validation timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    agent = Agent(
        model=model,
        system_prompt="""You are a Ray distributed data processing specialist.

MANDATORY WORKFLOW - FOLLOW EXACTLY:
1. Extract the Session ID from the user prompt (format: "Session ID: xxx")
2. Call get_data_sources(session_id) using that Session ID to discover available data
3. Generate Ray code using the discovered data sources
4. Call validate_code(code) to test the generated code
5. Check validation result:
   - If success=True: Return ONLY the validated code
   - If success=False: Read the error, fix the code, call validate_code again
6. Repeat validation up to 3 times if needed
7. You MUST get success=True before returning code
8. If all 3 attempts fail, return: "Validation failed after 3 attempts: [error]"

RAY OPERATIONS:
- ray.data.read_csv(s3_path), ray.data.read_parquet(s3_path)
- .map(lambda x: {...}) - Return dict
- .filter(lambda x: condition)
- .take_all() - Get results
- print() for output

CRITICAL RULES:
- NEVER use pandas
- map() returns dict, not scalars
- Always include print() statements
- Use exact S3 paths from get_data_sources

DATA SOURCE FORMAT:
CSV: {"filename": "x.csv", "s3_path": "s3://bucket/path"}
Glue: {"database": "db", "table": "tbl", "location": "s3://..."}

RETURN FORMAT:
Return ONLY the Python code that passed validation (no explanations, no markdown).""",
        tools=[get_data_sources, validate_code],
        name="RayCodeAgent"
    )
    
    return agent
```

**Backend Integration** (`main.py`):
```python
@app.post("/generate")
async def generate_code(request: GenerateRequest):
    """Generate Ray code using strands-agents with dynamic config"""
    try:
        # Extract config from request
        config = {
            'ray_cluster_url': str(request.config.ray_cluster_url),
            'bedrock_model_id': request.config.bedrock_model_id,
            'bedrock_region': request.config.bedrock_region,
            'aws_profile': request.config.aws_profile
        }
        
        # Validate cluster connectivity
        try:
            response = requests.get(
                f"{config['ray_cluster_url']}/api/version", 
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"Ray cluster unreachable: {str(e)}"
            )
        
        # Create agent with provided config
        ray_code_agent = create_ray_code_agent(config)
        
        # Get or create session
        if request.session_id not in sessions:
            sessions[request.session_id] = CodeInterpreterSession(request.session_id)
        
        session = sessions[request.session_id]
        
        # Create isolated prompt session ID
        prompt_id = f"{request.session_id}_{int(time.time() * 1000)}"
        session.current_prompt_id = prompt_id
        
        # Snapshot current data sources for this prompt (isolation)
        prompt_sessions[prompt_id] = {
            'csv': session.uploaded_csv,
            'tables': session.selected_tables.copy() if session.selected_tables else []
        }
        
        # Clear pending data sources for next prompt (start fresh session)
        session.uploaded_csv = None
        session.selected_tables = []
        
        # Log snapshot for this prompt
        snapshot = prompt_sessions[prompt_id]
        print(f"📊 Prompt session {prompt_id}:")
        print(f"   - Cluster: {config['ray_cluster_url']}")
        print(f"   - Model: {config['bedrock_model_id']}")
        print(f"   - CSV: {snapshot['csv']['filename'] if snapshot['csv'] else 'None'}")
        print(f"   - Tables: {len(snapshot['tables'])} selected")
        
        # Build prompt with session_id for tool calls
        prompt = f"Session ID: {prompt_id}\n\n{request.prompt}"
        
        print(f"🤖 Agent generating code with isolated session...")
        
        # Invoke agent with unique session ID for complete isolation
        response = await ray_code_agent.invoke_async(
            prompt,
            session_id=prompt_id
        )
        
        # Extract code from response
        full_response = ""
        if hasattr(response.message, 'content'):
            for block in response.message.content:
                if hasattr(block, 'text'):
                    full_response += block.text
                elif isinstance(block, dict) and 'text' in block:
                    full_response += block['text']
        else:
            full_response = str(response.message)
        
        # Check if agent reported validation failure
        if 'validation failed' in full_response.lower():
            print(f"⚠️ Agent reported validation failure")
            return {
                "success": False,
                "code": "",
                "error": full_response,
                "session_id": request.session_id
            }
        
        # Extract code
        code = full_response
        if '```python' in code:
            code = code.split('```python')[1].split('```')[0].strip()
        elif '```' in code:
            code = code.split('```')[1].split('```')[0].strip()
        
        code = code.strip()
        
        # Execute validated code if auto-execute enabled
        if request.config.auto_execute:
            print(f"🚀 Executing code...")
            execution_result = await execute_code_on_cluster(
                code, 
                request.session_id,
                config
            )
            
            # Store in history
            # ... (existing history storage logic)
            
            return {
                "success": True,
                "code": code,
                "execution_result": execution_result['result'],
                "job_id": execution_result['job_id'],
                "cluster_url": config['ray_cluster_url']
            }
        else:
            return {
                "success": True,
                "code": code,
                "cluster_url": config['ray_cluster_url']
            }
            
    except Exception as e:
        print(f"❌ Code generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_code_on_cluster(code: str, session_id: str, config: dict) -> dict:
    """Execute code on configured Ray cluster"""
    try:
        RAY_JOBS_API = f"{config['ray_cluster_url']}/api/jobs/"
        
        # Prepare code for execution
        test_code = re.sub(r'ray\.init\([^)]*\)\s*\n?', '', code)
        script = f"import ray\nray.init(address='auto')\n{test_code}"
        encoded = base64.b64encode(script.encode()).decode()
        
        job_data = {
            "entrypoint": f"python -c \"import base64; exec(base64.b64decode('{encoded}').decode())\""
        }
        
        response = requests.post(RAY_JOBS_API, json=job_data, timeout=10)
        response.raise_for_status()
        job_id = response.json()['job_id']
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 min timeout
            status_response = requests.get(f"{RAY_JOBS_API}{job_id}")
            status_data = status_response.json()
            
            if status_data['status'] == 'SUCCEEDED':
                logs_response = requests.get(f"{RAY_JOBS_API}{job_id}/logs")
                logs = logs_response.json().get('logs', '')
                
                # Filter logs
                filtered_logs = filter_ray_logs(logs)
                
                return {
                    "success": True,
                    "result": filtered_logs,
                    "job_id": job_id
                }
            elif status_data['status'] == 'FAILED':
                logs_response = requests.get(f"{RAY_JOBS_API}{job_id}/logs")
                logs = logs_response.json().get('logs', '')
                return {
                    "success": False,
                    "error": logs,
                    "job_id": job_id
                }
            
            await asyncio.sleep(2)
        
        return {
            "success": False,
            "error": "Execution timeout",
            "job_id": job_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "job_id": None
        }
```

### 4.4 Configuration Management

**REQ-BACK-001**: No Environment Variables  
Backend shall NOT rely on environment variables for Ray cluster or Bedrock configuration. All configuration shall come from API requests.

**REQ-BACK-002**: Configuration Validation  
Backend shall validate configuration on each request:
- Ray cluster URL is reachable (HTTP GET to /api/version)
- Bedrock model ID format is valid
- AWS credentials are available for specified profile
- Return clear error messages (HTTP 400/503) for invalid config

**REQ-BACK-003**: Agent Instance Caching  
Backend may cache agent instances per configuration hash to improve performance:
```python
agent_cache = {}  # {config_hash: agent_instance}

def get_or_create_agent(config):
    config_hash = hash(frozenset(config.items()))
    if config_hash not in agent_cache:
        agent_cache[config_hash] = create_ray_code_agent(config)
    return agent_cache[config_hash]
```

**REQ-BACK-004**: Backward Compatibility  
Backend shall support legacy mode for existing deployments:
- If `config` not provided in request, read from environment variables
- Log warning about deprecated usage
- Recommend migration to config-based approach

---

## 5. Configuration Flow

### 5.1 Extension to Backend Communication

**REQ-FLOW-001**: Configuration Injection  
On every API request, the extension shall inject configuration from settings.

**REQ-FLOW-002**: Configuration Updates  
When user changes settings:
1. Extension validates new settings
2. Next request uses updated config
3. Backend creates new agent instance
4. No restart required for either component

### 5.2 Agent Configuration Flow

```
VSCode Settings (user configured)
    ↓
Extension reads: rayClusterUrl, bedrockModelId, bedrockRegion, awsProfile
    ↓
Extension validates settings
    ↓
Extension sends request with config object
    ↓
Backend receives config
    ↓
Backend validates cluster connectivity
    ↓
Backend creates/retrieves agent:
  - BedrockModel(model_id, region, profile)
  - RAY_JOBS_API from cluster_url
    ↓
Agent validates code on configured cluster
    ↓
Backend executes on configured cluster
    ↓
Results returned to extension with cluster info
```

---

## 6. Implementation Plan

### 6.1 Phase 1: Core Extension & Settings (Week 1)
- [ ] Extension scaffolding (TypeScript)
- [ ] Settings configuration with validation
- [ ] Multi-cluster profile support
- [ ] Backend HTTP client with config injection
- [ ] Execute Selection command
- [ ] Execute File command
- [ ] Output channel for results
- [ ] Status bar with cluster indicator

### 6.2 Phase 2: Backend Modifications (Week 2)
- [ ] Modify `/generate` endpoint to accept ClusterConfig
- [ ] Modify `/execute` endpoint to accept ClusterConfig
- [ ] Update `create_ray_code_agent(config)` for dynamic initialization
- [ ] Add config validation in backend
- [ ] Update job management endpoints with cluster_url parameter
- [ ] Add `/health` and `/test-connection` endpoints
- [ ] Implement agent instance caching
- [ ] Test with multiple cluster configurations

### 6.3 Phase 3: Chat Interface (Week 3)
- [ ] Chat panel Webview with cluster selector
- [ ] Message input/display
- [ ] Code generation integration with config
- [ ] Code display with syntax highlighting
- [ ] Insert to editor functionality
- [ ] Session management
- [ ] Show active cluster in chat header

### 6.4 Phase 4: Dashboard & Jobs (Week 4)
- [ ] Dashboard panel (bottom panel) with dynamic URL
- [ ] Jobs TreeView panel grouped by cluster
- [ ] Job list refresh from multiple clusters
- [ ] Stop job functionality with cluster routing
- [ ] Job details display with cluster info
- [ ] Dashboard navigation and cluster switching

### 6.5 Phase 5: Data Sources & Polish (Week 5)
- [ ] CSV upload dialog
- [ ] Table selection dialog
- [ ] Data source display in chat
- [ ] Error handling for cluster connectivity
- [ ] Loading indicators
- [ ] Notifications with cluster context
- [ ] Connection test command

### 6.6 Phase 6: Testing & Documentation (Week 6)
- [ ] Unit tests for config validation
- [ ] Integration tests with different clusters
- [ ] Test with local Ray cluster
- [ ] Test with cloud Ray clusters
- [ ] Documentation (setup, configuration, usage)
- [ ] Example configurations for different cluster types
- [ ] Troubleshooting guide
- [ ] Package and publish to VSCode Marketplace

---

## 7. File Structure

```
ray-code-interpreter-vscode/
├── package.json                 # Extension manifest with settings schema
├── tsconfig.json               # TypeScript config
├── src/
│   ├── extension.ts            # Extension entry point
│   ├── commands/
│   │   ├── execute.ts          # Execute commands
│   │   ├── generate.ts         # Generate commands
│   │   ├── jobs.ts             # Job management commands
│   │   └── cluster.ts          # Cluster switching commands
│   ├── panels/
│   │   ├── chatPanel.ts        # Chat webview panel
│   │   ├── dashboardPanel.ts   # Dashboard webview panel
│   │   └── jobsPanel.ts        # Jobs tree view panel
│   ├── services/
│   │   ├── backendClient.ts    # HTTP client with config injection
│   │   ├── configManager.ts    # Settings and cluster management
│   │   ├── sessionManager.ts   # Session management
│   │   └── validator.ts        # Config validation
│   ├── models/
│   │   ├── config.ts           # Configuration interfaces
│   │   ├── cluster.ts          # Cluster profile model
│   │   └── request.ts          # API request models
│   ├── utils/
│   │   ├── logger.ts           # Logging utility
│   │   └── constants.ts        # Constants and defaults
│   └── webviews/
│       ├── chat.html           # Chat UI
│       ├── dashboard.html      # Dashboard UI
│       └── styles.css          # Webview styles
├── backend/                    # Modified FastAPI backend
│   ├── main.py                 # FastAPI server (modified)
│   ├── agents.py               # Strands-agents (modified)
│   ├── models.py               # Pydantic models (new)
│   └── requirements.txt        # Python dependencies
└── README.md                   # Documentation
```

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Configuration validation logic
- Cluster profile management
- Backend client methods
- Session management
- Request/response parsing

### 8.2 Integration Tests
- End-to-end code execution on different clusters
- Code generation with different Bedrock models
- Job management across multiple clusters
- Data source handling
- Cluster switching scenarios

### 8.3 Configuration Tests
- Valid cluster configurations
- Invalid cluster URLs
- Unreachable clusters
- Invalid Bedrock model IDs
- Missing AWS credentials
- Multi-cluster scenarios

### 8.4 Manual Tests
- UI responsiveness
- Webview rendering
- Context menu actions
- Keyboard shortcuts
- Settings UI
- Error messages clarity

---

## 9. Dependencies

### 9.1 VSCode Extension
- `@types/vscode`: ^1.80.0
- `axios`: ^1.5.0
- `typescript`: ^5.0.0

### 9.2 Backend (Modified)
- FastAPI
- strands-agents
- boto3 (AWS SDK)
- requests
- pydantic (for config models)

### 9.3 Ray Cluster (External - Not Provided)
The extension works with any Ray cluster that provides:
- Ray Dashboard API (port 8265 by default)
- Job submission endpoint (`/api/jobs/`)
- Ray version 2.x or higher

**Cluster Requirements**:
- Accessible HTTP endpoint for dashboard
- Network connectivity from user's machine
- Optional: ML packages (torch, numpy, etc.) if needed for jobs

**Supported Cluster Types**:
- Local Ray cluster (`ray start --head`)
- AWS ECS Fargate (user-deployed)
- Kubernetes Ray cluster
- Ray on VMs
- Anyscale hosted clusters
- Any Ray deployment with HTTP API access

**Note**: Cluster deployment and management are NOT part of this extension. Users must provide their own Ray cluster.

---

## 10. Constraints & Assumptions

### 10.1 Constraints
- Backend must be running locally or accessible via network
- Ray cluster must be deployed and accessible (not provided by extension)
- Ray cluster must expose dashboard API (port 8265 by default)
- AWS credentials must be configured for Bedrock access
- VSCode version >= 1.80.0
- Network connectivity required between:
  - VSCode ↔ Backend
  - Backend ↔ Ray Cluster
  - Backend ↔ AWS Bedrock

### 10.2 Assumptions
- Users have Python knowledge
- Users have AWS Bedrock access and credentials configured
- Users have deployed their own Ray cluster
- Backend is pre-configured and running
- Network connectivity is stable
- Ray cluster version is 2.x or higher
- Users understand Ray concepts (jobs, tasks, actors)

---

## 11. Non-Functional Requirements

### 11.1 Performance
- Extension activation: < 2 seconds
- Settings validation: < 500ms
- Code execution: Non-blocking UI
- Job list refresh: < 1 second per cluster
- Dashboard loading: < 3 seconds

### 11.2 Reliability
- Graceful handling of cluster unavailability
- Retry logic for transient network failures
- Clear error messages for configuration issues
- State persistence across VSCode restarts

### 11.3 Security
- No credential storage in settings
- Use AWS credential chain (env vars, ~/.aws/credentials)
- HTTPS support for cluster connections
- Validate all user inputs

### 11.4 Usability
- Intuitive configuration UI
- Clear error messages with actionable steps
- Contextual help and tooltips
- Consistent with VSCode UX patterns

---

## 12. Future Enhancements

### 12.1 Phase 2 Features
- Inline code suggestions
- Code snippets library
- Collaborative sessions
- Code diff viewer
- Performance profiling integration
- Custom agent configurations

### 12.2 Advanced Features
- Jupyter notebook integration
- Git integration for code versioning
- Local Ray cluster auto-start
- Code testing framework
- Ray Serve deployment support
- Ray Tune hyperparameter tuning UI

---

## 13. Acceptance Criteria

### 13.1 Core Functionality
- ✅ Execute selected code on any configured cluster
- ✅ Execute file from explorer on any configured cluster
- ✅ Generate code using any Bedrock model
- ✅ Display execution results with cluster context
- ✅ View Ray dashboard for any cluster in VSCode

### 13.2 Configuration
- ✅ Configure multiple Ray clusters
- ✅ Switch between clusters seamlessly
- ✅ Configure Bedrock model and region
- ✅ Validate all configurations
- ✅ Test connectivity to cluster and Bedrock

### 13.3 Job Management
- ✅ List jobs from all configured clusters
- ✅ Stop jobs on any cluster
- ✅ View job logs
- ✅ Auto-refresh job list

### 13.4 User Experience
- ✅ Intuitive UI with cluster indicators
- ✅ Clear error messages
- ✅ Fast response times
- ✅ Stable operation with multiple clusters

### 13.5 Documentation
- ✅ Complete README with setup instructions
- ✅ Configuration guide for different cluster types
- ✅ Troubleshooting section
- ✅ Example workflows

---

## 14. Glossary

| Term | Definition |
|------|------------|
| Agent | AI-powered code generation system using AWS Bedrock |
| Backend | FastAPI server handling code generation and execution |
| Ray Cluster | Distributed computing cluster for code execution (user-provided) |
| Session | Isolated execution context with data sources |
| Webview | VSCode UI component for custom HTML/CSS/JS |
| TreeView | VSCode UI component for hierarchical data |
| Command Palette | VSCode command search interface (Ctrl+Shift+P) |
| Cluster Profile | Saved configuration for a Ray cluster |
| Dynamic Configuration | Runtime configuration passed per request |

---

## 15. References

- VSCode Extension API: https://code.visualstudio.com/api
- Ray Documentation: https://docs.ray.io/
- Ray Dashboard API: https://docs.ray.io/en/latest/cluster/running-applications/job-submission/rest.html
- Strands-Agents: https://strandsagents.com/
- AWS Bedrock: https://aws.amazon.com/bedrock/
- FastAPI: https://fastapi.tiangolo.com/

---

## 16. Appendix

### 16.1 Example Configuration

**settings.json**:
```json
{
  "rayInterpreter.backendUrl": "http://localhost:8000",
  "rayInterpreter.rayClusterUrl": "http://my-cluster.example.com:8265",
  "rayInterpreter.bedrockModelId": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "rayInterpreter.bedrockRegion": "us-east-1",
  "rayInterpreter.awsProfile": "default",
  "rayInterpreter.autoExecute": true,
  "rayInterpreter.clusters": [
    {
      "name": "Production",
      "url": "http://prod-cluster:8265",
      "default": true
    },
    {
      "name": "Development",
      "url": "http://dev-cluster:8265"
    },
    {
      "name": "Local",
      "url": "http://localhost:8265"
    }
  ]
}
```

### 16.2 Example API Request

```typescript
// Extension sends to backend
const request = {
  prompt: "Create a dataset with 100 rows and calculate squared values",
  session_id: "vscode-session-abc123",
  config: {
    ray_cluster_url: "http://prod-cluster:8265",
    bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    bedrock_region: "us-east-1",
    aws_profile: "default"
  }
};

const response = await axios.post(
  'http://localhost:8000/generate',
  request
);

// Response includes cluster info
console.log(response.data.cluster_url); // "http://prod-cluster:8265"
console.log(response.data.code); // Generated Ray code
console.log(response.data.job_id); // "raysubmit_..."
```

---

**Document Version**: 2.0  
**Last Updated**: October 6, 2025  
**Status**: Final - Ready for Implementation  
**Key Changes from v1.0**:
- Removed ECS cluster deployment requirements
- Added dynamic configuration support
- Modified backend to accept config per request
- Updated agent initialization for runtime configuration
- Added multi-cluster support
- Added configuration validation requirements

