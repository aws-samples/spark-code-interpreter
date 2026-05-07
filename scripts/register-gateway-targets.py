#!/usr/bin/env python3
"""Register MCP tool targets on both Gateways.

External Gateway (Cognito JWT): ask-agent → wrapper Lambda
Internal Gateway (IAM): cold-path tools (EMR, Glue schema, Postgres schema)
"""

import boto3
import json
import os
import time

REGION = boto3.session.Session().region_name or "us-east-1"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# Get Gateway IDs from CloudFormation
cfn = boto3.client("cloudformation", region_name=REGION)
stack = cfn.describe_stacks(StackName=f"{ENVIRONMENT}-spark-complete-stack")
outputs = {o["OutputKey"]: o["OutputValue"] for o in stack["Stacks"][0]["Outputs"]}

EXTERNAL_GATEWAY_ID = outputs["AgentCoreGatewayId"]

# Find internal Gateway by name (created by deploy-all.sh, not CloudFormation)
INTERNAL_GATEWAY_ID = ""
try:
    gateways = client.list_gateways()
    internal_name = f"{ENVIRONMENT}-spark-internal-gateway"
    for gw in gateways.get("items", []):
        if gw["name"] == internal_name:
            INTERNAL_GATEWAY_ID = gw["gatewayId"]
            break
except Exception:
    pass

print(f"Account: {ACCOUNT_ID}, Region: {REGION}, Environment: {ENVIRONMENT}")
print(f"External Gateway: {EXTERNAL_GATEWAY_ID}")
print(f"Internal Gateway: {INTERNAL_GATEWAY_ID}")
print()

client = boto3.client("bedrock-agentcore-control", region_name=REGION)


def make_tool(name, desc, props, required):
    return {
        "name": name,
        "description": desc,
        "inputSchema": {"type": "object", "properties": props, "required": required},
    }


def clear_targets(gateway_id):
    """Delete all existing targets from a gateway."""
    resp = client.list_gateway_targets(gatewayIdentifier=gateway_id)
    items = resp.get("items", [])
    if not items:
        return
    print(f"  Clearing {len(items)} existing targets...")
    for t in items:
        try:
            client.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=t["targetId"])
        except Exception:
            pass
    time.sleep(5)


def register_target(gateway_id, name, description, lambda_name, tools):
    """Register a single target on a gateway."""
    lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{lambda_name}"
    print(f"  Registering: {name} → {lambda_name}")
    try:
        resp = client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=name,
            description=description,
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {"inlinePayload": tools},
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
        )
        print(f"    OK: {resp.get('targetId')} ({resp.get('status')})")
    except Exception as e:
        print(f"    Error: {e}")


# ============================================================================
# External Gateway (Cognito JWT) — ask-agent only
# ============================================================================
print("External Gateway (Cognito JWT):")
clear_targets(EXTERNAL_GATEWAY_ID)

register_target(
    EXTERNAL_GATEWAY_ID,
    "ask-agent",
    "Spark Code Interpreter - send natural language prompts, get PySpark code and results",
    f"{ENVIRONMENT}-spark-agent-wrapper",
    [
        make_tool(
            "ask_agent",
            "Ask the Spark Code Interpreter a natural language question",
            {
                "prompt": {"type": "string", "description": "Natural language query"},
                "s3_input_path": {"type": "string", "description": "Optional S3 CSV path"},
                "execution_engine": {"type": "string", "description": "auto, lambda, or emr"},
            },
            ["prompt"],
        )
    ],
)
print()

# ============================================================================
# Internal Gateway (IAM) — cold-path tools
# ============================================================================
if INTERNAL_GATEWAY_ID:
    print("Internal Gateway (IAM):")
    clear_targets(INTERNAL_GATEWAY_ID)

    register_target(
        INTERNAL_GATEWAY_ID,
        "execute-spark-on-emr",
        "Execute validated PySpark code on EMR Serverless",
        f"{ENVIRONMENT}-spark-tool-execute-spark-on-emr",
        [
            make_tool(
                "execute_spark_on_emr",
                "Execute PySpark on EMR Serverless",
                {
                    "spark_code": {"type": "string"},
                    "s3_output_path": {"type": "string"},
                    "s3_bucket": {"type": "string"},
                    "session_id": {"type": "string"},
                    "emr_application_id": {"type": "string"},
                    "region": {"type": "string"},
                },
                ["spark_code", "s3_output_path", "s3_bucket", "session_id", "emr_application_id"],
            )
        ],
    )

    register_target(
        INTERNAL_GATEWAY_ID,
        "get-glue-table-schema",
        "Fetch schema for an AWS Glue table",
        f"{ENVIRONMENT}-spark-tool-get-glue-table-schema",
        [
            make_tool(
                "get_glue_table_schema",
                "Fetch Glue table schema",
                {
                    "database_name": {"type": "string"},
                    "table_name": {"type": "string"},
                    "region": {"type": "string"},
                },
                ["database_name", "table_name"],
            )
        ],
    )

    register_target(
        INTERNAL_GATEWAY_ID,
        "get-postgres-table-schema",
        "Fetch schema for a PostgreSQL table",
        f"{ENVIRONMENT}-spark-tool-get-postgres-table-schema",
        [
            make_tool(
                "get_postgres_table_schema",
                "Fetch PostgreSQL table schema",
                {
                    "jdbc_url": {"type": "string"},
                    "secret_arn": {"type": "string"},
                    "database": {"type": "string"},
                    "schema": {"type": "string"},
                    "table": {"type": "string"},
                    "region": {"type": "string"},
                },
                ["jdbc_url", "secret_arn", "database", "schema", "table"],
            )
        ],
    )
    print()
else:
    print("Internal Gateway not found in stack outputs — skipping cold-path targets")
    print()

# ============================================================================
# Verify
# ============================================================================
print("Final state:")
print(f"  External Gateway ({EXTERNAL_GATEWAY_ID}):")
resp = client.list_gateway_targets(gatewayIdentifier=EXTERNAL_GATEWAY_ID)
for t in resp.get("items", []):
    print(f"    {t['name']}: {t['targetId']} ({t['status']})")

if INTERNAL_GATEWAY_ID:
    print(f"  Internal Gateway ({INTERNAL_GATEWAY_ID}):")
    resp = client.list_gateway_targets(gatewayIdentifier=INTERNAL_GATEWAY_ID)
    for t in resp.get("items", []):
        print(f"    {t['name']}: {t['targetId']} ({t['status']})")
