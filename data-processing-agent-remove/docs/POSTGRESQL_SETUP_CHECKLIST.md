# PostgreSQL Integration Setup Checklist

## Quick Reference for New Deployments

### 1. Infrastructure (AWS Console or IaC)

#### VPC Endpoints (in EMR VPC)
```bash
# CloudWatch Logs VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id <EMR_VPC_ID> \
  --service-name com.amazonaws.<region>.logs \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1> <subnet-2> <subnet-3> \
  --security-group-ids <EMR_SECURITY_GROUP> \
  --private-dns-enabled

# Secrets Manager VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id <EMR_VPC_ID> \
  --service-name com.amazonaws.<region>.secretsmanager \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1> <subnet-2> <subnet-3> \
  --security-group-ids <EMR_SECURITY_GROUP> \
  --private-dns-enabled
```

#### IAM Policy for EMR Role
```bash
# Add Secrets Manager permissions to EMR execution role
aws iam put-role-policy \
  --role-name EMRServerlessExecutionRole \
  --policy-name EMRSecretsManagerPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:<region>:<account>:secret:spark/postgres/*"
    }]
  }'
```

#### Upload JDBC Driver
```bash
# Download PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.8.jar

# Upload to S3
aws s3 cp postgresql-42.7.8.jar s3://<spark-bucket>/jars/
```

### 2. Backend Configuration

#### Update backend/settings.json
```json
{
  "spark": {
    "emr_application_id": "<standard-emr-app-id>",
    "emr_postgres_application_id": "<postgres-emr-app-id>",
    "supervisor_arn": "<spark-supervisor-agent-arn>"
  },
  "postgres": {
    "jdbc_driver_path": "s3://<spark-bucket>/jars/postgresql-42.7.8.jar",
    "connections": [
      {
        "name": "aurora",
        "secret_arn": "arn:aws:secretsmanager:<region>:<account>:secret:spark/postgres/<name>",
        "host": "<rds-endpoint>",
        "port": 5432,
        "database": "postgres",
        "auth_method": "user_password",
        "enabled": true
      }
    ]
  }
}
```

### 3. Code Deployment

#### Deploy Supervisor Agent
```bash
cd backend/spark-supervisor-agent
/path/to/bedrock-sdk/bin/python agent_deployment.py
```

#### Restart Backend
```bash
cd backend
pkill -f "uvicorn.*main:app"
/path/to/bedrock-sdk/bin/python -m uvicorn main:app --reload --port 8000 &
```

### 4. Verification

#### Test PostgreSQL Connection
```python
import requests, json, time

response = requests.post("http://localhost:8000/spark/generate", json={
    "prompt": "find top 10 products by order total",
    "session_id": f"test-{int(time.time())}",
    "framework": "spark",
    "execution_platform": "emr",
    "selected_postgres_tables": [{
        "connection_name": "aurora",
        "database": "postgres",
        "schema": "public",
        "table": "order_details",
        "jdbc_url": "jdbc:postgresql://<host>:5432/postgres",
        "auth_method": "user_password",
        "secret_arn": "<secret-arn>",
        "host": "<host>",
        "port": 5432,
        "columns": [
            {"name": "order_id", "type": "smallint"},
            {"name": "product_id", "type": "smallint"},
            {"name": "unit_price", "type": "real"},
            {"name": "quantity", "type": "smallint"},
            {"name": "discount", "type": "real"}
        ]
    }]
}, timeout=900)

result = response.json()
print(f"Success: {result.get('success')}")
print(f"Result: {result.get('result', {}).get('execution_result')}")
```

### 5. Required Environment Variables

**Current Setup (from conversation):**
- VPC ID: `vpc-0485dcc1f1d050b55`
- Subnets: `subnet-09cc990e2dd228cdc`, `subnet-006b1a09bd82fd9f7`, `subnet-016fb407bc2a3e4c0`
- Security Group: `sg-098a735e14f9f2953`
- S3 Bucket: `spark-data-260005718447-us-east-1`
- Region: `us-east-1`
- Account: `260005718447`

### 6. Key Files Modified

**Backend:**
- `backend/main.py` - Added `selected_postgres_tables` to request model (line 1201)
- `backend/main.py` - Updated to read PostgreSQL tables from request (line 1329)
- `backend/main.py` - Backend selects PostgreSQL EMR app and JDBC driver (line 1353-1356)
- `backend/settings.json` - Added `emr_postgres_application_id` and `jdbc_driver_path`

**Supervisor Agent:**
- `backend/spark-supervisor-agent/spark_supervisor_agent.py` - Updated EMR app ID retrieval (line 508)
- `backend/spark-supervisor-agent/spark_supervisor_agent.py` - Added JDBC driver to spark-submit (line 524-525)

### 7. Troubleshooting Commands

```bash
# Check VPC endpoints
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id>

# Check IAM role policies
aws iam list-role-policies --role-name EMRServerlessExecutionRole
aws iam get-role-policy --role-name EMRServerlessExecutionRole --policy-name EMRSecretsManagerPolicy

# Check EMR application
aws emr-serverless get-application --application-id <app-id>

# Check recent EMR jobs
aws emr-serverless list-job-runs --application-id <app-id> --max-results 5

# Check EMR job logs
aws s3 ls s3://<bucket>/logs/emr/applications/<app-id>/jobs/<job-id>/SPARK_DRIVER/
```

### 8. Success Criteria

✅ Backend settings.json has all PostgreSQL configuration  
✅ VPC endpoints for CloudWatch Logs and Secrets Manager exist and are available  
✅ EMR execution role has Secrets Manager permissions  
✅ PostgreSQL JDBC driver uploaded to S3  
✅ Supervisor agent deployed with updated code  
✅ Test request returns success with JDBC and Secrets Manager usage  
✅ EMR job completes successfully without ClassNotFoundException  

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-03
