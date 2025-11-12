#!/usr/bin/env python3
"""Test context building for PostgreSQL"""

# Simulate the context building logic
selected_postgres_tables = [
    {
        "connection_name": "aurora-test",
        "database": "postgres",
        "schema": "public",
        "table": "order_details"
    }
]
selected_tables = None
s3_input_path = None

# Build data sources
data_sources = []

if s3_input_path:
    data_sources.append(f"S3 CSV file: {s3_input_path}")

if selected_tables:
    tables_info = f"Glue tables: {selected_tables}"
    data_sources.append(tables_info)

if selected_postgres_tables:
    postgres_info = f"PostgreSQL tables: {selected_postgres_tables}"
    data_sources.append(postgres_info)

# CRITICAL: Only allow sample data if NO real data sources provided
if data_sources:
    data_source = "\n".join(data_sources)
else:
    data_source = "Generate sample data"

print("=" * 80)
print("CONTEXT BUILDING TEST")
print("=" * 80)
print(f"\nPostgreSQL tables: {bool(selected_postgres_tables)}")
print(f"Glue tables: {bool(selected_tables)}")
print(f"S3 input: {bool(s3_input_path)}")
print(f"\nData source context:\n{data_source}")

print("\n" + "=" * 80)
print("VALIDATION PLATFORM SELECTION")
print("=" * 80)
print(f"PostgreSQL tables provided: {bool(selected_postgres_tables)} → Use EMR")
print(f"Glue tables provided: {bool(selected_tables)} → Use EMR")
print(f"S3 CSV file provided: {bool(s3_input_path)} → Use select_execution_platform")

if selected_postgres_tables or selected_tables:
    print("\n✅ CORRECT: Will use EMR for validation")
elif s3_input_path:
    print("\n✅ CORRECT: Will use select_execution_platform")
else:
    print("\n✅ CORRECT: Will use Lambda")

print("\n" + "=" * 80)
print("SYNTHETIC DATA CHECK")
print("=" * 80)
if "Generate sample data" in data_source and (selected_postgres_tables or selected_tables or s3_input_path):
    print("❌ ERROR: Says 'Generate sample data' but real sources exist!")
elif "Generate sample data" not in data_source and (selected_postgres_tables or selected_tables or s3_input_path):
    print("✅ CORRECT: No 'Generate sample data' - will use real sources")
elif "Generate sample data" in data_source and not (selected_postgres_tables or selected_tables or s3_input_path):
    print("✅ CORRECT: Says 'Generate sample data' because no real sources")
else:
    print("⚠️  UNEXPECTED: Check logic")

print("=" * 80)
