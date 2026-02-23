# Ray Backend - Consolidated Agent Structure

This folder contains all backend agents for the Ray Code Interpreter system.

## Structure

```
backend/
├── code-generation-agent/     # Code Generation Agent
│   ├── agents.py              # Agent implementation
│   ├── agent_deployment.py    # Deployment script
│   ├── requirements.txt       # Python dependencies
│   └── .bedrock_agentcore.yaml # AgentCore configuration
│
├── supervisor-agent/          # Supervisor Agent
│   ├── supervisor_agents.py   # Agent implementation
│   ├── agent_deployment.py    # Deployment script
│   ├── requirements.txt       # Python dependencies
│   └── .bedrock_agentcore.yaml # AgentCore configuration
│
└── main.py                    # FastAPI backend server

```

## Agents

### 1. Code Generation Agent
- **Location**: `code-generation-agent/`
- **Purpose**: Generates Ray code from natural language prompts
- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9`
- **Model**: `us.anthropic.claude-sonnet-4-20250514-v1:0`

### 2. Supervisor Agent
- **Location**: `supervisor-agent/`
- **Purpose**: Orchestrates code generation and validation with retry logic (up to 5 attempts)
- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky`
- **Model**: `us.anthropic.claude-sonnet-4-20250514-v1:0`

## Deployment

### Deploy Code Generation Agent
```bash
cd code-generation-agent
python agent_deployment.py
```

### Deploy Supervisor Agent
```bash
cd supervisor-agent
python agent_deployment.py
```

### Start FastAPI Backend
```bash
python -m uvicorn main:app --port 8000
```

## Architecture

```
Backend (FastAPI)
    ↓
Supervisor Agent (AgentCore Runtime)
    ↓
Code Generation Agent (AgentCore Runtime)
    ↓
MCP Gateway → Lambda → Ray Cluster
```

## Validation Flow

1. Supervisor receives request
2. Calls Code Generation Agent to generate Ray code
3. Extracts clean Python code
4. Validates code via MCP Gateway → Lambda → Ray Cluster
5. If validation fails, retries up to 5 times with error feedback
6. Returns validated code or error after max attempts
