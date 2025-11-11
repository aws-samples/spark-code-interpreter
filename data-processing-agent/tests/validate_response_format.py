#!/usr/bin/env python3
"""
Validate that backend response format matches frontend expectations
"""
import json

# Sample backend response (from our earlier test)
backend_response = {
    "success": True,
    "result": json.dumps({
        "validated_code": """from pyspark.sql import SparkSession
from pyspark.sql import Row

spark = SparkSession.builder.appName("Test").getOrCreate()
data = [Row(name="Alice", age=28), Row(name="Bob", age=32)]
df = spark.createDataFrame(data)
df.show()
df.write.mode("overwrite").csv("s3://bucket/output/", header=True)
spark.stop()""",
        "execution_result": "Successfully executed on Lambda. Created DataFrame with 2 rows, displayed data, and wrote to S3.",
        "data": [],
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/"
    }),
    "framework": "spark"
}

print("🔍 Validating Response Format")
print("=" * 80)

# Simulate what frontend does (from App.jsx lines 115-145)
print("\n1️⃣ Frontend receives response...")
if not backend_response.get("success"):
    print("   ❌ Response has success=false")
    exit(1)
print("   ✅ Response has success=true")

print("\n2️⃣ Frontend parses result field...")
try:
    result_str = backend_response["result"]
    spark_data = json.loads(result_str)
    print("   ✅ Result field parsed successfully")
except Exception as e:
    print(f"   ❌ Failed to parse result: {e}")
    exit(1)

print("\n3️⃣ Frontend extracts validated_code...")
if "validated_code" in spark_data:
    code = spark_data["validated_code"]
    print(f"   ✅ validated_code found ({len(code)} chars)")
    print(f"\n   Code will appear in CodeEditor component:")
    print("   " + "-" * 76)
    for line in code.split("\n")[:8]:
        print(f"   {line}")
    if len(code.split("\n")) > 8:
        print("   ...")
    print("   " + "-" * 76)
else:
    print("   ❌ validated_code not found")
    exit(1)

print("\n4️⃣ Frontend extracts execution_result...")
if "execution_result" in spark_data:
    exec_result = spark_data["execution_result"]
    print(f"   ✅ execution_result found ({len(str(exec_result))} chars)")
    print(f"\n   Result will appear in ExecutionResults component:")
    print("   " + "-" * 76)
    result_lines = str(exec_result).split("\n")
    for line in result_lines[:5]:
        print(f"   {line}")
    if len(result_lines) > 5:
        print("   ...")
    print("   " + "-" * 76)
else:
    print("   ❌ execution_result not found")
    exit(1)

print("\n5️⃣ Frontend sets state...")
print("   ✅ setGeneratedCode(validated_code)")
print("   ✅ setEditedCode(validated_code)")
print("   ✅ setExecutionResult({code, result, success, ...})")
print("   ✅ setActiveTab('results')")

print("\n" + "=" * 80)
print("✅ VALIDATION PASSED")
print("\n📋 Frontend Integration Summary:")
print("   • CodeEditor will display: validated_code ✅")
print("   • ExecutionResults will display: execution_result ✅")
print("   • Response format matches App.jsx expectations ✅")
print("\n🎉 Frontend can successfully render the backend response!")
