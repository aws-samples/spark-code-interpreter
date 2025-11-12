# Software Requirements Specification (SRS)
## VSCode Ray Code Interpreter Plugin

**Version**: 1.0  
**Date**: October 6, 2025  
**Based on**: Ray Code Interpreter Web Application

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for converting the Ray Code Interpreter web application into a Visual Studio Code extension. The plugin will enable users to execute Ray code on remote clusters, generate code using AI, and manage Ray jobs directly from VSCode.

### 1.2 Scope
The VSCode plugin will:
- Replace the React frontend with VSCode UI components
- Retain the existing FastAPI backend and strands-agents implementation
- Add VSCode-specific features (file execution, right-click context menus)
- Provide integrated Ray Dashboard viewing
- Enable natural language code generation via chat interface
- Support any Ray cluster via configurable endpoints (no cluster deployment)
- Pass configuration settings to backend for dynamic agent initialization

### 1.3 Definitions
- **Ray Cluster**: Remote Ray cluster running on AWS ECS
- **Backend**: Existing FastAPI server with strands-agents
- **Agent**: AI agent using AWS Bedrock for code generation
- **Session**: Isolated execution context for prompts

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
│  │  - Settings Management                                │   │
│  │  - Backend Communication (HTTP Client)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Existing)                      │
├─────────────────────────────────────────────────────────────┤
│  - /generate (Code generation with agent)                    │
│  - /execute (Code execution on cluster)                      │
│  - /ray/jobs (List jobs)                                     │
│  - /ray/jobs/{id}/stop (Stop job)                           │
│  - /upload-csv (CSV upload)                                  │
│  - /sessions/{id}/select-tables (Table selection)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Strands-Agents (Existing)                            │
│  - RayCodeAgent (get_data_sources, validate_code)           │
│  - BedrockModel (Claude Sonnet 4.5)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Ray Cluster (AWS ECS)                           │
│  - Ray 2.49.2                                                │
│  - Dashboard (port 8265)                                     │
│  - Job execution                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

**VSCode Extension**:
- Language: TypeScript
- Framework: VSCode Extension API
- UI: Webview API (for chat and dashboard)
- HTTP Client: axios or node-fetch

**Backend** (No changes):
- FastAPI (Python)
- strands-agents framework
- AWS Bedrock (Claude Sonnet 4.5)

**Ray Cluster** (No changes):
- Ray 2.49.2 on AWS ECS Fargate
- 4GB RAM, 2 vCPU

---

## 3. Functional Requirements

### 3.1 Configuration Settings

**REQ-CFG-001**: Plugin Settings  
The extension shall provide the following configurable settings:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `rayInterpreter.backendUrl` | string | `http://localhost:8000` | FastAPI backend URL |
| `rayInterpreter.rayClusterUrl` | string | `` | Ray cluster dashboard URL (e.g., http://cluster-ip:8265) |
| `rayInterpreter.rayClusterAddress` | string | `` | Ray cluster address for job submission (e.g., cluster-ip:8265) |
| `rayInterpreter.bedrockModelId` | string | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | AWS Bedrock model ID |
| `rayInterpreter.bedrockRegion` | string | `us-east-1` | AWS Bedrock region |
| `rayInterpreter.awsProfile` | string | `default` | AWS profile name |
| `rayInterpreter.autoExecute` | boolean | `true` | Auto-execute after generation |
| `rayInterpreter.sessionId` | string | `vscode-session` | Session identifier |

**REQ-CFG-002**: Settings Validation  
The extension shall validate settings on activation:
- `rayClusterUrl` must be a valid HTTP/HTTPS URL
- `rayClusterAddress` must be in format `host:port`
- `bedrockModelId` must not be empty
- Display errors for invalid configurations

**REQ-CFG-003**: Settings UI  
Settings shall be accessible via VSCode Settings UI under "Ray Interpreter" category.

**REQ-CFG-004**: Configuration Passthrough  
Extension shall pass configuration to backend on each request:
- Ray cluster endpoint
- Bedrock model ID and region
- AWS profile
Backend shall use these settings to initialize agents dynamically.

---

### 3.2 Code Execution

**REQ-EXEC-001**: Execute Selected Code  
When user selects code in a Python file and invokes "Ray: Execute Selection":
1. Extract selected text
2. Send to backend `/execute` endpoint
3. Display execution results in Output panel
4. Show job ID and status

**REQ-EXEC-002**: Execute Entire File  
When user right-clicks a Python file and selects "Ray: Execute File":
1. Read entire file content
2. Send to backend `/execute` endpoint
3. Display results in Output panel
4. Update Jobs panel with new job

**REQ-EXEC-003**: Execute from File Explorer  
Right-click context menu in File Explorer shall include "Ray: Execute File" option for `.py` files.

**REQ-EXEC-004**: Execution Feedback  
During execution:
- Show progress notification
- Display "Executing..." status in status bar
- Stream logs to Output panel if available

**REQ-EXEC-005**: Execution Results  
After execution:
- Display success/failure notification
- Show execution output in dedicated Output channel
- Highlight errors in red
- Provide "View in Dashboard" link

---

### 3.3 Code Generation (Chat Interface)

**REQ-GEN-001**: Chat Panel  
The extension shall provide a chat panel (Webview) for natural language code generation:
- Located in Activity Bar (sidebar)
- Persistent across sessions
- Scrollable message history

**REQ-GEN-002**: Message Input  
Chat panel shall include:
- Text input field for prompts
- Send button
- Clear history button
- Data source selection (CSV/Tables)

**REQ-GEN-003**: Code Generation Flow  
When user submits a prompt:
1. Send to backend `/generate` endpoint with session ID
2. Display "Generating..." indicator
3. Show agent's thinking process (optional)
4. Display generated code in chat
5. Provide "Insert to Editor" button
6. Provide "Execute" button

**REQ-GEN-004**: Agent Integration  
The backend agent workflow shall be preserved:
1. Agent calls `get_data_sources(session_id)`
2. Agent generates Ray code
3. Agent calls `validate_code(code)` up to 3 times
4. Agent returns validated code
5. Backend auto-executes if `autoExecute` is true

**REQ-GEN-005**: Code Display  
Generated code shall be displayed with:
- Syntax highlighting (Python)
- Copy button
- Insert to editor button
- Execute button
- Edit and re-execute option

**REQ-GEN-006**: Session Isolation  
Each prompt shall create an isolated session:
- Unique session ID per prompt
- No context overlap between prompts
- Data sources snapshot per prompt
- Enable re-execution from history

**REQ-GEN-007**: Conversation History  
Chat panel shall display:
- User prompts
- Generated code
- Execution results
- Timestamps
- Data sources used

---

### 3.4 Ray Dashboard Integration

**REQ-DASH-001**: Dashboard Panel  
The extension shall provide a Ray Dashboard panel:
- Located in bottom panel (alongside Terminal, Debug Console)
- Implemented as Webview
- Loads Ray dashboard URL from settings

**REQ-DASH-002**: Dashboard Tab  
Dashboard shall appear as a tab named "Ray Dashboard" in the bottom panel.

**REQ-DASH-003**: Dashboard Features  
The dashboard panel shall:
- Display full Ray dashboard UI
- Support all dashboard interactions
- Auto-refresh on job submission
- Provide "Open in Browser" button

**REQ-DASH-004**: Dashboard Link  
All execution results shall include a "View in Dashboard" link that:
- Opens Dashboard panel if closed
- Focuses Dashboard tab
- Optionally navigates to specific job

---

### 3.5 Job Management

**REQ-JOB-001**: Jobs Panel  
The extension shall provide a Jobs TreeView panel showing:
- Running jobs
- Completed jobs (last 10)
- Failed jobs (last 10)
- Job ID, status, start time

**REQ-JOB-002**: Job List Refresh  
Jobs panel shall:
- Auto-refresh every 5 seconds when jobs are running
- Provide manual refresh button
- Show loading indicator during refresh

**REQ-JOB-003**: Job Actions  
Right-click context menu on job shall provide:
- "Stop Job" (for running jobs)
- "View Logs"
- "View in Dashboard"
- "Copy Job ID"

**REQ-JOB-004**: Stop Job  
When user stops a job:
1. Send request to `/ray/jobs/{id}/stop`
2. Show confirmation dialog
3. Update job status in panel
4. Display notification on success/failure

**REQ-JOB-005**: Job Status Icons  
Jobs shall display status icons:
- 🟢 Running
- ✅ Succeeded
- ❌ Failed
- ⏸️ Stopped
- ⏳ Pending

**REQ-JOB-006**: Job Details  
Clicking a job shall show details in Output panel:
- Job ID
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
| Ray: Execute Selection | `rayInterpreter.executeSelection` | Execute selected code |
| Ray: Execute File | `rayInterpreter.executeFile` | Execute current file |
| Ray: Generate Code | `rayInterpreter.generateCode` | Open chat panel |
| Ray: Open Dashboard | `rayInterpreter.openDashboard` | Open dashboard panel |
| Ray: Refresh Jobs | `rayInterpreter.refreshJobs` | Refresh jobs list |
| Ray: Stop Job | `rayInterpreter.stopJob` | Stop selected job |
| Ray: Clear Chat | `rayInterpreter.clearChat` | Clear chat history |
| Ray: Upload CSV | `rayInterpreter.uploadCsv` | Upload CSV file |
| Ray: Select Tables | `rayInterpreter.selectTables` | Select Glue tables |

**REQ-CMD-002**: Keybindings  
Default keybindings:
- `Ctrl+Shift+R` (Cmd+Shift+R on Mac): Execute Selection
- `Ctrl+Shift+G` (Cmd+Shift+G on Mac): Generate Code

---

### 3.8 User Interface

**REQ-UI-001**: Activity Bar Icon  
Extension shall add "Ray" icon to Activity Bar for chat panel access.

**REQ-UI-002**: Status Bar  
Extension shall show status in status bar:
- Cluster connection status (🟢 Connected / 🔴 Disconnected)
- Current job count
- Click to open Dashboard

**REQ-UI-003**: Output Channel  
Extension shall create "Ray Interpreter" output channel for:
- Execution logs
- Error messages
- Job status updates

**REQ-UI-004**: Notifications  
Extension shall show notifications for:
- Execution success/failure
- Job completion
- Connection errors
- Configuration errors

**REQ-UI-005**: Webview Styling  
Webviews (Chat, Dashboard) shall:
- Match VSCode theme (dark/light)
- Use VSCode UI toolkit styles
- Support responsive layout

---

## 4. Non-Functional Requirements

### 4.1 Performance

**REQ-PERF-001**: Startup Time  
Extension activation shall complete within 2 seconds.

**REQ-PERF-002**: Code Execution  
Code execution shall not block VSCode UI.

**REQ-PERF-003**: Job List Refresh  
Job list refresh shall complete within 1 second.

### 4.2 Reliability

**REQ-REL-001**: Error Handling  
Extension shall gracefully handle:
- Backend connection failures
- Ray cluster unavailability
- Invalid code execution
- Network timeouts

**REQ-REL-002**: State Persistence  
Extension shall persist:
- Chat history (last 50 messages)
- Session ID
- Data source selections

### 4.3 Security

**REQ-SEC-001**: Credentials  
Extension shall use AWS credentials from:
- Environment variables
- AWS credentials file (~/.aws/credentials)
- Never store credentials in settings

**REQ-SEC-002**: Code Execution  
Extension shall warn users before executing:
- Code from untrusted sources
- Code with destructive operations

### 4.4 Usability

**REQ-USE-001**: Documentation  
Extension shall include:
- README with setup instructions
- Command descriptions
- Configuration examples
- Troubleshooting guide

**REQ-USE-002**: Error Messages  
Error messages shall be:
- Clear and actionable
- Include troubleshooting hints
- Provide links to documentation

---

## 5. Backend Requirements (Modified)

### 5.1 API Endpoints (Modified)

The existing FastAPI backend shall be modified to accept configuration parameters:

**Code Generation**:
- `POST /generate` - Generate code with agent
  - Input: `{prompt, session_id, config: {ray_cluster_url, bedrock_model_id, bedrock_region, aws_profile}}`
  - Output: `{code, execution_result, job_id}`
  - Agent initialized with provided config

**Code Execution**:
- `POST /execute` - Execute code on cluster
  - Input: `{code, session_id, config: {ray_cluster_url}}`
  - Output: `{result, job_id, success}`
  - Uses provided Ray cluster endpoint

**Job Management**:
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

### 5.2 Agent Implementation (Modified)

The strands-agents implementation shall be modified to accept dynamic configuration:

**Agent Initialization** (`agents.py`):
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
        # Existing implementation
        pass
    
    @tool
    def validate_code(code: str) -> dict:
        """Validate Ray code by executing on cluster"""
        # Use RAY_JOBS_API from config
        # Existing implementation with dynamic endpoint
        pass
    
    agent = Agent(
        model=model,
        system_prompt="""...""",  # Existing prompt
        tools=[get_data_sources, validate_code],
        name="RayCodeAgent"
    )
    
    return agent
```

**Backend Modifications** (`main.py`):
```python
@app.post("/generate")
async def generate_code(request: GenerateRequest):
    """Generate Ray code using strands-agents with dynamic config"""
    
    # Extract config from request
    config = {
        'ray_cluster_url': request.config.get('ray_cluster_url'),
        'bedrock_model_id': request.config.get('bedrock_model_id'),
        'bedrock_region': request.config.get('bedrock_region'),
        'aws_profile': request.config.get('aws_profile', 'default')
    }
    
    # Create agent with provided config
    ray_code_agent = create_ray_code_agent(config)
    
    # Existing generation logic
    # ...
```

**Request Models** (`main.py`):
```python
class ClusterConfig(BaseModel):
    ray_cluster_url: str
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_region: str = "us-east-1"
    aws_profile: str = "default"

class GenerateRequest(BaseModel):
    prompt: str
    session_id: str
    config: ClusterConfig

class ExecuteRequest(BaseModel):
    code: str
    session_id: str
    config: ClusterConfig
```

**Agent Workflow** (No changes):
1. Extract Session ID from prompt
2. Call `get_data_sources(session_id)`
3. Generate Ray code using data sources
4. Call `validate_code(code)` to test on configured cluster
5. If validation fails, fix and retry (up to 3 times)
6. Return validated code

**Session Isolation** (No changes):
- Each prompt gets unique session ID: `{base_session}_{timestamp}`
- Data sources snapshot to `prompt_sessions[session_id]`
- No context overlap between prompts
- Data sources cleared after prompt execution

### 5.3 Configuration Management

**REQ-BACK-001**: Environment Variables (Deprecated)  
Backend shall NOT rely on environment variables for Ray cluster or Bedrock configuration. All configuration shall come from API requests.

**REQ-BACK-002**: Configuration Validation  
Backend shall validate configuration on each request:
- Ray cluster URL is reachable
- Bedrock model ID is valid
- AWS credentials are available
- Return clear error messages for invalid config

**REQ-BACK-003**: Configuration Caching  
Backend may cache agent instances per configuration to improve performance, but shall support dynamic reconfiguration.

**REQ-BACK-004**: Backward Compatibility  
Backend shall support both:
- Legacy mode: Read from environment variables if config not provided
- New mode: Use config from request (preferred)

---

## 6. Configuration Flow

### 6.1 Extension to Backend Communication

**REQ-FLOW-001**: Configuration Injection  
On every API request, the extension shall inject configuration:

```typescript
// Extension sends
{
  prompt: "Create a dataset...",
  session_id: "vscode-session-123",
  config: {
    ray_cluster_url: "http://my-cluster:8265",
    bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    bedrock_region: "us-east-1",
    aws_profile: "default"
  }
}
```

**REQ-FLOW-002**: Backend Processing  
Backend shall:
1. Extract config from request
2. Initialize agent with config
3. Use Ray cluster endpoint from config
4. Return results

**REQ-FLOW-003**: Configuration Updates  
When user changes settings:
1. Extension validates new settings
2. Next request uses updated config
3. Backend creates new agent instance
4. No restart required

### 6.2 Agent Configuration Flow

```
VSCode Settings
    ↓
Extension reads config
    ↓
Extension sends request with config
    ↓
Backend receives config
    ↓
Backend creates agent with:
  - BedrockModel(model_id, region, profile)
  - RAY_JOBS_API from cluster_url
    ↓
Agent validates code on configured cluster
    ↓
Backend executes on configured cluster
    ↓
Results returned to extension
```

### 6.3 Multi-Cluster Support

**REQ-MULTI-001**: Cluster Profiles  
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
    }
  ]
}
```

**REQ-MULTI-002**: Cluster Selection  
Extension shall provide cluster selector in:
- Status bar (click to switch)
- Chat panel (dropdown)
- Command palette

---

## 7. Implementation Plan

### 6.1 Phase 1: Core Extension (Week 1)
- [ ] Extension scaffolding (TypeScript)
- [ ] Settings configuration
- [ ] Backend HTTP client
- [ ] Execute Selection command
- [ ] Execute File command
- [ ] Output channel for results

### 6.2 Phase 2: Chat Interface (Week 2)
- [ ] Chat panel Webview
- [ ] Message input/display
- [ ] Code generation integration
- [ ] Code display with syntax highlighting
- [ ] Insert to editor functionality
- [ ] Session management

### 6.3 Phase 3: Dashboard & Jobs (Week 3)
- [ ] Dashboard panel (bottom panel)
- [ ] Jobs TreeView panel
- [ ] Job list refresh
- [ ] Stop job functionality
- [ ] Job details display
- [ ] Dashboard navigation

### 6.4 Phase 4: Data Sources (Week 4)
- [ ] CSV upload dialog
- [ ] Table selection dialog
- [ ] Data source display in chat
- [ ] Session data isolation
- [ ] Clear data sources

### 6.5 Phase 5: Polish & Testing (Week 5)
- [ ] Error handling
- [ ] Loading indicators
- [ ] Notifications
- [ ] Documentation
- [ ] Testing (unit + integration)
- [ ] Package and publish

---

## 7. File Structure

```
ray-code-interpreter-vscode/
├── package.json                 # Extension manifest
├── tsconfig.json               # TypeScript config
├── src/
│   ├── extension.ts            # Extension entry point
│   ├── commands/
│   │   ├── execute.ts          # Execute commands
│   │   ├── generate.ts         # Generate commands
│   │   └── jobs.ts             # Job management commands
│   ├── panels/
│   │   ├── chatPanel.ts        # Chat webview panel
│   │   ├── dashboardPanel.ts   # Dashboard webview panel
│   │   └── jobsPanel.ts        # Jobs tree view panel
│   ├── services/
│   │   ├── backendClient.ts    # HTTP client for backend
│   │   ├── rayClient.ts        # Ray cluster client
│   │   └── sessionManager.ts   # Session management
│   ├── utils/
│   │   ├── config.ts           # Settings management
│   │   ├── logger.ts           # Logging utility
│   │   └── validation.ts       # Input validation
│   └── webviews/
│       ├── chat.html           # Chat UI
│       ├── dashboard.html      # Dashboard UI
│       └── styles.css          # Webview styles
├── backend/                    # Existing FastAPI backend
│   ├── main.py                 # FastAPI server
│   ├── agents.py               # Strands-agents implementation
│   └── requirements.txt        # Python dependencies
└── README.md                   # Documentation
```

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Command execution logic
- Backend client methods
- Session management
- Configuration validation

### 8.2 Integration Tests
- End-to-end code execution
- Code generation with agent
- Job management operations
- Data source handling

### 8.3 Manual Tests
- UI responsiveness
- Webview rendering
- Context menu actions
- Keyboard shortcuts

---

## 9. Dependencies

### 9.1 VSCode Extension
- `@types/vscode`: ^1.80.0
- `axios`: ^1.5.0
- `typescript`: ^5.0.0

### 9.2 Backend (Existing)
- FastAPI
- strands-agents
- boto3 (AWS SDK)
- requests

### 9.3 Ray Cluster (External - Not Included)

The extension works with any Ray cluster that provides:
- Ray Dashboard API (port 8265 by default)
- Job submission endpoint
- Ray version 2.x or higher

**Cluster Requirements**:
- Accessible HTTP endpoint for dashboard
- Network connectivity from user's machine
- Optional: ML packages (torch, numpy, etc.) if needed

**Note**: Cluster deployment and management are NOT part of this extension. Users must provide their own Ray cluster (local, AWS ECS, Kubernetes, etc.).

---

## 10. Constraints & Assumptions

### 10.1 Constraints
- Backend must be running locally or accessible via network
- Ray cluster must be deployed and accessible (not provided by extension)
- Ray cluster must expose dashboard API (port 8265 by default)
- AWS credentials must be configured for Bedrock access
- VSCode version >= 1.80.0

### 10.2 Assumptions
- Users have Python knowledge
- Users have AWS Bedrock access
- Users have deployed their own Ray cluster
- Backend is pre-configured and running
- Network connectivity is stable
- Ray cluster version is 2.x or higher

---

## 11. Future Enhancements

### 11.1 Phase 2 Features
- Inline code suggestions
- Code snippets library
- Multi-cluster support
- Collaborative sessions
- Code diff viewer
- Performance profiling

### 11.2 Advanced Features
- Jupyter notebook integration
- Git integration for code versioning
- Custom agent configurations
- Local Ray cluster support
- Code testing framework

---

## 12. Acceptance Criteria

### 12.1 Core Functionality
- ✅ Execute selected code successfully
- ✅ Execute file from explorer
- ✅ Generate code from natural language
- ✅ Display execution results
- ✅ View Ray dashboard in VSCode

### 12.2 Job Management
- ✅ List running jobs
- ✅ Stop jobs
- ✅ View job logs
- ✅ Auto-refresh job list

### 12.3 User Experience
- ✅ Intuitive UI
- ✅ Clear error messages
- ✅ Fast response times
- ✅ Stable operation

### 12.4 Documentation
- ✅ Complete README
- ✅ Configuration guide
- ✅ Troubleshooting section
- ✅ Example workflows

---

## 13. Glossary

| Term | Definition |
|------|------------|
| Agent | AI-powered code generation system using AWS Bedrock |
| Backend | FastAPI server handling code generation and execution |
| Ray Cluster | Distributed computing cluster for code execution |
| Session | Isolated execution context with data sources |
| Webview | VSCode UI component for custom HTML/CSS/JS |
| TreeView | VSCode UI component for hierarchical data |
| Command Palette | VSCode command search interface (Ctrl+Shift+P) |

---

## 14. References

- VSCode Extension API: https://code.visualstudio.com/api
- Ray Documentation: https://docs.ray.io/
- Strands-Agents: https://strandsagents.com/
- AWS Bedrock: https://aws.amazon.com/bedrock/
- FastAPI: https://fastapi.tiangolo.com/

---

**Document Version**: 1.0  
**Last Updated**: October 6, 2025  
**Status**: Draft for Review
