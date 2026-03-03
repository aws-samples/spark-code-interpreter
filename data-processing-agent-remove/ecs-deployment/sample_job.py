import ray
import time

# This script runs directly on the Ray cluster
ray.init(address="auto")

print("="*50)
print("Ray Data Processing Job")
print("="*50)

# Test 1: Basic data processing
print("\n1. Creating dataset...")
ds = ray.data.range(1000)
print(f"   Created dataset with {ds.count()} rows")

# Test 2: Map transformation
print("\n2. Applying transformations...")
ds_transformed = ds.map(lambda x: {"id": x["id"], "squared": x["id"] ** 2, "cubed": x["id"] ** 3})
sample = ds_transformed.take(5)
print(f"   Sample results:")
for row in sample:
    print(f"     {row}")

# Test 3: Filtering
print("\n3. Filtering data...")
ds_filtered = ds_transformed.filter(lambda x: x["id"] % 100 == 0)
print(f"   Filtered to {ds_filtered.count()} rows")

# Test 4: Batch processing
print("\n4. Batch processing with pandas...")
def process_batch(batch):
    import pandas as pd
    df = pd.DataFrame(batch)
    df['sum'] = df['squared'] + df['cubed']
    return df

ds_batch = ds_transformed.map_batches(process_batch, batch_format="pandas")
print(f"   Processed {ds_batch.count()} rows")
print(f"   Sample:")
for row in ds_batch.take(3):
    print(f"     {row}")

# Test 5: Aggregation
print("\n5. Aggregation...")
data = [{"category": i % 5, "value": i * 10} for i in range(100)]
ds_agg = ray.data.from_items(data)
result = ds_agg.groupby("category").count()
print(f"   Group counts:")
for row in result.take_all():
    print(f"     Category {row['category']}: {row['count()']} items")

print("\n" + "="*50)
print("Job completed successfully!")
print("="*50)
print(f"Cluster resources: {ray.cluster_resources()}")
print(f"Available nodes: {len(ray.nodes())}")
