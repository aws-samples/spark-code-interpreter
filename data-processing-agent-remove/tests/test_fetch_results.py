#!/usr/bin/env python3
"""Test script to debug fetch_spark_results issue"""

import sys
import os
import json
import re

# Add the current directory to Python path
sys.path.insert(0, './backend/spark-supervisor-agent')

def test_s3_path_extraction():
    """Test S3 path extraction logic from Spark code"""
    
    # Test cases for different Spark code patterns
    test_cases = [
        {
            'name': 'Simple CSV write',
            'code': '''
df.write.mode("overwrite").csv("s3://spark-data-260005718447-us-east-1/output/top_10_closing/")
            ''',
            'expected': 's3://spark-data-260005718447-us-east-1/output/top_10_closing/'
        },
        {
            'name': 'Variable-based write',
            'code': '''
output_path = "s3://spark-data-260005718447-us-east-1/output/results/"
df.write.csv(output_path)
            ''',
            'expected': 's3://spark-data-260005718447-us-east-1/output/results/'
        },
        {
            'name': 'Parquet write',
            'code': '''
result_df.write.mode("overwrite").parquet("s3://spark-data-260005718447-us-east-1/output/analysis/")
            ''',
            'expected': 's3://spark-data-260005718447-us-east-1/output/analysis/'
        }
    ]
    
    def extract_s3_path_from_code(spark_code):
        """Extract S3 output path from Spark code"""
        # Look for .write.csv() or .write.parquet() calls
        patterns = [
            r'\.write\.(?:mode\([^)]+\)\.)?csv\(["\']([^"\']+)["\']',
            r'\.write\.(?:mode\([^)]+\)\.)?parquet\(["\']([^"\']+)["\']',
            r'output_path\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, spark_code)
            if match:
                return match.group(1)
        
        return None
    
    print("Testing S3 path extraction logic:")
    print("=" * 50)
    
    for test_case in test_cases:
        extracted = extract_s3_path_from_code(test_case['code'])
        status = "✓ PASS" if extracted == test_case['expected'] else "✗ FAIL"
        print(f"{status} {test_case['name']}")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Extracted: {extracted}")
        print()

def test_fetch_spark_results_logic():
    """Test the fetch_spark_results function logic"""
    print("Testing fetch_spark_results function:")
    print("=" * 50)
    
    # Import the function
    try:
        from spark_supervisor_agent import fetch_spark_results
        print("✓ Successfully imported fetch_spark_results")
        
        # Test with a known S3 path (should return no recent files)
        test_path = "s3://spark-data-260005718447-us-east-1/output/test/"
        result = fetch_spark_results(test_path, max_rows=10)
        
        print(f"Test result for {test_path}:")
        print(f"  Status: {result.get('status')}")
        print(f"  Data count: {len(result.get('data', []))}")
        print(f"  Message: {result.get('message', 'No message')}")
        
    except Exception as e:
        print(f"✗ Error importing or testing fetch_spark_results: {e}")

if __name__ == "__main__":
    test_s3_path_extraction()
    test_fetch_spark_results_logic()
