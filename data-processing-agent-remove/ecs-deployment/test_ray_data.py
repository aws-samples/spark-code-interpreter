#!/usr/bin/env python3
"""Test Ray Data processing on ECS cluster"""

import ray
import sys

if len(sys.argv) < 2:
    print("Usage: python test_ray_data.py <HEAD_NODE_PUBLIC_IP>")
    sys.exit(1)

head_ip = sys.argv[1]

print(f"Connecting to Ray cluster at {head_ip}...")
ray.init(f"ray://{head_ip}:10001")

print(f"\nRay cluster resources: {ray.cluster_resources()}")
print(f"Available nodes: {len(ray.nodes())}")

# Test 1: Basic Ray Data operations
print("\n" + "="*50)
print("Test 1: Basic Ray Data Operations")
print("="*50)

# Create a simple dataset
ds = ray.data.range(1000)
print(f"Created dataset with {ds.count()} rows")

# Map operation
ds_squared = ds.map(lambda x: {"value": x["id"], "squared": x["id"] ** 2})
print(f"Applied map transformation")

# Show first few rows
print("\nFirst 5 rows:")
for row in ds_squared.take(5):
    print(f"  {row}")

# Test 2: Filtering and aggregation
print("\n" + "="*50)
print("Test 2: Filtering and Aggregation")
print("="*50)

# Filter even numbers
ds_even = ds_squared.filter(lambda x: x["value"] % 2 == 0)
print(f"Filtered to even numbers: {ds_even.count()} rows")

# Test 3: Groupby and aggregate
print("\n" + "="*50)
print("Test 3: GroupBy Operations")
print("="*50)

# Create dataset with categories
data = [{"category": i % 5, "value": i} for i in range(100)]
ds_grouped = ray.data.from_items(data)

# Group by category and count
result = ds_grouped.groupby("category").count()
print("Grouped by category:")
for row in result.take_all():
    print(f"  Category {row['category']}: {row['count()']} items")

# Test 4: Batch processing
print("\n" + "="*50)
print("Test 4: Batch Processing")
print("="*50)

def process_batch(batch):
    import pandas as pd
    df = pd.DataFrame(batch)
    df['processed'] = df['id'] * 2 + 1
    return df

ds_batch = ray.data.range(100)
ds_processed = ds_batch.map_batches(process_batch, batch_format="pandas")
print("Applied batch processing")
print("\nFirst 5 processed rows:")
for row in ds_processed.take(5):
    print(f"  {row}")

# Test 5: Reading from Python objects (simulating S3/data source)
print("\n" + "="*50)
print("Test 5: Data Pipeline")
print("="*50)

# Simulate a data processing pipeline
pipeline_data = [
    {"user_id": i, "score": i * 10, "category": "A" if i % 2 == 0 else "B"}
    for i in range(1000)
]

ds_pipeline = ray.data.from_items(pipeline_data)

# Multi-step pipeline
result = (ds_pipeline
    .filter(lambda x: x["score"] > 500)
    .map(lambda x: {**x, "score_normalized": x["score"] / 1000})
    .groupby("category")
    .count())

print("Pipeline result:")
for row in result.take_all():
    print(f"  {row}")

print("\n" + "="*50)
print("All Ray Data tests completed successfully!")
print("="*50)
print(f"\nCluster is ready for data processing workloads.")
print(f"Dashboard: http://{head_ip}:8265")

ray.shutdown()
