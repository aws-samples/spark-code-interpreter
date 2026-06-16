# Project Structure

## Root Directory - Active Documentation

### Primary Documentation
- **README.md** - Main project overview and quick start
- **CHECKPOINT_SUMMARY.md** - Complete summary of all changes
- **DEPLOYMENT_GUIDE.md** - Step-by-step deployment for new accounts
- **START_HERE.md** - Quick start guide

### Technical Documentation
- **CLOUDFORMATION_UPDATES_COMPLETE.md** - CloudFormation stack changes
- **COMPLETE_CHANGES_CHECKLIST.md** - Detailed checklist of all changes
- **S3_WRITE_FIX.md** - S3 write configuration fix
- **GATEWAY_TARGET_CONFIG.md** - Gateway Target configuration
- **WHY_NO_CLOUDFORMATION_TARGETS.md** - Manual Gateway Target explanation

### Operational Guides
- **ONE_COMMAND_DEPLOY.md** - Automated deployment script
- **QUICK_DEPLOY.md** - Quick deployment guide
- **QUICK_START.md** - Quick start guide
- **TESTING_GUIDE.md** - Testing procedures
- **HOW_TO_SEND_PAYLOAD.md** - Payload format guide

## Code Structure

```
.
├── agent-code/                      # Bedrock Agent definitions
│   ├── code-generation-agent/       # Code generation agent
│   │   ├── config.py
│   │   └── deployment_config_helper.py
│   └── spark-supervisor-agent/      # Spark supervisor agent
│       ├── config.py
│       └── deployment_config_helper.py
│
├── agent-wrapper/                   # Wrapper Lambda (natural language)
│   └── agent_wrapper.py             # Main Lambda handler
│
├── cloudformation/                  # Infrastructure as Code
│   └── spark-complete-stack.yml     # Complete CloudFormation stack
│
├── Docker/                          # Spark Lambda container
│   ├── Dockerfile                   # Container definition
│   ├── sparkLambdaHandler.py        # Lambda handler for Spark
│   ├── download_jars.sh             # JAR download script
│   ├── spark-class                  # Spark class wrapper
│   ├── log4j.properties             # Logging configuration
│   └── requirements.txt             # Python dependencies
│
├── scripts/                         # Deployment and testing scripts
│   ├── deploy-all-automated.sh      # One-command deployment
│   ├── deploy-agent-wrapper.sh      # Deploy wrapper Lambda
│   ├── get-user-token.sh            # Get Cognito JWT token
│   ├── ask-gateway.sh               # Test Gateway invocation
│   ├── test-s3-structure.sh         # Test S3 session structure
│   ├── test-agent-direct.sh         # Test agent directly
│   ├── test-mcp-gateway.sh          # Test MCP protocol
│   ├── test-complete-stack.sh       # Test complete stack
│   ├── list-gateway-tools.sh        # List Gateway tools
│   ├── check-gateway-status.sh      # Check Gateway status
│   ├── add-gateway-target.sh        # Add Gateway Target
│   └── add-agent-target.sh          # Add agent as target
│
├── config/                          # Configuration files
│   └── deployment-config.json       # Deployment configuration
│
├── docs/                            # Additional documentation
│
├── backend/                         # Backend code (if applicable)
│
└── archive/                         # Historical documentation
    ├── README.md                    # Archive explanation
    └── [24 archived files]          # Historical status files
```

## Key Files by Purpose

### Deployment
1. **cloudformation/spark-complete-stack.yml** - Main infrastructure template
2. **scripts/deploy-all-automated.sh** - Automated deployment
3. **DEPLOYMENT_GUIDE.md** - Complete deployment instructions

### Lambda Functions
1. **agent-wrapper/agent_wrapper.py** - Wrapper Lambda (natural language → agent)
2. **Docker/sparkLambdaHandler.py** - Spark Lambda (PySpark execution)

### Agents
1. **agent-code/spark-supervisor-agent/** - Orchestrates code generation and execution
2. **agent-code/code-generation-agent/** - Generates PySpark code

### Testing
1. **scripts/test-*.sh** - Various test scripts
2. **TESTING_GUIDE.md** - Testing procedures

### Configuration
1. **GATEWAY_TARGET_CONFIG.md** - Gateway Target schema
2. **S3_WRITE_FIX.md** - S3 configuration
3. **config/deployment-config.json** - Deployment settings

## Documentation Hierarchy

### Level 1: Getting Started
Start here for new users:
1. **README.md** - Project overview
2. **START_HERE.md** - Quick start
3. **QUICK_START.md** - Minimal setup

### Level 2: Deployment
For deploying in new accounts:
1. **DEPLOYMENT_GUIDE.md** - Complete guide
2. **ONE_COMMAND_DEPLOY.md** - Automated deployment
3. **QUICK_DEPLOY.md** - Quick deployment

### Level 3: Technical Details
For understanding the system:
1. **CHECKPOINT_SUMMARY.md** - All changes summary
2. **CLOUDFORMATION_UPDATES_COMPLETE.md** - CloudFormation details
3. **COMPLETE_CHANGES_CHECKLIST.md** - Detailed checklist

### Level 4: Configuration
For specific configurations:
1. **GATEWAY_TARGET_CONFIG.md** - Gateway configuration
2. **S3_WRITE_FIX.md** - S3 configuration
3. **WHY_NO_CLOUDFORMATION_TARGETS.md** - Manual steps explanation

### Level 5: Operations
For testing and operations:
1. **TESTING_GUIDE.md** - Testing procedures
2. **HOW_TO_SEND_PAYLOAD.md** - Payload formats
3. **scripts/** - Operational scripts

## Archive Structure

The `archive/` folder contains 24 historical documentation files:
- Status updates during development
- Incremental fix documentation
- Working confirmations
- Historical summaries

See `archive/README.md` for details.

## File Naming Conventions

- **UPPERCASE.md** - Documentation files
- **lowercase.py** - Python source code
- **lowercase.sh** - Shell scripts
- **lowercase.yml** - YAML configuration
- **lowercase.json** - JSON configuration

## Maintenance

### Adding New Documentation
- Place in root directory if active/current
- Update this file with new entry
- Update README.md if it's a primary document

### Archiving Old Documentation
- Move to `archive/` folder
- Update `archive/README.md`
- Remove from this file

### Updating Code
- Update source files in respective directories
- Update relevant documentation
- Test changes before committing

## Quick Reference

### Deploy Everything
```bash
./scripts/deploy-all-automated.sh
```

### Test Wrapper Lambda
```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"calculate 10 + 20"}' \
  /tmp/test.json
```

### Check S3 Results
```bash
aws s3 ls s3://spark-data-{account}-{region}/ --recursive
```

### Get Cognito Token
```bash
./scripts/get-user-token.sh user@example.com password
```

### Test Gateway
```bash
./scripts/ask-gateway.sh "calculate 10 + 20"
```

## Documentation Status

✅ **Current and Complete**

All documentation is up-to-date as of December 2024. Historical files have been archived for reference.

## Next Steps

1. Review **README.md** for project overview
2. Follow **DEPLOYMENT_GUIDE.md** for deployment
3. Use **TESTING_GUIDE.md** for testing
4. Reference **CHECKPOINT_SUMMARY.md** for technical details
