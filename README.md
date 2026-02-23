# Spark Code Interpreter - AWS Deployment

Complete Spark code interpretation system using AWS Bedrock AgentCore, Lambda, and EMR Serverless. Submit natural language queries that are converted to PySpark code, validated, and executed.

## Architecture

```
User/Application
    ↓ (JWT Token)
AgentCore Gateway (MCP)
    ↓
Wrapper Lambda
    ↓
Spark Supervisor Agent
    ↓
Code Generation Agent
    ↓
Spark Lambda (PySpark)
    ↓
S3 (Session-based Results)
```

## Quick Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete instructions.

### Prerequisites
- AWS CLI configured
- Docker with buildx support
- Python 3.11+
- bedrock-agentcore-starter-toolkit

### Deploy

**Option 1: One Command (Recommended)**
```bash
./scripts/deploy-all.sh
```

This deploys everything: agents, Docker image, and CloudFormation stack.

**Option 2: Step by Step**
```bash
# 1. Deploy agents
cd agent-code/spark-supervisor-agent && python3 agent_deployment.py
cd ../code-generation-agent && python3 agent_deployment.py

# 2. Deploy stack (builds Docker image + deploys CloudFormation)
./scripts/deploy-stack.sh

# 3. Add Gateway Target (manual via Console - see DEPLOYMENT_GUIDE.md)
```

### Test

```bash
# Via Lambda Console
{"prompt":"what is 7*10"}

# Or test script
./scripts/test-calculation.sh "what is 7*10"
```

## Configuration

| Component | Value |
|-----------|-------|
| Model | Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) |
| Wrapper Lambda Timeout | 900s (15 min) |
| Spark Lambda Timeout | 300s (5 min) |
| S3 Structure | `s3://spark-data-{account}-{region}/{session-id}/` |

## Key Features

✅ Natural language → PySpark code  
✅ Automatic validation & execution  
✅ S3 write support (automatic config)  
✅ Session-based storage  
✅ JWT authentication (Cognito)  
✅ MCP protocol support  
✅ EMR Serverless for large datasets  

## Directory Structure

```
.
├── agent-code/              # Bedrock agents
│   ├── spark-supervisor-agent/
│   └── code-generation-agent/
├── agent-wrapper/           # Wrapper Lambda code
├── cloudformation/          # Infrastructure templates
├── Docker/                  # Spark Lambda image
├── scripts/                 # Deployment scripts
├── config/                  # Configuration files
├── archive/                 # Historical docs
├── README.md               # This file
└── DEPLOYMENT_GUIDE.md     # Complete deployment guide
```

## Troubleshooting

**S3 Write Issues**: Check Lambda logs for JAR classpath
```bash
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

**Model Issues**: All components use Claude Sonnet 4.5 by default

**Gateway Timeout**: Gateway times out at ~30s but Lambda continues. Check S3 for results.

## Cost Estimate

~$0.01-$1.00 per query depending on complexity

## Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [archive/](archive/) - Development history and detailed notes

---

**Version**: 2.0.0 | **Model**: Claude Sonnet 4.5 | **Updated**: Dec 2025
