"""Quick verification of output file fix"""
import json

# Sample response from test
response1 = '{"spark_code": "from pyspark.sql import SparkSession\\nimport json\\n\\n# Initialize Spark session\\nspark = SparkSession.builder \\\\\\n    .appName(\\"SimpleCalculation\\") \\\\\\n    .getOrCreate()\\n\\n# Calculate 7 times 10\\nresult = 7 * 10\\n\\n# Print the result\\nprint(f\\"Result: 7 times 10 = {result}\\")\\n\\n# Create a DataFrame with the result\\nfrom pyspark.sql import Row\\nresult_data = [Row(calculation=\\"7 * 10\\", result=result)]\\nresult_df = spark.createDataFrame(result_data)\\n\\n# Show the result\\nresult_df.show()\\n\\n# Write results to S3\\noutput_path = \\"s3://spark-code-execution-output-bucket/test-simple-calc-055149f3ba2f4a9aacc6c03f368a832d/\\"\\nresult_df.coalesce(1).write.mode(\\"overwrite\\").csv(output_path, header=True)\\n\\nprint(f\\"Results written to {output_path}\\")\\n\\n# Write results to /tmp/output.json for Lambda\\noutput_data = result_df.collect()\\noutput_json = [row.asDict() for row in output_data]\\nwith open(\'/tmp/output.json\', \'w\') as f:\\n    json.dump(output_json, f)\\n\\n# Stop Spark session\\nspark.stop()"}'

# Parse the JSON
parsed = json.loads(response1)
spark_code = parsed['spark_code']

print("="*80)
print("EXTRACTED SPARK CODE:")
print("="*80)
print(spark_code)
print("="*80)

# Check for output file requirements
checks = {
    'has_json_import': 'import json' in spark_code,
    'has_output_file': '/tmp/output.json' in spark_code,
    'has_json_dump': 'json.dump(' in spark_code,
    'has_with_open': "with open('/tmp/output.json'" in spark_code
}

print("\n🔍 Output File Checks:")
for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"  {status} {check}: {passed}")

all_passed = all(checks.values())

if all_passed:
    print("\n✅ ALL CHECKS PASSED - Code includes output file writing!")
else:
    print("\n⚠️ SOME CHECKS FAILED")
