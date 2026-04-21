# Plan: Modularize Spark Supervisor Tools into MCP Tools on AgentCore Gateway

## Decisions (Confirmed)

| # | Question | Decision |
|---|----------|----------|
| 1 | Single Lambda vs. one per tool | **One Lambda per tool** — better isolation and independent scaling |
| 2 | Move `fetch_spark_results`? | **Yes** — move it too, making supervisor a pure orchestrator |
| 3 | Config passing | **Parameters per call** — dynamic, passed in each MCP tool invocation |
| 4 | Keep wrapper Lambda? | **Yes** — keep for backward compatibility |
| 5 | Gateway auth | **IAM-based** — within same account, no Cognito needed for agent-to-tool calls |
| 6 | Naming convention | **Approved** — `generate_spark_code`, `execute_spark_on_lambda`, etc. |

---

## Current Architecture

```
External Caller
  │
  ▼
Wrapper Lambda (dev-spark-agent-wrapper)
  │  - Injects config, generates session_id
  │  - Calls invoke_agent_runtime() directly (bypasses Gateway)
  │
  ▼
AgentCore Runtime (spark_supervisor_agent) — MONOLITHIC
  └── 11 tools all in one file:
        ├── call_code_generation_agent    (calls Code Gen AgentCore runtime)
        ├── execute_spark_code_lambda     (invokes Spark Lambda via boto3)
        ├── execute_spark_code_emr        (submits EMR Serverless job)
        ├── fetch_glue_table_schema       (Glue API)
        ├── fetch_postgres_table_schema   (PostgreSQL via psycopg2)
        ├── fetch_spark_results           (reads S3)
        ├── select_execution_platform     (pure logic)
        ├── validate_spark_code           (pure logic)
        ├── ensure_output_file_writing    (pure logic)
        ├── extract_python_code           (pure logic)
        └── extract_execution_logs        (pure logic)
```

---

## Target Architecture

```
External Caller
  │
  ├──(existing path)──► Wrapper Lambda ──► AgentCore Runtime (supervisor)
  │
  └──(new MCP path)───► AgentCore Gateway (MCP) ──► Tool Lambdas
                              │
                              ▼
                    ┌─────────────────────────────────────────┐
                    │  MCP Tool Targets (one Lambda each)     │
                    │                                         │
                    │  ┌─ generate_spark_code                 │
                    │  │   Lambda: dev-spark-tool-codegen     │
                    │  │   Timeout: 300s                      │
                    │  │   Deps: boto3 bedrock-agentcore      │
                    │  │                                      │
                    │  ├─ execute_spark_on_lambda              │
                    │  │   Lambda: dev-spark-tool-exec-lambda │
                    │  │   Timeout: 320s                      │
                    │  │   Deps: boto3 lambda                 │
                    │  │                                      │
                    │  ├─ execute_spark_on_emr                 │
                    │  │   Lambda: dev-spark-tool-exec-emr    │
                    │  │   Timeout: 900s                      │
                    │  │   Deps: boto3 emr-serverless, s3     │
                    │  │                                      │
                    │  ├─ get_glue_table_schema                │
                    │  │   Lambda: dev-spark-tool-glue-schema │
                    │  │   Timeout: 30s                       │
                    │  │   Deps: boto3 glue                   │
                    │  │                                      │
                    │  ├─ get_postgres_table_schema            │
                    │  │   Lambda: dev-spark-tool-pg-schema   │
                    │  │   Timeout: 30s                       │
                    │  │   Deps: boto3 secretsmanager,        │
                    │  │         psycopg2-binary (layer)      │
                    │  │                                      │
                    │  └─ fetch_spark_results                  │
                    │      Lambda: dev-spark-tool-fetch-results│
                    │      Timeout: 60s                       │
                    │      Deps: boto3 s3                     │
                    └─────────────────────────────────────────┘

AgentCore Runtime (spark_supervisor_agent) — ORCHESTRATOR ONLY
  └── 5 local tools (pure logic, no external calls):
        ├── select_execution_platform
        ├── validate_spark_code
        ├── ensure_output_file_writing
        ├── extract_python_code
        └── extract_execution_logs
  └── Calls MCP tools on Gateway via IAM auth for all external operations
```

---

## Tools Moving to MCP Gateway (6 tools → 6 Lambdas)

| MCP Tool Name | Lambda Function Name | Source Function | Timeout | Memory | Dependencies |
|---------------|---------------------|-----------------|---------|--------|--------------|
| `generate_spark_code` | `dev-spark-tool-codegen` | `call_code_generation_agent` | 300s | 256MB | boto3 bedrock-agentcore |
| `execute_spark_on_lambda` | `dev-spark-tool-exec-lambda` | `execute_spark_code_lambda` | 320s | 256MB | boto3 lambda |
| `execute_spark_on_emr` | `dev-spark-tool-exec-emr` | `execute_spark_code_emr` | 900s | 256MB | boto3 emr-serverless, s3, sts |
| `get_glue_table_schema` | `dev-spark-tool-glue-schema` | `fetch_glue_table_schema` | 30s | 128MB | boto3 glue |
| `get_postgres_table_schema` | `dev-spark-tool-pg-schema` | `fetch_postgres_table_schema` | 30s | 256MB | boto3 secretsmanager, psycopg2-binary |
| `fetch_spark_results` | `dev-spark-tool-fetch-results` | `fetch_spark_results` | 60s | 256MB | boto3 s3 |

## Tools Staying Local in Supervisor (5 tools)

| Tool | Reason |
|------|--------|
| `select_execution_platform` | Pure decision logic based on file size |
| `validate_spark_code` | String analysis — checks imports, output file writing |
| `ensure_output_file_writing` | Code transformation — injects output file logic |
| `extract_python_code` | String parsing — extracts code from markdown blocks |
| `extract_execution_logs` | Dict parsing — extracts logs from execution results |

---

## MCP Tool Schemas

### 1. generate_spark_code

```json
{
  "name": "generate_spark_code",
  "description": "Generate PySpark code from a natural language prompt using the Code Generation Agent",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": { "type": "string", "description": "Natural language query describing the data operation" },
      "session_id": { "type": "string", "description": "Session ID for tracking" },
      "s3_input_path": { "type": "string", "description": "S3 path to input CSV file" },
      "selected_tables": { "type": "array", "description": "List of Glue table references" },
      "selected_postgres_tables": { "type": "array", "description": "List of PostgreSQL table references with connection details" },
      "s3_output_path": { "type": "string", "description": "S3 path for writing results" },
      "model_id": { "type": "string", "description": "Bedrock model ID for code generation" },
      "code_gen_agent_arn": { "type": "string", "description": "ARN of the Code Generation AgentCore runtime" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["prompt", "session_id", "model_id", "code_gen_agent_arn"]
  }
}
```

### 2. execute_spark_on_lambda

```json
{
  "name": "execute_spark_on_lambda",
  "description": "Execute validated PySpark code on AWS Lambda (Spark-on-Lambda)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "spark_code": { "type": "string", "description": "Validated PySpark code to execute" },
      "s3_output_path": { "type": "string", "description": "S3 path for output results" },
      "lambda_function": { "type": "string", "description": "Name of the Spark Lambda function" },
      "s3_bucket": { "type": "string", "description": "S3 bucket name" },
      "spark_config": { "type": "object", "description": "Spark configuration (S3A filesystem, etc.)" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["spark_code", "s3_output_path", "lambda_function", "s3_bucket"]
  }
}
```

### 3. execute_spark_on_emr

```json
{
  "name": "execute_spark_on_emr",
  "description": "Execute validated PySpark code on EMR Serverless",
  "inputSchema": {
    "type": "object",
    "properties": {
      "spark_code": { "type": "string", "description": "Validated PySpark code to execute" },
      "s3_output_path": { "type": "string", "description": "S3 path for output results" },
      "s3_bucket": { "type": "string", "description": "S3 bucket for scripts and logs" },
      "session_id": { "type": "string", "description": "Session ID (used to save code to S3)" },
      "emr_application_id": { "type": "string", "description": "EMR Serverless application ID" },
      "emr_execution_role_arn": { "type": "string", "description": "IAM role ARN for EMR execution" },
      "emr_timeout_minutes": { "type": "number", "description": "Timeout in minutes for EMR job", "default": 15 },
      "jdbc_driver_path": { "type": "string", "description": "S3 path to JDBC driver JAR (for PostgreSQL)" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["spark_code", "s3_output_path", "s3_bucket", "session_id", "emr_application_id"]
  }
}
```

### 4. get_glue_table_schema

```json
{
  "name": "get_glue_table_schema",
  "description": "Fetch detailed schema for an AWS Glue table including columns, types, location, and partitions",
  "inputSchema": {
    "type": "object",
    "properties": {
      "database_name": { "type": "string", "description": "Glue database name" },
      "table_name": { "type": "string", "description": "Glue table name" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["database_name", "table_name"]
  }
}
```

### 5. get_postgres_table_schema

```json
{
  "name": "get_postgres_table_schema",
  "description": "Fetch schema for a PostgreSQL table by querying information_schema via JDBC",
  "inputSchema": {
    "type": "object",
    "properties": {
      "jdbc_url": { "type": "string", "description": "PostgreSQL JDBC URL" },
      "secret_arn": { "type": "string", "description": "Secrets Manager ARN for DB credentials" },
      "database": { "type": "string", "description": "Database name" },
      "schema": { "type": "string", "description": "Schema name (e.g., 'public')" },
      "table": { "type": "string", "description": "Table name" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["jdbc_url", "secret_arn", "database", "schema", "table"]
  }
}
```

### 6. fetch_spark_results

```json
{
  "name": "fetch_spark_results",
  "description": "Fetch Spark execution results from S3 output path",
  "inputSchema": {
    "type": "object",
    "properties": {
      "s3_output_path": { "type": "string", "description": "S3 path where Spark wrote results" },
      "max_rows": { "type": "number", "description": "Maximum rows to return (default: all)" },
      "s3_bucket": { "type": "string", "description": "S3 bucket name" },
      "region": { "type": "string", "description": "AWS region" }
    },
    "required": ["s3_output_path", "s3_bucket"]
  }
}
```

---

## Implementation Phases

### Phase 1: Create Lambda Functions (6 new Lambdas) ✅ COMPLETE
### Phase 2: Register MCP Tools on Gateway ✅ COMPLETE
### Phase 3: Update Spark Supervisor Agent ✅ COMPLETE
### Phase 4: Update CloudFormation ✅ COMPLETE
### Phase 5: Update Deployment Script ✅ COMPLETE

**Directory structure:**
```
mcp-tools/
├── generate-spark-code/
│   ├── handler.py              # Extracted from call_code_generation_agent
│   └── requirements.txt        # boto3
├── execute-spark-on-lambda/
│   ├── handler.py              # Extracted from execute_spark_code_lambda
│   └── requirements.txt        # boto3
├── execute-spark-on-emr/
│   ├── handler.py              # Extracted from execute_spark_code_emr
│   └── requirements.txt        # boto3
├── get-glue-table-schema/
│   ├── handler.py              # Extracted from fetch_glue_table_schema
│   └── requirements.txt        # boto3
├── get-postgres-table-schema/
│   ├── handler.py              # Extracted from fetch_postgres_table_schema
│   └── requirements.txt        # boto3, psycopg2-binary
└── fetch-spark-results/
    ├── handler.py              # Extracted from fetch_spark_results
    └── requirements.txt        # boto3
```

**Each Lambda handler follows this pattern:**
```python
import json

def lambda_handler(event, context):
    """MCP Tool: <tool_name>
    
    Receives parameters directly (no config injection needed).
    Returns standardized JSON response.
    """
    try:
        # Extract parameters from event
        param1 = event.get('param1')
        param2 = event.get('param2')
        
        # Execute tool logic (moved from spark_supervisor_agent.py)
        result = do_work(param1, param2)
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }
```

**Key extraction notes per tool:**

| Lambda | Extract From | Special Handling |
|--------|-------------|------------------|
| `generate-spark-code` | Lines 67-490 | Remove `get_config()` calls; accept `model_id`, `code_gen_agent_arn`, `region` as params |
| `execute-spark-on-lambda` | Lines 640-697 | Remove `get_config()` calls; accept `lambda_function`, `s3_bucket`, `spark_config`, `region` as params |
| `execute-spark-on-emr` | Lines 699-811 | Remove `get_config()` and `CURRENT_SESSION_ID` global; accept `session_id`, `emr_application_id`, `emr_execution_role_arn`, `s3_bucket`, `region` as params |
| `get-glue-table-schema` | Lines 1090-1133 | Remove `AWS_REGION` global; accept `region` as param |
| `get-postgres-table-schema` | Lines 1135-1219 | Remove `AWS_REGION` global; accept `region` as param; package psycopg2-binary as Lambda layer |
| `fetch-spark-results` | Lines 978-1088 | Remove `get_config()` calls; accept `s3_bucket`, `region` as params |

### Phase 2: Register MCP Tools on Gateway

**Gateway Target Configuration:**

Each Lambda gets registered as a Gateway target with its tool schema. Since CloudFormation doesn't support Gateway targets natively, this will be done via:

1. **AWS CLI / SDK script** — A deployment script that calls `bedrock-agentcore` APIs to register targets
2. **Tool schemas** — As defined in the MCP Tool Schemas section above

**IAM Configuration:**
- Each tool Lambda needs an execution role with permissions for its specific AWS services
- Gateway needs `lambda:InvokeFunction` permission on all 6 tool Lambdas
- Tool Lambdas authenticate via IAM (no Cognito JWT needed)

**Per-Lambda IAM permissions:**

| Lambda | IAM Permissions Needed |
|--------|----------------------|
| `dev-spark-tool-codegen` | `bedrock-agentcore:InvokeAgentRuntime` |
| `dev-spark-tool-exec-lambda` | `lambda:InvokeFunction` on `dev-spark-on-lambda` |
| `dev-spark-tool-exec-emr` | `emr-serverless:StartJobRun`, `emr-serverless:GetJobRun`, `s3:PutObject`, `sts:GetCallerIdentity` |
| `dev-spark-tool-glue-schema` | `glue:GetTable` |
| `dev-spark-tool-pg-schema` | `secretsmanager:GetSecretValue` |
| `dev-spark-tool-fetch-results` | `s3:GetObject`, `s3:ListBucket` |

### Phase 3: Update Spark Supervisor Agent

**Changes to `spark_supervisor_agent.py`:**

1. **Remove** the 6 tool function implementations (code gen, exec lambda, exec emr, glue schema, pg schema, fetch results)
2. **Add** MCP Gateway client helper:
   ```python
   def call_mcp_tool(tool_name: str, params: dict) -> dict:
       """Call an MCP tool on the AgentCore Gateway via IAM auth"""
       # Use boto3 bedrock-agentcore client to invoke Gateway tool
       pass
   ```
3. **Replace** each removed tool with a thin wrapper that calls `call_mcp_tool()`:
   ```python
   @tool
   def generate_spark_code(prompt: str, session_id: str, ...) -> str:
       """Generate PySpark code via MCP Gateway"""
       config = get_config()
       return call_mcp_tool("generate_spark_code", {
           "prompt": prompt,
           "session_id": session_id,
           "model_id": config.get("model_id"),
           "code_gen_agent_arn": config.get("code_gen_agent_arn"),
           "region": config.get("region", "us-east-1"),
           ...
       })
   ```
4. **Keep** the 5 local pure-logic tools unchanged
5. **Update** the system prompt to use new tool names
6. **Update** the `tools=[]` list in `create_spark_supervisor_agent()`

### Phase 4: Update CloudFormation

Add to `cloudformation/spark-complete-stack.yml`:

1. **6 new Lambda functions** with appropriate:
   - Runtime: Python 3.11
   - Memory and timeout per table above
   - IAM execution roles with least-privilege permissions
   - Environment variables: None (config passed per call)

2. **Lambda Layer for psycopg2** (for `get-postgres-table-schema` only)

3. **Lambda permissions** for Gateway to invoke each tool Lambda:
   ```yaml
   ToolLambdaGatewayPermission:
     Type: AWS::Lambda::Permission
     Properties:
       FunctionName: !Ref ToolLambdaFunction
       Action: lambda:InvokeFunction
       Principal: bedrock-agentcore.amazonaws.com
       SourceArn: !GetAtt SparkAgentCoreGateway.GatewayArn
   ```

4. **IAM role for supervisor agent** — Add permission to invoke Gateway MCP tools

### Phase 5: Update Deployment Script

Update `scripts/deploy-all.sh`:

1. **Build and deploy** each of the 6 tool Lambdas:
   - Package code + dependencies
   - Create/update Lambda functions
   - Special handling for psycopg2 layer

2. **Register Gateway targets** via AWS CLI:
   ```bash
   aws bedrock-agentcore create-gateway-target \
     --gateway-id $GATEWAY_ID \
     --name "generate_spark_code" \
     --target-configuration lambdaTarget={lambdaArn=$CODEGEN_LAMBDA_ARN} \
     --tool-schema '...'
   ```

3. **Redeploy supervisor agent** with updated code

---

## Rollback Plan

If issues arise:
1. Supervisor agent still has the original tool implementations in git history
2. Revert `spark_supervisor_agent.py` to use local tools
3. Redeploy supervisor agent
4. Tool Lambdas can remain deployed (unused) or be deleted

---

## Testing Strategy

### Unit Tests
- Test each tool Lambda independently with sample payloads
- Verify input validation and error handling

### Integration Tests
- Test supervisor agent calling MCP tools via Gateway
- Verify IAM auth works for agent-to-Gateway calls
- Test timeout handling for long-running tools (EMR)

### End-to-End Tests
- Wrapper Lambda → Supervisor Agent → MCP Tools → Spark Lambda
- Test with: simple calculation, CSV group by, Glue table query, PostgreSQL query

### Backward Compatibility
- Verify wrapper Lambda still works unchanged
- Verify existing API Gateway integrations (if any) still work

---

## Migration Order

Execute in this order to minimize risk:

1. **Deploy tool Lambdas** (no impact — nothing calls them yet)
2. **Register Gateway targets** (no impact — supervisor still uses local tools)
3. **Update and redeploy supervisor agent** (switches to MCP tools)
4. **Test end-to-end**
5. **Clean up** old tool code from supervisor agent (already done in step 3)

---

## Estimated Effort

| Phase | Effort | Description |
|-------|--------|-------------|
| Phase 1: Create 6 Lambdas | 2-3 hours | Extract code, create handlers, package dependencies |
| Phase 2: Register Gateway targets | 1 hour | Define schemas, write registration script |
| Phase 3: Update supervisor agent | 1-2 hours | Replace tools with MCP wrappers, update prompt |
| Phase 4: Update CloudFormation | 1-2 hours | Add Lambda resources, IAM roles, permissions |
| Phase 5: Update deploy script | 1 hour | Add build/deploy steps for new Lambdas |
| Testing | 2-3 hours | Unit, integration, end-to-end testing |
| **Total** | **8-12 hours** | |

---

## Open Items

- **Gateway MCP invocation from AgentCore runtime**: Need to verify the exact boto3 API for an AgentCore runtime agent to call MCP tools on a Gateway using IAM auth. This may require the agent to use the Gateway's MCP endpoint URL directly, or there may be a dedicated SDK method.
- **psycopg2 Lambda Layer**: Need to build or find a pre-built Lambda layer for psycopg2-binary compatible with Python 3.11 on Amazon Linux 2023.
- **Gateway target registration API**: CloudFormation doesn't support Gateway targets. Need to confirm the exact AWS CLI/SDK commands for `create-gateway-target` or equivalent.
