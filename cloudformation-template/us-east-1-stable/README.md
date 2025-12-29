

# Spark Code Interpreter - Stable us-east-1 Deployment Package

This is a complete, tested, and stable deployment package for the Spark Code Interpreter system in AWS us-east-1 region.

## 🎯 What's Included

This package contains everything needed to deploy a fully functional Spark Code Interpreter system:

- **CloudFormation Templates**: Infrastructure as Code for all AWS resources
- **Agent Code**: Bedrock AgentCore agents (Spark Supervisor, Code Generation)
- **Backend Code**: FastAPI backend with all bug fixes applied
- **Deployment Scripts**: Automated deployment and configuration
- **Documentation**: Complete setup and troubleshooting guides

## ✅ Bug Fixes Incorporated

All known issues have been fixed in this stable release:

1. **Lambda Function Name**: Corrected from `sparkOnLambda-spark-code-interpreter` to `dev-spark-on-lambda`
2. **EMR Application ID**: Updated to use correct application ID format
3. **Account ID**: Fixed cross-account role issues (hardcoded old account removed)
4. **EMR Execution Role**: Corrected ARN to use current account
5. **S3 Bucket**: Updated to use account-specific bucket naming
6. **Configuration Management**: Centralized config with environment variable support
7. **Bedrock Model**: Configured to use Claude Haiku 4.5 to avoid throttling

## 📋 Prerequisites

Before deploying, ensure you have:

- **AWS Account** with appropriate permissions
- **AWS CLI** v2.x installed and configured
- **Docker** installed (for building Lambda layers)
- **Python 3.11+** installed
- **jq** installed (for JSON processing)
- **bedrock-agentcore CLI** installed: `pip install bedrock-agentcore-starter-toolkit`

### AWS Permissions Required

Your AWS user/role needs:
- CloudFormation full access
- IAM role creation
- S3 bucket creation
- Lambda function management
- EMR Serverless management
- Bedrock AgentCore access
- EC2 VPC/Subnet read access

## 🚀 Quick Start Deployment

### Step 1: Clone and Navigate

```bash
cd us-east-1-stable
```

### Step 2: Set Environment Variables

```bash
export AWS_REGION=us-east-1
export ENVIRONMENT=dev  # or prod
export AWS_PROFILE=your-profile  # if using named profiles
```

### Step 3: Deploy Infrastructure

```bash
cd scripts
chmod +x deploy-complete-stack.sh
./deploy-complete-stack.sh
```

This will:
- Create S3 bucket for Spark data
- Deploy Lambda functions
- Create EMR Serverless application
- Set up IAM roles with correct permissions
- Deploy Application Load Balancer
- Generate configuration files

### Step 4: Deploy AgentCore Agents

```bash
# Deploy Code Generation Agent
cd ../agent-code/code-generation-agent
bedrock-agentcore deploy --region us-east-1

# Deploy Spark Supervisor Agent
cd ../spark-supervisor-agent
bedrock-agentcore deploy --region us-east-1
```

Save the agent ARNs from the deployment output.

### Step 5: Update Configuration

Edit `config/deployment-config.json` with the agent ARNs:

```json
{
  "code_gen_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/...",
  "spark_supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/..."
}
```

### Step 6: Deploy Backend

```bash
cd ../backend
./deploy-backend.sh
```

### Step 7: Test Deployment

```bash
cd ../scripts
./test-deployment.sh
```

## 📁 Directory Structure

```
us-east-1-stable/
├── README.md                          # This file
├── cloudformation/
│   └── spark-complete-stack.yml       # Main CloudFormation template
├── agent-code/
│   ├── spark-supervisor-agent/        # Spark orchestration agent
│   │   ├── spark_supervisor_agent.py  # Main agent code (all fixes applied)
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── .bedrock_agentcore.yaml
│   └── code-generation-agent/         # Code generation agent
│       ├── agents.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── .bedrock_agentcore.yaml
├── backend/
│   ├── main.py                        # FastAPI backend
│   ├── config_snowflake.py            # Configuration (all fixes applied)
│   ├── requirements.txt
│   └── deploy-backend.sh
├── scripts/
│   ├── deploy-complete-stack.sh       # Main deployment script
│   ├── test-deployment.sh             # Testing script
│   ├── cleanup.sh                     # Cleanup script
│   └── update-config.sh               # Configuration update script
├── config/
│   ├── deployment-config.json         # Generated during deployment
│   └── example-config.json            # Example configuration
└── docs/
    ├── DEPLOYMENT.md                  # Detailed deployment guide
    ├── CONFIGURATION.md               # Configuration reference
    ├── TROUBLESHOOTING.md             # Common issues and solutions
    └── ARCHITECTURE.md                # System architecture
```

## 🔧 Configuration

### Key Configuration Files

1. **deployment-config.json**: Generated during deployment, contains all resource IDs
2. **config_snowflake.py**: Backend configuration with environment variable support
3. **.bedrock_agentcore.yaml**: Agent deployment configuration

### Environment Variables

The system supports these environment variables:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# Bedrock Configuration
BEDROCK_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0

# Spark Configuration
DATA_BUCKET=spark-data-ACCOUNT-us-east-1
SPARK_LAMBDA_FUNCTION=dev-spark-on-lambda
EMR_APPLICATION_ID=your-emr-app-id

# Agent ARNs
CODE_GEN_AGENT_ARN=arn:aws:bedrock-agentcore:...
SPARK_SUPERVISOR_ARN=arn:aws:bedrock-agentcore:...
```

## 🧪 Testing

### Basic Health Check

```bash
curl http://your-alb-url/health
```

### Test Spark Code Generation

```bash
curl -X POST http://your-alb-url/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 100 rows",
    "session_id": "test-session",
    "execution_platform": "lambda"
  }'
```

### Check Logs

```bash
# Backend logs
aws logs tail /aws/lambda/dev-spark-supervisor-invocation --follow

# Agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-*/DEFAULT --follow

# Lambda execution logs
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Bedrock Throttling

**Symptom**: `serviceUnavailableException: Bedrock is unable to process your request`

**Solution**:
- Wait 10-15 minutes between requests
- Request service quota increase via AWS Support
- Use a different Bedrock model with higher quotas

#### 2. Lambda Function Not Found

**Symptom**: `ResourceNotFoundException: Function not found`

**Solution**:
- Verify Lambda function name in config matches deployed function
- Check CloudFormation stack outputs
- Redeploy Lambda function

#### 3. EMR Cross-Account Role Error

**Symptom**: `AccessDeniedException: Cross-account pass role is not allowed`

**Solution**:
- Verify EMR execution role ARN uses correct account ID
- Check IAM role trust policy
- Update config with correct role ARN

#### 4. S3 Access Denied

**Symptom**: `AccessDenied` when writing to S3

**Solution**:
- Verify S3 bucket name matches account ID
- Check IAM role policies include S3 permissions
- Ensure bucket exists in correct region

### Getting Help

1. Check logs in CloudWatch
2. Review `docs/TROUBLESHOOTING.md` for detailed solutions
3. Verify all configuration values are correct
4. Ensure all prerequisites are installed

## 📊 Monitoring

### CloudWatch Dashboards

The deployment creates CloudWatch dashboards for:
- Lambda function metrics
- EMR job execution
- Agent invocation metrics
- API Gateway metrics

### Key Metrics to Monitor

- **Lambda Duration**: Should be < 300 seconds
- **EMR Job Success Rate**: Should be > 95%
- **Agent Invocation Errors**: Should be < 5%
- **S3 Bucket Size**: Monitor for cost optimization

## 🔄 Updates and Maintenance

### Updating Agent Code

```bash
cd agent-code/spark-supervisor-agent
# Make changes to spark_supervisor_agent.py
bedrock-agentcore deploy --region us-east-1
```

### Updating Backend

```bash
cd backend
# Make changes to main.py or config_snowflake.py
./deploy-backend.sh
```

### Updating Infrastructure

```bash
cd scripts
# Modify cloudformation/spark-complete-stack.yml
./deploy-complete-stack.sh
```

## 🗑️ Cleanup

To remove all resources:

```bash
cd scripts
./cleanup.sh
```

This will:
- Delete CloudFormation stack
- Remove S3 bucket (after emptying)
- Delete AgentCore agents
- Clean up logs

## 📝 Version History

### v1.0.0 (Current - Stable)
- Initial stable release
- All bug fixes incorporated
- Complete documentation
- Tested deployment process
- Production-ready

### Key Fixes from Previous Versions
- Lambda function name correction
- EMR application ID fix
- Account ID hardcoding removed
- S3 bucket naming standardized
- Configuration management improved
- Bedrock model optimization

## 🤝 Support

For issues or questions:
1. Check `docs/TROUBLESHOOTING.md`
2. Review CloudWatch logs
3. Verify configuration values
4. Check AWS service quotas

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

This stable release incorporates fixes and improvements from extensive testing and debugging sessions.

---

**Ready to deploy?** Start with Step 1 of the Quick Start guide above!
