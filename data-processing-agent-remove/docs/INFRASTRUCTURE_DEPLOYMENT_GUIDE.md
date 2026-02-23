# Infrastructure Deployment Guide - PostgreSQL Integration

**Purpose:** Comprehensive guide for deploying PostgreSQL integration infrastructure from scratch  
**Date:** 2025-10-30  
**Status:** Reference for future automation script

---

## PREREQUISITES

### AWS Resources Required:
- Aurora PostgreSQL cluster (existing or new)
- VPC with private subnets
- NAT Gateway for internet access
- Security groups configured
- IAM roles with appropriate permissions
- S3 bucket for Spark data

### Local Requirements:
- AWS CLI configured
- PostgreSQL JDBC driver JAR file
- Python 3.12+ with conda
- bedrock-sdk conda environment

---

## DEPLOYMENT STEPS

### STEP 1: Aurora PostgreSQL Setup

#### 1.1 Create Aurora PostgreSQL Cluster (if not exists)
```bash
aws rds create-db-cluster \
  --db-cluster-identifier pg-database \
  --engine aurora-postgresql \
  --engine-version 16.8 \
  --master-username postgres \
  --master-user-password <SECURE_PASSWORD> \
  --vpc-security-group-ids sg-098a735e14f9f2953 \
  --db-subnet-group-name default-vpc-0485dcc1f1d050b55 \
  --serverless-v2-scaling-configuration MinCapacity=2.0,MaxCapacity=10.0 \
  --enable-iam-database-authentication \
  --enable-http-endpoint \
  --storage-encrypted \
  --region us-east-1
```

#### 1.2 Create Database Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier pg-database-instance-1 \
  --db-cluster-identifier pg-database \
  --db-instance-class db.serverless \
  --engine aurora-postgresql \
  --region us-east-1
```

#### 1.3 Create Application User
```sql
-- Connect to Aurora as master user
CREATE USER "pg-spark" WITH PASSWORD 'Pg@spark';
GRANT CONNECT ON DATABASE postgres TO "pg-spark";
GRANT USAGE ON SCHEMA public TO "pg-spark";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "pg-spark";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "pg-spark";
```

**Outputs to Capture:**
- Cluster endpoint: `pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com`
- Reader endpoint: `pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com`
- Port: `5432`
- VPC ID: `vpc-0485dcc1f1d050b55`
- Security Group: `sg-098a735e14f9f2953`

---

### STEP 2: VPC and Network Configuration

#### 2.1 Verify Private Subnets
```bash
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=vpc-0485dcc1f1d050b55" \
            "Name=map-public-ip-on-launch,Values=false" \
  --query 'Subnets[*].[SubnetId,AvailabilityZone,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table \
  --region us-east-1
```

**Expected Output:**
- subnet-006b1a09bd82fd9f7 (us-east-1a) - default-private-subnet-1a
- subnet-016fb407bc2a3e4c0 (us-east-1b) - default-private-subnet-1b
- subnet-09cc990e2dd228cdc (us-east-1c) - default-private-subnet-1c

#### 2.2 Check NAT Gateway
```bash
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=vpc-0485dcc1f1d050b55" \
  --query 'NatGateways[*].[NatGatewayId,State,SubnetId]' \
  --output table \
  --region us-east-1
```

**If no NAT Gateway exists, create one:**
```bash
# 1. Allocate Elastic IP
EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --region us-east-1 --query 'AllocationId' --output text)

# 2. Create NAT Gateway in public subnet
NAT_GW=$(aws ec2 create-nat-gateway \
  --subnet-id subnet-0ffcc9c369d011e54 \
  --allocation-id $EIP_ALLOC \
  --region us-east-1 \
  --query 'NatGateway.NatGatewayId' \
  --output text)

# 3. Wait for NAT Gateway to be available
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW --region us-east-1

# 4. Update route table for private subnets
ROUTE_TABLE=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-0485dcc1f1d050b55" \
            "Name=association.subnet-id,Values=subnet-006b1a09bd82fd9f7" \
  --query 'RouteTables[0].RouteTableId' \
  --output text \
  --region us-east-1)

aws ec2 create-route \
  --route-table-id $ROUTE_TABLE \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW \
  --region us-east-1
```

#### 2.3 Verify Security Group Rules
```bash
aws ec2 describe-security-groups \
  --group-ids sg-098a735e14f9f2953 \
  --query 'SecurityGroups[0].IpPermissions' \
  --region us-east-1
```

**Required Rules:**
- Inbound: Port 5432 from same security group (self-referencing)
- Outbound: All traffic (default)

---

### STEP 3: S3 and Secrets Manager Setup

#### 3.1 Upload PostgreSQL JDBC Driver
```bash
# Download driver (if not already downloaded)
wget https://jdbc.postgresql.org/download/postgresql-42.7.8.jar

# Upload to S3
aws s3 cp postgresql-42.7.8.jar \
  s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar \
  --region us-east-1

# Verify upload
aws s3 ls s3://spark-data-260005718447-us-east-1/jars/ --region us-east-1
```

**Output to Capture:**
- JDBC Driver Path: `s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar`

#### 3.2 Create Secrets Manager Secret
```bash
SECRET_ARN=$(aws secretsmanager create-secret \
  --name spark/postgres/aurora-prod \
  --description "Aurora PostgreSQL connection for Spark" \
  --secret-string '{
    "connection_name": "aurora-prod",
    "host": "pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "postgres",
    "username": "pg-spark",
    "password": "Pg@spark",
    "jdbc_url": "jdbc:postgresql://pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres"
  }' \
  --region us-east-1 \
  --query 'ARN' \
  --output text)

echo "Secret ARN: $SECRET_ARN"
```

**Output to Capture:**
- Secret ARN: `arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod-ltLn9I`

#### 3.3 Enable Automatic Rotation (Optional)
```bash
# Create rotation Lambda function first (separate process)
# Then enable rotation:
aws secretsmanager rotate-secret \
  --secret-id spark/postgres/aurora-prod \
  --rotation-lambda-arn <ROTATION_LAMBDA_ARN> \
  --rotation-rules AutomaticallyAfterDays=30 \
  --region us-east-1
```

---

### STEP 4: EMR Serverless Application Setup

#### 4.1 Create VPC-Enabled EMR Application for PostgreSQL
```bash
EMR_APP_ID=$(aws emr-serverless create-application \
  --name spark-postgres-interpreter-app \
  --release-label emr-7.0.0 \
  --type SPARK \
  --architecture X86_64 \
  --initial-capacity '{
    "DRIVER": {
      "workerCount": 1,
      "workerConfiguration": {
        "cpu": "2vCPU",
        "memory": "4GB",
        "disk": "20GB"
      }
    },
    "EXECUTOR": {
      "workerCount": 2,
      "workerConfiguration": {
        "cpu": "4vCPU",
        "memory": "8GB",
        "disk": "20GB"
      }
    }
  }' \
  --maximum-capacity '{
    "cpu": "400vCPU",
    "memory": "1000GB",
    "disk": "400TB"
  }' \
  --auto-start-configuration '{"enabled": true}' \
  --auto-stop-configuration '{"enabled": true, "idleTimeoutMinutes": 15}' \
  --network-configuration '{
    "subnetIds": [
      "subnet-006b1a09bd82fd9f7",
      "subnet-016fb407bc2a3e4c0",
      "subnet-09cc990e2dd228cdc"
    ],
    "securityGroupIds": ["sg-098a735e14f9f2953"]
  }' \
  --region us-east-1 \
  --query 'applicationId' \
  --output text)

echo "EMR PostgreSQL Application ID: $EMR_APP_ID"
```

#### 4.2 Configure CloudWatch Logging
```bash
aws emr-serverless update-application \
  --application-id $EMR_APP_ID \
  --monitoring-configuration '{
    "cloudWatchLoggingConfiguration": {
      "enabled": true,
      "logTypes": {
        "SPARK_DRIVER": ["stdout", "stderr"],
        "SPARK_EXECUTOR": ["stdout", "stderr"]
      }
    },
    "managedPersistenceMonitoringConfiguration": {
      "enabled": true
    }
  }' \
  --region us-east-1
```

**Output to Capture:**
- EMR PostgreSQL Application ID: `00g0oddl52n83r09`

---

### STEP 5: IAM Role Configuration

#### 5.1 Get EMR Execution Role
```bash
# Typically created automatically, or use existing role
EMR_ROLE_ARN="arn:aws:iam::260005718447:role/EMRServerlessExecutionRole"
```

#### 5.2 Add Secrets Manager Permissions
```bash
# Create policy document
cat > postgres-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/*"
    },
    {
      "Sid": "JDBCDriverAccess",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::spark-data-260005718447-us-east-1/jars/*"
    }
  ]
}
EOF

# Attach policy to role
aws iam put-role-policy \
  --role-name EMRServerlessExecutionRole \
  --policy-name PostgreSQLAccess \
  --policy-document file://postgres-policy.json \
  --region us-east-1
```

#### 5.3 Verify Role Permissions
```bash
aws iam get-role-policy \
  --role-name EMRServerlessExecutionRole \
  --policy-name PostgreSQLAccess \
  --region us-east-1
```

---

### STEP 6: Backend Configuration

#### 6.1 Update `backend/config.py`
Add PostgreSQL configuration to `DEFAULT_CONFIG`:
```python
"postgres": {
    "connections": [
        {
            "name": "aurora-prod",
            "secret_arn": "<SECRET_ARN_FROM_STEP_3.2>",
            "description": "Production Aurora PostgreSQL 16.8",
            "enabled": True
        }
    ],
    "default_connection": "aurora-prod",
    "jdbc_driver_path": "<JDBC_DRIVER_PATH_FROM_STEP_3.1>",
    "secrets_manager_prefix": "spark/postgres/",
    "connection_timeout": 10,
    "query_timeout": 30,
    "use_dedicated_emr": True
}
```

Update Spark configuration:
```python
"spark": {
    ...
    "emr_postgres_application_id": "<EMR_APP_ID_FROM_STEP_4.1>",
    ...
}
```

#### 6.2 Install Dependencies
```bash
cd backend
conda run -n bedrock-sdk pip install psycopg2-binary==2.9.9
```

#### 6.3 Create `postgres_metadata.py`
Copy the implementation from `POSTGRES_IMPLEMENTATION_LOG.md`

#### 6.4 Update `main.py`
Add PostgreSQL endpoints (see implementation log)

---

### STEP 7: Agent Deployment

#### 7.1 Deploy Spark Supervisor Agent
```bash
cd backend/spark-supervisor-agent
conda run -n bedrock-sdk python agent_deployment.py
```

**Expected Output:**
- Deployment time: ~45-60 seconds
- Agent ARN: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR`

#### 7.2 Verify Deployment
```bash
aws bedrock-agentcore describe-agent-runtime \
  --agent-runtime-arn <AGENT_ARN> \
  --region us-east-1
```

---

### STEP 8: Testing and Validation

#### 8.1 Test Backend Endpoints
```bash
# Start backend
cd backend
conda run -n bedrock-sdk uvicorn main:app --reload

# Test in another terminal
curl http://localhost:8000/postgres/connections
curl http://localhost:8000/postgres/aurora-prod/databases
```

#### 8.2 Test Aurora Connectivity
```bash
# From EC2 instance in same VPC
psql -h pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com \
     -U pg-spark \
     -d postgres \
     -p 5432
```

#### 8.3 Test EMR → Aurora Connectivity
Create a test Spark job that connects to Aurora and verify it runs successfully.

---

## CONFIGURATION CHECKLIST

Use this checklist to ensure all components are configured:

### Infrastructure:
- [ ] Aurora PostgreSQL cluster created
- [ ] Application user created with appropriate permissions
- [ ] VPC with private subnets configured
- [ ] NAT Gateway created and route tables updated
- [ ] Security groups allow port 5432 access
- [ ] JDBC driver uploaded to S3
- [ ] Secrets Manager secret created
- [ ] EMR PostgreSQL application created with VPC
- [ ] CloudWatch logging enabled for EMR
- [ ] IAM roles updated with Secrets Manager permissions

### Backend:
- [ ] `config.py` updated with Secret ARN and EMR App ID
- [ ] `postgres_metadata.py` created
- [ ] `main.py` updated with PostgreSQL endpoints
- [ ] `requirements.txt` includes psycopg2-binary
- [ ] Dependencies installed in bedrock-sdk environment

### Agents:
- [ ] Spark Supervisor Agent updated with PostgreSQL support
- [ ] Agent deployed successfully
- [ ] Agent ARN captured and verified

### Testing:
- [ ] Backend endpoints respond correctly
- [ ] Metadata fetching works
- [ ] Aurora connectivity verified
- [ ] EMR can access Aurora
- [ ] EMR can access Secrets Manager
- [ ] End-to-end query execution successful

---

## TROUBLESHOOTING

### Issue: Connection Timeout to Aurora
**Symptoms:** EMR jobs fail with connection timeout  
**Solutions:**
1. Verify NAT Gateway exists and route tables are correct
2. Check security group allows port 5432 from EMR security group
3. Verify Aurora is in same VPC or VPC peering is configured
4. Check Aurora cluster status (must be "available")

### Issue: Secrets Manager Access Denied
**Symptoms:** EMR jobs fail with "Access Denied" for Secrets Manager  
**Solutions:**
1. Verify IAM role has `secretsmanager:GetSecretValue` permission
2. Check resource ARN in policy matches secret ARN
3. Verify EMR execution role is correctly configured

### Issue: JDBC Driver Not Found
**Symptoms:** EMR jobs fail with "ClassNotFoundException: org.postgresql.Driver"  
**Solutions:**
1. Verify JDBC driver is uploaded to S3
2. Check S3 path in config.py is correct
3. Verify EMR execution role has `s3:GetObject` permission for jars/*
4. Ensure `--jars` parameter is included in spark-submit

### Issue: Authentication Failed
**Symptoms:** EMR jobs fail with "password authentication failed"  
**Solutions:**
1. Verify credentials in Secrets Manager are correct
2. Test credentials manually with psql
3. Check user has appropriate database permissions
4. Verify Secret ARN in config.py is correct

---

## COST ESTIMATION

### One-Time Costs:
- NAT Gateway Elastic IP: $0 (included with NAT Gateway)

### Monthly Recurring Costs:
| Resource | Cost | Notes |
|----------|------|-------|
| NAT Gateway | ~$32 | $0.045/hour |
| NAT Gateway Data Transfer | Variable | $0.045/GB processed |
| Secrets Manager | $0.40 | Per secret per month |
| Secrets Manager API Calls | ~$0.05 | $0.05 per 10,000 calls |
| Aurora PostgreSQL Serverless v2 | Variable | 2-10 ACU, $0.12/ACU-hour |
| EMR Serverless | Variable | Pay per use, auto-stop enabled |
| S3 Storage (JDBC driver) | <$0.01 | ~1 MB |

**Estimated Total:** $35-50/month (excluding Aurora and EMR usage)

### Cost Optimization:
1. Use VPC endpoints for S3 and Secrets Manager to avoid NAT Gateway data transfer
2. Enable EMR auto-stop (already configured: 15 min idle timeout)
3. Use Aurora Serverless v2 auto-scaling (already configured: 2-10 ACU)
4. Cache Secrets Manager credentials to reduce API calls

---

## SECURITY BEST PRACTICES

### Implemented:
- ✅ Credentials in Secrets Manager (never hardcoded)
- ✅ VPC-based network isolation
- ✅ Security groups restrict access
- ✅ Encryption at-rest (Aurora KMS)
- ✅ IAM role-based access
- ✅ Private subnets for Aurora and EMR

### Recommended Enhancements:
1. **Enable IAM Database Authentication:**
   ```bash
   aws rds modify-db-cluster \
     --db-cluster-identifier pg-database \
     --enable-iam-database-authentication \
     --region us-east-1
   ```

2. **Remove External IP Access:**
   ```bash
   aws ec2 revoke-security-group-ingress \
     --group-id sg-098a735e14f9f2953 \
     --protocol tcp \
     --port 5432 \
     --cidr 108.24.105.184/32 \
     --region us-east-1
   ```

3. **Enable VPC Flow Logs:**
   ```bash
   aws ec2 create-flow-logs \
     --resource-type VPC \
     --resource-ids vpc-0485dcc1f1d050b55 \
     --traffic-type ALL \
     --log-destination-type cloud-watch-logs \
     --log-group-name /aws/vpc/flowlogs \
     --region us-east-1
   ```

4. **Create VPC Endpoints:**
   ```bash
   # S3 endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-0485dcc1f1d050b55 \
     --service-name com.amazonaws.us-east-1.s3 \
     --route-table-ids <ROUTE_TABLE_ID> \
     --region us-east-1
   
   # Secrets Manager endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-0485dcc1f1d050b55 \
     --vpc-endpoint-type Interface \
     --service-name com.amazonaws.us-east-1.secretsmanager \
     --subnet-ids subnet-006b1a09bd82fd9f7 subnet-016fb407bc2a3e4c0 \
     --security-group-ids sg-098a735e14f9f2953 \
     --region us-east-1
   ```

5. **Enable Automatic Credential Rotation:**
   - Create Lambda function for rotation
   - Configure rotation schedule (30-90 days)
   - Test rotation process

---

## ROLLBACK PROCEDURE

If deployment fails or issues occur:

### 1. Rollback Agent:
```bash
# Revert to previous agent version (if backup exists)
# Or redeploy previous version from git
```

### 2. Rollback Backend:
```bash
cd backend
git checkout <PREVIOUS_COMMIT>
# Restart backend
```

### 3. Remove Infrastructure (if needed):
```bash
# Delete EMR application
aws emr-serverless delete-application \
  --application-id $EMR_APP_ID \
  --region us-east-1

# Delete Secrets Manager secret
aws secretsmanager delete-secret \
  --secret-id spark/postgres/aurora-prod \
  --force-delete-without-recovery \
  --region us-east-1

# Delete JDBC driver from S3
aws s3 rm s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar
```

**Note:** Keep Aurora cluster and VPC configuration as they don't impact existing workflows.

---

## AUTOMATION SCRIPT (TODO)

Create `deploy_postgres_integration.sh` that automates all steps:

```bash
#!/bin/bash
# PostgreSQL Integration Deployment Script
# Usage: ./deploy_postgres_integration.sh

set -e

# Configuration
REGION="us-east-1"
ACCOUNT_ID="260005718447"
S3_BUCKET="spark-data-${ACCOUNT_ID}-${REGION}"
VPC_ID="vpc-0485dcc1f1d050b55"
SECURITY_GROUP="sg-098a735e14f9f2953"
SUBNETS="subnet-006b1a09bd82fd9f7,subnet-016fb407bc2a3e4c0,subnet-09cc990e2dd228cdc"

# Step 1: Upload JDBC Driver
echo "Uploading JDBC driver..."
aws s3 cp postgresql-42.7.8.jar s3://${S3_BUCKET}/jars/postgresql-42.7.8.jar --region ${REGION}

# Step 2: Create Secrets Manager Secret
echo "Creating Secrets Manager secret..."
SECRET_ARN=$(aws secretsmanager create-secret ...)

# Step 3: Create EMR Application
echo "Creating EMR PostgreSQL application..."
EMR_APP_ID=$(aws emr-serverless create-application ...)

# Step 4: Update IAM Roles
echo "Updating IAM roles..."
aws iam put-role-policy ...

# Step 5: Update Backend Configuration
echo "Updating backend configuration..."
# Use sed or Python to update config.py

# Step 6: Deploy Agent
echo "Deploying Spark Supervisor Agent..."
cd backend/spark-supervisor-agent
conda run -n bedrock-sdk python agent_deployment.py

echo "✅ PostgreSQL integration deployed successfully!"
echo "Secret ARN: $SECRET_ARN"
echo "EMR App ID: $EMR_APP_ID"
```

---

**END OF DEPLOYMENT GUIDE**
