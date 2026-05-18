# Spark Code Interpreter - Execution Statistics (2026-05-18)

Performance profiling data collected from CloudWatch Logs on 2026-05-18.

**Environment:** AWS Account 914787431788, Region us-east-1, Environment dev  
**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)  
**Supervisor Agent:** `spark_supervisor_agent-LUFQfC7cMH`  
**Code Gen Agent:** `spark_code_generator-Q8EJ8p53TZ`  
**Architecture:** GraphBuilder single-graph (`generate_and_validate` → `csv_execution` / `glue_execution`)  
**Branch:** `agentcore-modularization`

---

## What Changed Since Last Run (2026-05-15)

| Change | Description |
|---|---|
| **GraphBuilder migration** | `invoke()` now builds a single 3-node graph with conditional edges instead of 3 separate single-node graphs chained by if/else |
| **Schema injection** | CSV header extracted in `prepare_csv_sample` and injected into code gen prompt — column names are exact |
| **Skip `extract_execution_logs` on success** | Agent system prompt instructs agent to jump directly to `fetch_spark_results` on success; `extract_execution_logs` only fires on failure |
| **`_prepare_sample` calculation fallback** | No `s3_input_path` + no `selected_tables` + no `spark_code` → returns `is_small=True, sample_path=''`; enables pure-calculation queries |
| **Node renamed** | `validation` → `generate_and_validate` |

---

## Summary Table

| # | File | Size | Rows | Query | Node Used | is_small | Duration | Tool Calls | Code Retries | Result |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `sample_sales.csv` | 1.7 KB | 4 | Total sales by region | generate_and_validate | True | 66–77s | 6 | **0** | ✅ |
| 2 | `employee_performance.csv` | 57 KB | 8 | Avg salary by department | generate_and_validate | True | 72s | 6 | **0** | ✅ |
| 3 | `employee_performance_large.csv` | 23 MB | 5 | Top 5 employees by performance rating + bonus | generate_and_validate | True | 72s | 6 | **0** | ✅ |

All runs used `generate_and_validate` node (all files ≤ 100 MB). No `csv_execution` node was triggered.

---

## Comparison vs. Baseline (2026-05-15)

| Metric | 2026-05-15 (baseline) | 2026-05-18 (GraphBuilder + schema injection) | Δ |
|---|---|---|---|
| sample_sales.csv (1.7 KB) | 125.0s | **66–77s** | **−48–59s (−40–47%)** |
| employee_performance_large.csv (23 MB) | 125.1s | **72s** | **−53s (−42%)** |
| Code retries (column mismatch) | 1 per run | **0** | **−100%** |
| Tool calls per run | 13 (with retry) | **6** | **−54%** |
| `extract_execution_logs` on success | Always called | **Never called** | Eliminated |

The performance gain comes from two independent improvements:
1. **Schema injection** eliminated all column-name mismatch retries (was the single biggest time cost: ~40s per retry including re-generation + re-execution)
2. **Skip `extract_execution_logs` on success** saved 4–6s per successful run

---

## Detailed Profiling: Run #1 (sample_sales.csv, 1.7 KB)

**Query:** "What is the total sales by region?"  
**File:** `sample_sales.csv` (1,737 bytes, 12 data rows → 4 result rows)  
**Session:** `21497729-8653-4335-a919-54637f75511b`  
**Duration:** ~66.5s (wrapper Lambda: 66,503 ms)  
**Path:** `_prepare_sample` (is_small=True) → graph → `generate_and_validate` → *(no execution node)*

### Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Notes |
|---|---|---|---|
| 19:02:44.639 | 0.0s | Sample ready | file_size=1,737B, is_small=True |
| 19:02:46.773 | 2.1s | Tool #1: call_code_generation_agent | Schema context injected; exact column names used |
| 19:03:00.044 | ~15s | Tool #2: extract_python_code | |
| 19:03:04.965 | ~20s | Tool #3: validate_spark_code | |
| 19:03:11.206 | ~27s | Tool #4: select_execution_platform | → Lambda |
| 19:03:13.568 | ~29s | Tool #5: execute_spark_code_lambda | ~26s execution |
| 19:03:39.403 | ~55s | Tool #6: fetch_spark_results | |
| 19:03:49.417 | ~65s | Result from node: generate_and_validate | |

**Code retries:** 0 — schema injection provided exact column names (`order_id, date, region, category, product, quantity, unit_price, total_sales`)

### Output

```
region,total_sales
North,13800.0
West,13380.0
South,12710.0
East,10670.0
```

---

## Detailed Profiling: Run #2 (employee_performance.csv, 57 KB)

**Query:** "Show average salary by department"  
**File:** `employee_performance.csv` (57,987 bytes)  
**Session:** `21ca0810-c45e-45aa-9561-a53ba689d6f7`  
**Duration:** 72.1s (wrapper Lambda: 72,096 ms)  
**Path:** `_prepare_sample` (is_small=True) → graph → `generate_and_validate`

### Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Notes |
|---|---|---|---|
| 19:07:40.336 | 0.0s | Sample ready | file_size=57,987B, is_small=True |
| 19:07:42.991 | 2.7s | Tool #1: call_code_generation_agent | |
| 19:07:55.394 | ~15s | Tool #2: extract_python_code | |
| 19:08:00.368 | ~20s | Tool #3: validate_spark_code | |
| 19:08:05.800 | ~25s | Tool #4: ensure_output_file_writing | |
| 19:08:11.099 | ~31s | Tool #5: select_execution_platform | → Lambda |
| 19:08:13.726 | ~33s | Tool #6: execute_spark_code_lambda | ~38s execution |
| ~19:08:51 | ~70s | Tool (implicit): fetch_spark_results | |
| 19:08:51.168 | ~71s | Result from node: generate_and_validate | |

**Code retries:** 0

### Output (8 departments)

```
department,average_salary
Engineering,158396.39
Finance,123950.91
HR,90688.36
Marketing,110100.61
Operations,99350.29
Product,138858.54
Sales,127320.66
Support,83617.77
```

---

## Detailed Profiling: Run #3 (employee_performance_large.csv, 23 MB)

**Query:** "Show top 5 employees by performance rating and their bonus amount"  
**File:** `employee_performance_large.csv` (23,638,369 bytes, ~200K rows)  
**Session:** `2d11f890-070c-47f4-b03f-783da7456a1a`  
**Duration:** 72.1s (wrapper Lambda: 72,108 ms)  
**Path:** `_prepare_sample` (is_small=True) → graph → `generate_and_validate`

### Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Notes |
|---|---|---|---|
| 19:09:45.628 | 0.0s | Sample ready | file_size=23,638,369B, is_small=True |
| 19:09:48.058 | 2.4s | Tool #1: call_code_generation_agent | |
| 19:10:00.612 | 15.0s | Tool #2: extract_python_code | |
| 19:10:03.901 | 18.3s | Tool #3: validate_spark_code | |
| 19:10:09.440 | 23.8s | Tool #4: select_execution_platform | → Lambda |
| 19:10:12.236 | 26.6s | Tool #5: execute_spark_code_lambda | ~29s execution |
| 19:10:41.024 | 55.4s | Tool #6: fetch_spark_results | |
| 19:10:44.400 | 58.8s | Result from node: generate_and_validate | |

**Code retries:** 0

### Output (top 5 by performance)

```
employee_id,first_name,last_name,performance_rating,bonus_amount
EMP000014,Paul,Thompson,Outstanding,27161.72
EMP000028,Linda,Harris,Outstanding,18685.55
EMP000029,Nancy,Williams,Outstanding,16133.48
EMP000035,Karen,Ramirez,Outstanding,15636.66
EMP000053,James,Rodriguez,Outstanding,13726.40
```

---

## Key Observations

### 1. Schema Injection: Zero Retries
The 2026-05-15 baseline had 1 retry per run due to column name mismatch (generated `salary` but schema has `base_salary`, generated `sales` but schema has `total_sales`). Schema injection injects the exact CSV header row into the code gen prompt. Zero retries across all 3 runs today.

### 2. Tool Call Count: 6 vs 13
Without retry: 6 tools. With retry (old): 13 tools (code gen × 2, extract/validate × 2, extract_execution_logs × 1, execute × 2, fetch_results × 1). The skip-on-success optimization also eliminated the `extract_execution_logs` call on successful runs.

### 3. Large File (23 MB) Same Speed as Small (1.7 KB)
Both 1.7 KB and 23 MB files completed in ~66–72s. The wrapper extracts a 100 MB byte-range sample for large files (the sample is still the full 23 MB file since it's under 100 MB), and the Spark execution time scales with the sample size rather than the original file size.

### 4. No 2-Phase Execution Triggered
All files today are ≤ 100 MB (`is_small=True`), so the `csv_execution` node was never triggered. The `generate_and_validate` node result is returned directly. A ≥ 100 MB file would trigger the `csv_execution` conditional edge (see 2026-05-15 Run #3: `large_sales.csv` 150 MB, 232.3s with 2-phase).
