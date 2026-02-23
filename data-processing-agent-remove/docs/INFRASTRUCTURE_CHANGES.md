# Infrastructure Changes for PostgreSQL Integration

## Overview
This document captures all infrastructure changes made to enable PostgreSQL integration with Spark on EMR Serverless. Use this as reference for creating Infrastructure as Code (IaC) templates.

---

## 1. VPC Endpoints

### 1.1 CloudWatch Logs VPC Endpoint
**Purpose:** Enable EMR Serverless jobs to write logs to CloudWatch Logs from within VPC

**Resource ID:** `vpce-0f5bee5beccb281d8`

**Configuration:**
```yaml
Service: com.amazonaws.us-east-1.logs
VPC: vpc-0485dcc1f1d050b55
Type: Interface
PrivateDnsEnabled: true
Subnets:
  - subnet-09cc990e2dd228cdc
  - subnet-006b1a09bd82fd9f7
  - subnet-016fb407bc2a3e4c0
SecurityGroups:
  - sg-098a735e14f9f2953
```

**Terraform Example:**
```hcl
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = "vpc-0485dcc1f1d050b55"
  service_name        = "com.amazonaws.us-east-1.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  subnet_ids = [
    "subnet-09cc990e2dd228cdc",
    "subnet-006b1a09bd82fd9f7",
    "subnet-016fb407bc2a3e4c0"
  ]
  
  security_group_ids = ["sg-098a735e14f9f2953"]
  
  tags = {
    Name = "emr-cloudwatch-logs-endpoint"
  }
}
```

### 1.2 Secrets Manager VPC Endpoint
**Purpose:** Enable EMR Serverless jobs to retrieve PostgreSQL credentials from Secrets Manager

**Resource ID:** `vpce-0bc8e399a2bfa1009`

**Configuration:**
```yaml
Service: com.amazonaws.us-east-1.secretsmanager
VPC: vpc-0485dcc1f1d050b55
Type: Interface
PrivateDnsEnabled: true
Subnets:
  - subnet-09cc990e2dd228cdc
  - subnet-006b1a09bd82fd9f7
  - subnet-016fb407bc2a3e4c0
SecurityGroups:
  - sg-098a735e14f9f2953
```

**Terraform Example:**
```hcl
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = "vpc-0485dcc1f1d050b55"
  service_name        = "com.amazonaws.us-east-1.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  subnet_ids = [
    "subnet-09cc990e2dd228cdc",
    "subnet-006b1a09bd82fd9f7",
    "subnet-016fb407bc2a3e4c0"
  ]
  
  security_group_ids = ["sg-098a735e14f9f2953"]
  
  tags = {
    Name = "emr-secretsmanager-endpoint"
  }
}
```

---

## 2. IAM Permissions

### 2.1 EMR Serverless Execution Role
**Role Name:** `EMRServerlessExecutionRole`
**Role ARN:** `arn:aws:iam::260005718447:role/EMRServerlessExecutionRole`

### 2.2 New Inline Policy: EMRSecretsManagerPolicy
**Purpose:** Grant EMR jobs permission to retrieve PostgreSQL credentials

**Policy Document:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/*"
    }
  ]
}
```

**Terraform Example:**
```hcl
resource "aws_iam_role_policy" "emr_secrets_manager" {
  name = "EMRSecretsManagerPolicy"
  role = aws_iam_role.emr_serverless_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:spark/postgres/*"
      }
    ]
  })
}
```

### 2.3 Existing Policies (for reference)
- **Attached Managed Policies:**
  - `AWSGlueServiceRole`
  - `AmazonEMRServicePolicy_v2`
  
- **Existing Inline Policy:** `EMRServerlessS3Policy`
  - S3 read/write permissions
  - CloudWatch Logs permissions (CreateLogGroup, CreateLogStream, PutLogEvents)

---

## 3. EMR Serverless Application

### 3.1 PostgreSQL-Enabled EMR Application
**Application ID:** `00g0oddl52n83r09`
**Name:** `spark-postgres-interpreter-app`

**Configuration:**
```yaml
ReleaseLabel: emr-7.0.0
Type: Spark
Architecture: X86_64

InitialCapacity:
  Driver:
    WorkerCount: 1
    CPU: 2 vCPU
    Memory: 4 GB
    Disk: 20 GB
  Executor:
    WorkerCount: 2
    CPU: 4 vCPU
    Memory: 8 GB
    Disk: 20 GB

MaximumCapacity:
  CPU: 400 vCPU
  Memory: 1000 GB
  Disk: 400000 GB

NetworkConfiguration:
  SubnetIds:
    - subnet-09cc990e2dd228cdc
    - subnet-006b1a09bd82fd9f7
    - subnet-016fb407bc2a3e4c0
  SecurityGroupIds:
    - sg-098a735e14f9f2953

MonitoringConfiguration:
  CloudWatchLoggingConfiguration:
    Enabled: true
    LogTypes:
      SPARK_DRIVER: [stdout, stderr]
      SPARK_EXECUTOR: [stdout, stderr]
  ManagedPersistenceMonitoringConfiguration:
    Enabled: true

AutoStartConfiguration:
  Enabled: true

AutoStopConfiguration:
  Enabled: true
  IdleTimeoutMinutes: 15
```

**Terraform Example:**
```hcl
resource "aws_emrserverless_application" "postgres_spark" {
  name          = "spark-postgres-interpreter-app"
  release_label = "emr-7.0.0"
  type          = "Spark"
  
  initial_capacity {
    initial_capacity_type = "Driver"
    
    initial_capacity_config {
      worker_count = 1
      worker_configuration {
        cpu    = "2 vCPU"
        memory = "4 GB"
        disk   = "20 GB"
      }
    }
  }
  
  initial_capacity {
    initial_capacity_type = "Executor"
    
    initial_capacity_config {
      worker_count = 2
      worker_configuration {
        cpu    = "4 vCPU"
        memory = "8 GB"
        disk   = "20 GB"
      }
    }
  }
  
  maximum_capacity {
    cpu    = "400 vCPU"
    memory = "1000 GB"
    disk   = "400000 GB"
  }
  
  network_configuration {
    subnet_ids         = [
      "subnet-09cc990e2dd228cdc",
      "subnet-006b1a09bd82fd9f7",
      "subnet-016fb407bc2a3e4c0"
    ]
    security_group_ids = ["sg-098a735e14f9f2953"]
  }
  
  auto_start_configuration {
    enabled = true
  }
  
  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }
  
  tags = {
    Name = "PostgreSQL Spark Application"
  }
}
```

---

## 4. S3 Resources

### 4.1 PostgreSQL JDBC Driver
**Location:** `s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar`
**Purpose:** JDBC driver for PostgreSQL connectivity from Spark

**Upload Command:**
```bash
aws s3 cp postgresql-42.7.8.jar s3://spark-data-260005718447-us-east-1/jars/
```

**Terraform Example:**
```hcl
resource "aws_s3_object" "postgresql_jdbc_driver" {
  bucket = "spark-data-260005718447-us-east-1"
  key    = "jars/postgresql-42.7.8.jar"
  source = "postgresql-42.7.8.jar"
  etag   = filemd5("postgresql-42.7.8.jar")
}
```

---

## 5. Application Configuration

### 5.1 Backend Settings (backend/settings.json)

**Required Configuration:**
```json
{
  "spark": {
    "emr_application_id": "00fv6g7rptsov009",
    "emr_postgres_application_id": "00g0oddl52n83r09",
    "supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
  },
  "postgres": {
    "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar",
    "connections": [
      {
        "name": "aurora",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
        "host": "pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com",
        "port": 5432,
        "database": "postgres",
        "auth_method": "user_password",
        "enabled": true
      }
    ]
  }
}
```

### 5.2 Code Changes

**Backend (main.py):**
- Added `selected_postgres_tables` field to `SparkGenerateRequest` model
- Updated endpoint to read PostgreSQL tables from request
- Backend selects `emr_postgres_application_id` when PostgreSQL tables present
- Backend passes `jdbc_driver_path` to supervisor agent config

**Supervisor Agent (spark_supervisor_agent.py):**
- Updated EMR app ID retrieval to check both `emr_postgres_application_id` and `emr_application_id`
- Added `--jars` parameter to spark-submit when `jdbc_driver_path` is provided

---

## 6. Network Requirements

### 6.1 Security Group Rules
**Security Group:** `sg-098a735e14f9f2953` (default VPC security group)

**Required Rules:**
- **Egress:** Allow all outbound traffic (0.0.0.0/0)
- **Ingress:** Allow all traffic from same security group (for inter-service communication)
- **Ingress:** PostgreSQL port 5432 from specific IPs (if needed)

### 6.2 RDS Connectivity
- RDS cluster must be in same VPC or have network connectivity
- RDS security group must allow inbound PostgreSQL (5432) from EMR security group
- In this setup: RDS uses same security group (`sg-098a735e14f9f2953`)

---

## 7. Secrets Manager

### 7.1 PostgreSQL Credentials Secret
**Secret ARN:** `arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf`

**Secret Format:**
```json
{
  "username": "<postgres_username>",
  "password": "<postgres_password>"
}
```

**Terraform Example:**
```hcl
resource "aws_secretsmanager_secret" "postgres_credentials" {
  name        = "spark/postgres/aurora"
  description = "PostgreSQL credentials for Spark EMR access"
}

resource "aws_secretsmanager_secret_version" "postgres_credentials" {
  secret_id = aws_secretsmanager_secret.postgres_credentials.id
  secret_string = jsonencode({
    username = var.postgres_username
    password = var.postgres_password
  })
}
```

---

## 8. Deployment Checklist

When deploying to a new environment, ensure:

- [ ] VPC endpoints created for CloudWatch Logs and Secrets Manager
- [ ] EMR execution role has Secrets Manager permissions
- [ ] PostgreSQL JDBC driver uploaded to S3
- [ ] EMR Serverless application created with VPC configuration
- [ ] Backend settings.json configured with correct ARNs and paths
- [ ] Security groups allow EMR to RDS connectivity
- [ ] PostgreSQL credentials stored in Secrets Manager
- [ ] Supervisor agent deployed with updated code

---

## 9. Cost Considerations

**VPC Endpoints:**
- CloudWatch Logs: ~$0.01/hour + $0.01/GB data processed
- Secrets Manager: ~$0.01/hour + $0.01/GB data processed

**EMR Serverless:**
- Charged per vCPU-hour and GB-hour consumed
- Auto-stop after 15 minutes of inactivity reduces costs

**Secrets Manager:**
- $0.40/secret/month
- $0.05 per 10,000 API calls

---

## 10. Troubleshooting

**Common Issues:**

1. **ClassNotFoundException: org.postgresql.Driver**
   - Ensure `jdbc_driver_path` is configured in backend settings
   - Verify JDBC JAR exists in S3

2. **Connect timeout to CloudWatch Logs**
   - Verify CloudWatch Logs VPC endpoint exists and is available
   - Check security group allows traffic to VPC endpoint

3. **AccessDeniedException for Secrets Manager**
   - Verify EMR execution role has `EMRSecretsManagerPolicy`
   - Ensure Secrets Manager VPC endpoint exists

4. **PostgreSQL connection timeout**
   - Verify RDS security group allows inbound from EMR security group
   - Check network connectivity between VPC subnets

---

## Document Version
- **Created:** 2025-11-03
- **Last Updated:** 2025-11-03
- **Author:** Infrastructure Team
