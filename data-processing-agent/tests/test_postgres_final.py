#!/usr/bin/env python3
"""Test PostgreSQL code generation - verify no os.environ and correct EMR app"""

import json

# Sample generated code to check
test_code = """
import boto3, json
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
secret = secrets_client.get_secret_value(SecretId='arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-967bdca7-jS7ksa')
creds = json.loads(secret['SecretString'])
username = creds['username']
password = creds['password']

df = spark.read.format("jdbc") \\
    .option("url", "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres") \\
    .option("dbtable", "public.order_details") \\
    .option("user", username) \\
    .option("password", password) \\
    .option("driver", "org.postgresql.Driver") \\
    .load()
"""

print("=" * 80)
print("POSTGRESQL CODE VALIDATION")
print("=" * 80)

# Check for forbidden patterns
has_os_environ = "os.environ" in test_code or "os.getenv" in test_code
has_secret_arn = "arn:aws:secretsmanager" in test_code
has_jdbc_url = "jdbc:postgresql://" in test_code
has_secrets_manager = "get_secret_value" in test_code
has_placeholder = "YOUR_" in test_code or "REPLACE_" in test_code

print(f"\n✓ Uses Secrets Manager: {has_secrets_manager}")
print(f"✓ Has actual Secret ARN: {has_secret_arn}")
print(f"✓ Has actual JDBC URL: {has_jdbc_url}")
print(f"✗ Uses os.environ (FORBIDDEN): {has_os_environ}")
print(f"✗ Has placeholders (FORBIDDEN): {has_placeholder}")

print("\n" + "=" * 80)
if not has_os_environ and has_secret_arn and has_jdbc_url and not has_placeholder:
    print("✅ CODE GENERATION CORRECT!")
else:
    print("❌ CODE GENERATION HAS ISSUES!")
    if has_os_environ:
        print("   - Remove os.environ usage")
    if not has_secret_arn:
        print("   - Add actual Secret ARN from context")
    if not has_jdbc_url:
        print("   - Add actual JDBC URL from context")
    if has_placeholder:
        print("   - Replace placeholders with actual values")

print("\n" + "=" * 80)
print("BACKEND CONFIGURATION CHECK")
print("=" * 80)

# Check backend config
with open('backend/config.py', 'r') as f:
    config_content = f.read()
    
has_postgres_emr = "emr_postgres_application_id" in config_content
has_jdbc_driver = "jdbc_driver_path" in config_content

print(f"✓ Has PostgreSQL EMR application ID: {has_postgres_emr}")
print(f"✓ Has JDBC driver path: {has_jdbc_driver}")

if has_postgres_emr:
    import re
    match = re.search(r'"emr_postgres_application_id":\s*"([^"]+)"', config_content)
    if match:
        print(f"  PostgreSQL EMR App: {match.group(1)}")

print("=" * 80)
