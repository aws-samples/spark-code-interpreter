# Ray Native Processing - Distributed Computing Emphasis

## Issue

The code generator was producing code that used pandas for processing, with Ray only used for reading files. This defeats the purpose of using Ray's distributed framework.

**Example of WRONG approach:**
```python
import ray
ray.init(address='auto')

# Read with Ray
ds = ray.data.read_csv("s3://bucket/data.csv")

# Convert to pandas (BAD - loses distributed processing)
df = ds.to_pandas()

# Process with pandas (BAD - single machine)
df['squared'] = df['value'] * 2
result = df.groupby('category').sum()

print(result)
```

## Solution

Updated CodeGeneratorAgent system prompt to emphasize Ray-native distributed operations.

### Key Changes

1. **Explicit Warning Against Pandas**
   - NEVER use `to_pandas()`, `to_arrow()`
   - NEVER convert to pandas DataFrames
   - Use Ray Data APIs for ALL transformations

2. **Emphasis on Distributed Processing**
   - Ray is a DISTRIBUTED framework
   - Leverage parallelism
   - Use Ray-native operations

3. **Ray Data Operations Highlighted**
   - `.map()` - Row-wise transformations
   - `.map_batches()` - Batch operations (more efficient)
   - `.flat_map()` - One-to-many transformations
   - `.filter()` - Filter rows
   - `.groupby().map_groups()` - Distributed aggregations
   - `.repartition()` - Control parallelism

## Correct Ray-Native Patterns

### Pattern 1: Row-wise Transformation
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Transform each row (distributed)
ds_transformed = ds.map(lambda row: {
    'id': row['id'],
    'value': row['value'],
    'squared': row['value'] ** 2
})

# Show results
for row in ds_transformed.take(10):
    print(row)
```

### Pattern 2: Batch Operations (More Efficient)
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Process in batches (more efficient than row-by-row)
def process_batch(batch):
    # batch is a dict of arrays
    return {
        'id': batch['id'],
        'value': batch['value'],
        'squared': batch['value'] ** 2
    }

ds_transformed = ds.map_batches(process_batch)

print(f"Total rows: {ds_transformed.count()}")
```

### Pattern 3: Distributed Aggregation
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Group and aggregate (distributed)
def aggregate_group(group):
    total = sum(row['value'] for row in group)
    count = len(group)
    return {
        'category': group[0]['category'],
        'total': total,
        'count': count,
        'average': total / count
    }

result = ds.groupby('category').map_groups(aggregate_group)

for row in result.take_all():
    print(f"{row['category']}: total={row['total']}, avg={row['average']}")
```

### Pattern 4: Filtering
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Filter rows (distributed)
ds_filtered = ds.filter(lambda row: row['value'] > 100)

print(f"Filtered rows: {ds_filtered.count()}")
```

### Pattern 5: Chaining Operations
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Chain multiple operations (all distributed)
result = (ds
    .filter(lambda row: row['value'] > 0)
    .map(lambda row: {'category': row['category'], 'value': row['value'] * 2})
    .groupby('category')
    .map_groups(lambda group: {
        'category': group[0]['category'],
        'sum': sum(row['value'] for row in group)
    })
)

for row in result.take_all():
    print(row)
```

### Pattern 6: Controlling Parallelism
```python
import ray
ray.init(address='auto')

ds = ray.data.read_csv("s3://bucket/data.csv")

# Increase parallelism for large datasets
ds = ds.repartition(100)  # Split into 100 partitions

# Process in parallel
ds_processed = ds.map(lambda row: {
    'id': row['id'],
    'processed': expensive_computation(row['value'])
})

print(f"Processed {ds_processed.count()} rows in parallel")
```

## What NOT to Do

### ❌ WRONG: Converting to Pandas
```python
# BAD - Loses distributed processing
df = ds.to_pandas()
df['squared'] = df['value'] ** 2
```

### ❌ WRONG: Using Pandas Operations
```python
# BAD - Not distributed
import pandas as pd
df = pd.read_csv("s3://bucket/data.csv")
result = df.groupby('category').sum()
```

### ❌ WRONG: Collecting All Data First
```python
# BAD - Loads everything into memory
all_data = ds.take_all()
for row in all_data:
    process(row)  # Not distributed
```

## Benefits of Ray-Native Processing

### 1. Distributed Execution
- Operations run across multiple workers
- Scales to large datasets
- Automatic parallelization

### 2. Memory Efficiency
- Streaming processing
- No need to load entire dataset
- Handles data larger than memory

### 3. Fault Tolerance
- Automatic retry on failures
- Lineage tracking
- Resilient to worker failures

### 4. Performance
- Parallel execution
- Optimized data transfer
- Efficient batch processing

## Updated System Prompt

The CodeGeneratorAgent now includes:

```
CRITICAL - USE RAY NATIVE OPERATIONS:
- NEVER use pandas operations (to_pandas(), to_arrow(), etc.)
- NEVER convert to pandas DataFrames for processing
- ALWAYS use Ray Data APIs for ALL transformations
- Ray is a DISTRIBUTED framework - leverage parallelism

RAY DATA OPERATIONS (use these):
- .map() - Transform each row
- .map_batches() - Transform batches (more efficient)
- .flat_map() - One-to-many transformations
- .filter() - Filter rows
- .groupby().map_groups() - Distributed aggregations
- .repartition() - Control parallelism

WRONG - DON'T DO THIS:
✗ df = ds.to_pandas()  # Defeats distributed processing
✗ df.groupby()  # Use Ray's groupby instead
✗ df.apply()  # Use Ray's map instead
```

## Verification

```bash
python3 -c "
from agents import create_code_generator_agent
agent = create_code_generator_agent()
prompt = agent.system_prompt
assert 'DISTRIBUTED' in prompt
assert 'NEVER use pandas' in prompt
assert 'map_batches' in prompt
print('✅ Agent emphasizes Ray-native distributed processing')
"
```

## Summary

✅ **Updated CodeGeneratorAgent prompt**
✅ **Emphasizes Ray-native operations**
✅ **Warns against pandas usage**
✅ **Includes distributed processing patterns**
✅ **Highlights map_batches for efficiency**
✅ **Shows groupby().map_groups() for aggregations**
✅ **Mentions repartition() for parallelism**

The code generator now produces code that fully leverages Ray's distributed computing capabilities instead of falling back to pandas single-machine processing.
