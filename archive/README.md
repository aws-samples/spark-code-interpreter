# Archive

This directory contains historical documentation and development notes from the project evolution.

## Recently Archived (Dec 2025)

### Documentation Directory (Old Architecture)
- **ARCHITECTURE.md** - Old architecture with ALB and backend Lambda (FastAPI)
- **CHANGES.md** - Changes from old deployment (references old account IDs: 260005718447, 025523569182)
- **CONFIGURATION.md** - Configuration for old architecture (references backend/config_snowflake.py)
- **DEPLOYMENT.md** - Old deployment process with ALB setup
- **TROUBLESHOOTING.md** - Troubleshooting for old architecture components

**Why archived**: Current architecture uses:
- AgentCore Gateway (not ALB)
- Cognito JWT authentication (not ALB-based auth)
- Wrapper Lambda inline in CloudFormation (not separate backend Lambda)
- Session-based S3 storage
- MCP protocol support

### Scripts Directory Cleanup
- **scripts-intermediate/** - Intermediate and redundant deployment/test scripts (27 total)
  - Gateway-specific scripts (add-gateway-target.sh, ask-gateway.sh, etc.)
  - Backend/ALB deployment scripts (deploy-backend.sh, update-alb-access.sh)
  - Intermediate test scripts (quick-test.sh, simple-test.sh, etc.)
  - Authentication scripts (get-client-credentials.sh, get-user-token.sh)
  - Update/config scripts (update-config.sh, update-s3-config.sh)
  - Complex deployment scripts (deploy-complete-stack.sh, deploy-all.sh)
  - Infrastructure test script (test-complete-stack.sh)
  - **deploy-agent-wrapper.sh** - Redundant (wrapper Lambda in CloudFormation)
  - **rebuild-spark-lambda.sh** - Redundant (Docker build now in deploy-stack.sh)
  - Superseded by 3 essential scripts in root scripts/ directory

### Backend Development Directory
- **backend-development/** - Complete backend/backend directory with development versions of agents
  - Contains older versions of spark-supervisor-agent and code-generation-agent
  - Includes test files, deployment scripts, and configuration backups
  - Superseded by root-level agent-code/ directory

### Deployment Documentation
- **FINAL_DEPLOYMENT_SUMMARY.md** - Complete summary of all changes (v2.0.0)
- **CHECKPOINT_SUMMARY.md** - Development checkpoint summary
- **QUICK_DEPLOY.md** - Quick deployment guide (superseded by DEPLOYMENT_GUIDE.md)
- **QUICK_START.md** - Quick start guide (superseded by README.md)
- **ONE_COMMAND_DEPLOY.md** - One-command deployment attempt
- **START_HERE.md** - Original getting started guide

### Technical Documentation
- **S3_WRITE_FIX.md** - S3 write configuration fix details
- **CLOUDFORMATION_UPDATES_COMPLETE.md** - CloudFormation update summary
- **COMPLETE_CHANGES_CHECKLIST.md** - Detailed change checklist
- **PROJECT_STRUCTURE.md** - Project structure documentation

### Configuration
- **GATEWAY_TARGET_CONFIG.md** - Gateway Target configuration details
- **WHY_NO_CLOUDFORMATION_TARGETS.md** - Explanation of manual Gateway Target setup
- **HOW_TO_SEND_PAYLOAD.md** - Payload format guide
- **TESTING_GUIDE.md** - Testing procedures
- **LAMBDA_TOOL_SCHEMA.json** - Lambda tool schema definition

## Previously Archived

### Deployment Scripts
- **deploy-spark-supervisor-agent.sh** - Agent deployment script
- **fix-lambda-image-final.sh** - Lambda image fix script
- **fix-lambda-image-platform.sh** - Platform-specific fix
- **redeploy-with-new-model.sh** - Model update script
- **update-agent-model.sh** - Agent model update

### Status Documents
- **DEPLOYMENT_READY.md** - Deployment readiness checklist
- **DEPLOYMENT_SUMMARY.md** - Deployment summary
- **DEPLOY_AGENT_INSTRUCTIONS.md** - Agent deployment instructions
- **DEPLOY_WITH_VALID_CREDENTIALS.md** - Credential setup guide
- **EXPOSE_AGENT_VIA_GATEWAY.md** - Gateway exposure guide
- **ADD_AGENT_TARGET.md** - Adding agent targets

### Implementation Notes
- **AGENTCORE_GATEWAY_IMPLEMENTATION.md** - Gateway implementation details
- **CLOUDFORMATION_AND_DOCKER_RELATIONSHIP.md** - CloudFormation/Docker relationship
- **COMPLETE_FINAL_SUMMARY.md** - Final implementation summary
- **COMPLETE_SETUP_SUMMARY.md** - Setup summary
- **CURRENT_STATUS.md** - Status snapshot
- **FINAL_IMPLEMENTATION_SUMMARY.md** - Implementation summary
- **FINAL_S3_STRUCTURE.md** - S3 structure documentation
- **FINAL_STATUS.md** - Final status
- **FINAL_WORKING_STATUS.md** - Working status confirmation
- **GATEWAY_MIGRATION_SUMMARY.md** - Gateway migration notes
- **GATEWAY_WORKING_CONFIRMED.md** - Gateway confirmation
- **STABLE_PACKAGE_COMPLETE.md** - Stable package notes
- **SUCCESS.md** - Success milestone
- **VERIFICATION_REPORT.md** - Verification report
- **WRAPPER_LAMBDA_DEPLOYED.md** - Wrapper Lambda deployment

### Issue Fixes
- **IMPORTANT_S3_FIX_REQUIRED.md** - S3 fix requirements
- **MODEL_UPDATE_REQUIRED.md** - Model update requirements
- **NEW_S3_STRUCTURE.md** - New S3 structure proposal
- **NO_TOOLS_FIX.md** - Tools fix
- **S3_FIX_APPLIED.md** - S3 fix application
- **S3_RESULTS_LOCATION.md** - S3 results location
- **SECRET_HASH_FIX.md** - Secret hash fix
- **TOKEN_FIX.md** - Token fix

## Current Active Documentation

For current documentation, see the root directory:
- **README.md** - Project overview and quick start
- **DEPLOYMENT_GUIDE.md** - Complete deployment instructions

## Purpose

These files are preserved for:
- Historical reference
- Understanding project evolution
- Troubleshooting similar issues
- Learning from development process

---

**Last Updated**: Dec 2025
