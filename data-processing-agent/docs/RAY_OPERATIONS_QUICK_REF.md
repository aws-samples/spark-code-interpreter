# Ray Native Operations - Quick Reference

## ❌ DON'T Use Pandas

```python
# WRONG - Defeats distributed processing
df = ds.to_pandas()
df['new_col'] = df['old_col'] * 2
result = df.groupby('category').sum()
```

## ✅ DO Use Ray Data APIs

### Row Transformation
```python
ds.map(lambda row: {'id': row['id'], 'value': row['value'] * 2})
```

### Batch Transformation (More Efficient)
```python
ds.map_batches(lambda batch: {'sum': batch['value'].sum()})
```

### Filtering
```python
ds.filter(lambda row: row['value'] > 100)
```

### Aggregation
```python
ds.groupby('category').map_groups(lambda group: {
    'category': group[0]['category'],
    'total': sum(row['value'] for row in group)
})
```

### Increase Parallelism
```python
ds.repartition(100)  # Split into 100 partitions
```

### Chaining Operations
```python
ds.filter(...).map(...).groupby(...).map_groups(...)
```

## Key Operations

| Operation | Use Case | Example |
|-----------|----------|---------|
| `.map()` | Transform each row | `ds.map(lambda r: {'x': r['x'] * 2})` |
| `.map_batches()` | Batch processing | `ds.map_batches(process_batch)` |
| `.filter()` | Filter rows | `ds.filter(lambda r: r['x'] > 0)` |
| `.groupby()` | Group data | `ds.groupby('category')` |
| `.map_groups()` | Aggregate groups | `.map_groups(aggregate_fn)` |
| `.repartition()` | Control parallelism | `ds.repartition(100)` |
| `.take()` | Get N rows | `ds.take(10)` |
| `.take_all()` | Get all rows | `ds.take_all()` |
| `.count()` | Count rows | `ds.count()` |

## Remember

✅ All operations are **distributed**
✅ Use **Ray Data APIs** for transformations
✅ **Never** convert to pandas for processing
✅ Leverage **parallelism** with repartition
✅ Use **map_batches** for efficiency
