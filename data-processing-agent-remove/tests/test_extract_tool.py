#!/usr/bin/env python3

import re

def extract_python_code(text: str) -> str:
    """Extract Python code from markdown-formatted text
    
    Args:
        text: Text containing Python code in markdown format
    
    Returns:
        Extracted Python code without markdown markers
    """
    
    # Remove thinking tags
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    
    # Extract code from markdown blocks
    code_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Try without language specifier
    code_match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Return as-is if no markdown found
    return text.strip()

# Test with sample text from the logs
test_text = '''```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

# Create SparkSession
spark = SparkSession.builder \\
    .appName("SampleDataFrame") \\
    .getOrCreate()

# Define schema
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("city", StringType(), True),
    StructField("salary", IntegerType(), True)
])

# Create sample data
data = [
    (1, "Alice Johnson", 28, "New York", 75000),
    (2, "Bob Smith", 35, "Los Angeles", 85000),
    (3, "Carol White", 42, "Chicago", 95000),
    (4, "David Brown", 31, "Houston", 78000),
    (5, "Emma Davis", 26, "Phoenix", 68000),
    (6, "Frank Miller", 39, "Philadelphia", 88000),
    (7, "Grace Lee", 33, "San Antonio", 82000),
    (8, "Henry Wilson", 45, "San Diego", 98000),
    (9, "Iris Martinez", 29, "Dallas", 72000),
    (10, "Jack Taylor", 37, "San Jose", 91000)
]

# Create DataFrame
df = spark.createDataFrame(data, schema=schema)

# Display the DataFrame
print("Sample DataFrame:")
df.show()

# Display schema
print("\\nDataFrame Schema:")
df.printSchema()

# Display summary statistics
print("\\nDataFrame Summary:")
df.describe().show()

# Write results to S3
output_path = "s3://spark-data-260005718447-us-east-1/output/spark-session-edf04bcc87c4456ab8cfe2d14b332245"
df.write.mode("overwrite").csv(output_path, header=True)

print(f"\\nResults written to: {output_path}")
```'''

if __name__ == "__main__":
    print("Testing extract_python_code function...")
    result = extract_python_code(test_text)
    print("Extracted code:")
    print("=" * 50)
    print(result)
    print("=" * 50)
    print(f"Length: {len(result)} characters")
    print("Test completed successfully!")
