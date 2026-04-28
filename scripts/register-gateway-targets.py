#!/usr/bin/env python3
"""Register MCP tool Lambda functions as Gateway targets on AgentCore Gateway."""

import boto3
import json

REGION = "us-east-1"
ACCOUNT_ID = "914787431788"
ENVIRONMENT = "dev"
GATEWAY_ID = "dev-spark-gateway-qmofb4jgze"

client = boto3.client("bedrock-agentcore-control", region_name=REGION)


def make_tool(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


TARGETS = [
    {
        "name": "generate-spark-code",
        "description": "Generate PySpark code from a natural language prompt using the Code Generation Agent",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-generate-spark-code",
        "tools": [
            make_tool(
                "generate_spark_code",
                "Generate PySpark code from a natural language prompt",
                {
                    "prompt": {"type": "string", "description": "Natural language query"},
                    "session_id": {"type": "string", "description": "Session ID"},
                    "s3_input_path": {"type": "string", "description": "S3 input CSV path"},
                    "s3_output_path": {"type": "string", "description": "S3 output path"},
                    "model_id": {"type": "string", "description": "Bedrock model ID"},
                    "code_gen_agent_arn": {"type": "string", "description": "Code Gen Agent ARN"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["prompt", "session_id", "model_id", "code_gen_agent_arn"],
            )
        ],
    },
    {
        "name": "execute-spark-on-lambda",
        "description": "Execute validated PySpark code on AWS Lambda",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-execute-spark-on-lambda",
        "tools": [
            make_tool(
                "execute_spark_on_lambda",
                "Execute validated PySpark code on Spark-on-Lambda",
                {
                    "spark_code": {"type": "string", "description": "Validated PySpark code"},
                    "s3_output_path": {"type": "string", "description": "S3 output path"},
                    "lambda_function": {"type": "string", "description": "Spark Lambda name"},
                    "s3_bucket": {"type": "string", "description": "S3 bucket"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["spark_code", "s3_output_path", "lambda_function", "s3_bucket"],
            )
        ],
    },
    {
        "name": "execute-spark-on-emr",
        "description": "Execute validated PySpark code on EMR Serverless",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-execute-spark-on-emr",
        "tools": [
            make_tool(
                "execute_spark_on_emr",
                "Execute validated PySpark code on EMR Serverless",
                {
                    "spark_code": {"type": "string", "description": "Validated PySpark code"},
                    "s3_output_path": {"type": "string", "description": "S3 output path"},
                    "s3_bucket": {"type": "string", "description": "S3 bucket"},
                    "session_id": {"type": "string", "description": "Session ID"},
                    "emr_application_id": {"type": "string", "description": "EMR app ID"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["spark_code", "s3_output_path", "s3_bucket", "session_id", "emr_application_id"],
            )
        ],
    },
    {
        "name": "get-glue-table-schema",
        "description": "Fetch schema for an AWS Glue table",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-get-glue-table-schema",
        "tools": [
            make_tool(
                "get_glue_table_schema",
                "Fetch detailed schema for an AWS Glue table",
                {
                    "database_name": {"type": "string", "description": "Glue database name"},
                    "table_name": {"type": "string", "description": "Glue table name"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["database_name", "table_name"],
            )
        ],
    },
    {
        "name": "get-postgres-table-schema",
        "description": "Fetch schema for a PostgreSQL table via JDBC",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-get-postgres-table-schema",
        "tools": [
            make_tool(
                "get_postgres_table_schema",
                "Fetch schema for a PostgreSQL table by querying information_schema",
                {
                    "jdbc_url": {"type": "string", "description": "PostgreSQL JDBC URL"},
                    "secret_arn": {"type": "string", "description": "Secrets Manager ARN"},
                    "database": {"type": "string", "description": "Database name"},
                    "schema": {"type": "string", "description": "Schema name"},
                    "table": {"type": "string", "description": "Table name"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["jdbc_url", "secret_arn", "database", "schema", "table"],
            )
        ],
    },
    {
        "name": "fetch-spark-results",
        "description": "Fetch Spark execution results from S3",
        "lambda_function": f"{ENVIRONMENT}-spark-tool-fetch-spark-results",
        "tools": [
            make_tool(
                "fetch_spark_results",
                "Fetch Spark execution results from S3 output path",
                {
                    "s3_output_path": {"type": "string", "description": "S3 results path"},
                    "s3_bucket": {"type": "string", "description": "S3 bucket name"},
                    "max_rows": {"type": "number", "description": "Max rows to return"},
                    "region": {"type": "string", "description": "AWS region"},
                },
                ["s3_output_path", "s3_bucket"],
            )
        ],
    },
]


def register_targets():
    print(f"Registering {len(TARGETS)} MCP tool targets on Gateway: {GATEWAY_ID}\n")

    created_ids = []
    for target_def in TARGETS:
        name = target_def["name"]
        lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{target_def['lambda_function']}"
        print(f"Registering: {name}")
        print(f"  Lambda: {lambda_arn}")

        try:
            response = client.create_gateway_target(
                gatewayIdentifier=GATEWAY_ID,
                name=name,
                description=target_def["description"],
                targetConfiguration={
                    "mcp": {
                        "lambda": {
                            "lambdaArn": lambda_arn,
                            "toolSchema": {
                                "inlinePayload": target_def["tools"],
                            },
                        }
                    }
                },
                credentialProviderConfigurations=[
                    {
                        "credentialProviderType": "GATEWAY_IAM_ROLE",
                    }
                ],
            )
            tid = response.get("targetId", "unknown")
            status = response.get("status", "unknown")
            print(f"  OK - ID: {tid}, Status: {status}")
            created_ids.append(tid)
        except client.exceptions.ConflictException:
            print("  SKIP - Already exists")
        except Exception as e:
            print(f"  FAIL - {e}")
        print()

    # Sync targets if any were created
    if created_ids:
        print("Synchronizing gateway targets...")
        try:
            client.synchronize_gateway_targets(
                gatewayIdentifier=GATEWAY_ID,
                targetIdList=created_ids,
            )
            print("OK - Sync initiated")
        except Exception as e:
            print(f"Sync note: {e}")
        print()

    # List all targets
    print("All registered targets:")
    try:
        response = client.list_gateway_targets(gatewayIdentifier=GATEWAY_ID)
        for t in response.get("targets", []):
            print(f"  {t.get('name')}: {t.get('targetId')} ({t.get('status')})")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    register_targets()
