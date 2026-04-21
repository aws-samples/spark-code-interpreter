#!/usr/bin/env python3
"""Generate the Spark Code Interpreter architecture diagram with modular MCP tools."""

import os
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.ml import Sagemaker, Bedrock
from diagrams.aws.analytics import EMRCluster, GlueDataCatalog
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito, SecretsManager
from diagrams.aws.management import Cloudwatch
from diagrams.aws.integration import Eventbridge
from diagrams.aws.general import Users
from diagrams.aws.network import APIGateway

OUTPUT_DIR = "images"

with Diagram(
    "Spark Code Interpreter - Modular MCP Architecture",
    filename=f"{OUTPUT_DIR}/architecture-mcp",
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "28",
        "bgcolor": "white",
        "pad": "0.5",
        "nodesep": "0.8",
        "ranksep": "1.2",
    },
):
    user = Users("Business\nUser")

    with Cluster("Authentication"):
        cognito = Cognito("Cognito\nUser Pool")

    wrapper = Lambda("Wrapper\nLambda")

    with Cluster("AgentCore Runtime"):
        supervisor = Sagemaker("Spark Supervisor\nAgent\n(Orchestrator)")

    with Cluster("MCP Tool Lambdas\n(one Lambda per tool)"):
        codegen_tool = Lambda("generate\nspark code")
        exec_lambda_tool = Lambda("execute spark\non Lambda")
        exec_emr_tool = Lambda("execute spark\non EMR")
        glue_schema_tool = Lambda("get Glue\ntable schema")
        pg_schema_tool = Lambda("get Postgres\ntable schema")
        fetch_results_tool = Lambda("fetch spark\nresults")

    with Cluster("AgentCore Gateway\n(MCP Protocol)"):
        gateway = APIGateway("MCP\nGateway")

    with Cluster("Execution Backends"):
        spark_lambda = Lambda("Spark on\nLambda (SoAL)")
        emr = EMRCluster("EMR\nServerless")

    with Cluster("Code Generation"):
        codegen_agent = Sagemaker("Code Gen\nAgent\n(AgentCore)")
        bedrock = Bedrock("Amazon\nBedrock\n(Claude)")

    with Cluster("Data Sources"):
        s3 = S3("S3 Bucket\n(Data + Results)")
        glue_catalog = GlueDataCatalog("Glue Data\nCatalog")
        secrets = SecretsManager("Secrets\nManager")

    with Cluster("Observability"):
        cloudwatch = Cloudwatch("CloudWatch\nLogs")
        eventbridge = Eventbridge("EventBridge\nAlerts")

    # User -> Wrapper Lambda -> AgentCore Runtime (direct, not via Gateway)
    user >> Edge(label="prompt") >> wrapper
    wrapper >> Edge(label="invoke_agent_runtime\n(direct)") >> supervisor

    # External MCP clients -> Gateway -> same tool Lambdas
    user >> Edge(label="MCP client\n(optional)", style="dashed", color="gray") >> cognito
    cognito >> Edge(style="dashed", color="gray") >> gateway
    gateway >> Edge(label="routes to\ntool Lambdas", style="dashed", color="gray") >> codegen_tool

    # Supervisor -> MCP Tool Lambdas (direct lambda:InvokeFunction)
    supervisor >> Edge(label="lambda:Invoke") >> codegen_tool
    supervisor >> Edge(label="lambda:Invoke") >> exec_lambda_tool
    supervisor >> Edge(label="lambda:Invoke") >> exec_emr_tool
    supervisor >> Edge(label="lambda:Invoke") >> glue_schema_tool
    supervisor >> Edge(label="lambda:Invoke") >> pg_schema_tool
    supervisor >> Edge(label="lambda:Invoke") >> fetch_results_tool

    # MCP Tools -> Backends
    codegen_tool >> codegen_agent
    codegen_agent >> bedrock
    exec_lambda_tool >> spark_lambda
    exec_emr_tool >> emr
    glue_schema_tool >> glue_catalog
    pg_schema_tool >> secrets
    fetch_results_tool >> s3

    # Execution backends -> S3
    spark_lambda >> s3
    emr >> s3

    # Observability
    supervisor >> Edge(style="dotted", color="gray") >> cloudwatch
    cloudwatch >> Edge(style="dotted", color="gray") >> eventbridge
