# Spark Code Interpreter - Execution Statistics

Performance profiling data collected from CloudWatch Logs on 2026-05-06.

**Environment:** AWS Account 914787431788, Region us-east-1, Environment dev  
**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)  
**Supervisor Agent:** `spark_supervisor_agent-LUFQfC7cMH`  
**Code Gen Agent:** `spark_code_generator-Q8EJ8p53TZ`

---

## Summary Table

| # | Data Source | File Size | Rows | Query | Execution Platform | Total Time | Iterations | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | Glue: `spark_test_db.sample_sales` | ~1 KB | 30 | Sum total_sales by category | Lambda (validation) + EMR (failed) | 413s | Multiple (auth issues) | Failed (first attempt) |
| 2 | Glue: `spark_test_db.sample_sales` | ~1 KB | 30 | Sum total_sales by category | Lambda (validation) + EMR | 87s | 1 | Success |
| 3 | Glue: `spark_test_db.sample_sales` | ~1 KB | 30 | Sum total_sales by category | Lambda (validation) + EMR | 285s | Multiple (retries) | Success |
| 4 | Glue: `spark_test_db.us_flights` | 565 MB | 5.8M | Avg departure_delay by airline, top 10 | EMR (3 iterations) | 181s | 3 | Success |
| 5 | Glue: `spark_test_db.us_flights` | 565 MB | 5.8M | Avg departure_delay by airline, top 10 | Lambda (validation) + EMR (failed) + Lambda | 108s | 1 | Success |
| 6 | Glue: `spark_test_db.us_flights` | 565 MB | 5.8M | Avg departure_delay by airline, top 10 | EMR + Lambda (4 code gen iterations) | 255s | 4 | Success |
| 7 | CSV: `employee_performance.csv` | 22.5 MB | 200K | Avg base_salary by department | Lambda (2-phase: sample + full) | 99s | 1 | Success |
| 8 | CSV: `employee_performance.csv` | 22.5 MB | 200K | Count by dept & performance_rating | Lambda (2-phase: sample + full) | 117s | 1 | Success |

---

## Detailed Profiling: Run #7 (CSV 22.5MB, 2-Phase Lambda)

**Query:** "Calculate the average base_salary grouped by department, ordered descending"  
**File:** `employee_performance.csv` (22.5 MB, 200,000 rows)  
**Total Time:** 99.4s (wrapper Lambda duration)  
**Agent Time:** 98.4s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 21:12:17.301 | 0.0s | Wrapper Lambda START | — | Cold start: 440ms |
| 21:12:17.865 | 0.6s | Sample extraction (S3) | 0.6s | Read 100KB, extract 200 rows, write to S3 |
| 21:12:18.295 | 1.0s | Agent config loaded | 0.4s | AgentCore routing + container warm-up |
| 21:12:21.045 | 3.7s | LLM Reasoning #1 | 2.8s | Decides on 2-phase approach |
| 21:12:21.358 | 4.1s | **Tool #1: call_code_generation_agent** | 10.0s | Code Gen Agent (5.1s actual) |
| 21:12:31.283 | 14.0s | **Tool #2: extract_python_code** | 4.3s | LLM reasoning + extraction |
| 21:12:35.578 | 18.3s | **Tool #3: validate_spark_code** | 4.9s | LLM reasoning + validation |
| 21:12:40.479 | 23.2s | **Tool #4: execute_spark_code_lambda** (VALIDATION) | 28.3s | Sample 200 rows |
| 21:13:08.765 | 51.5s | LLM Reasoning #2 | 0.8s | Decides Phase 2 |
| 21:13:09.546 | 52.2s | **Tool #5: select_execution_platform** | 4.5s | LLM reasoning + S3 HEAD |
| 21:13:14.047 | 56.7s | **Tool #6: execute_spark_code_lambda** (PRODUCTION) | 24.0s | Full 200K rows |
| 21:13:38.016 | 80.7s | **Tool #7: extract_execution_logs** | 7.0s | CloudWatch query |
| 21:13:45.045 | 87.7s | **Tool #8: fetch_spark_results** | 4.7s | S3 read (cold start 344ms) |
| 21:13:49.741 | 92.4s | LLM Final Response | 7.0s | JSON formatting (streaming) |
| 21:13:56.708 | 99.4s | Agent complete | — | |

### Lambda Execution Details

| Invocation | Lambda | Duration | Init | Memory Used | Notes |
|---|---|---|---|---|---|
| Validation (200 rows) | dev-spark-on-lambda | 19.5s | 518ms (cold) | 1468 MB | Spark init dominates |
| Production (200K rows) | dev-spark-on-lambda | 17.6s | — (warm) | 1468 MB | Warm start, similar time |
| MCP Tool (validation) | dev-spark-tool-execute-spark-on-lambda | 22.6s | 307ms (cold) | 96 MB | Wraps Spark Lambda |
| MCP Tool (production) | dev-spark-tool-execute-spark-on-lambda | 18.2s | — (warm) | 96 MB | Wraps Spark Lambda |
| Fetch Results | dev-spark-tool-fetch-spark-results | 126ms | 344ms (cold) | 66 MB | S3 read only |

### Time Breakdown by Category

| Category | Time | % | Details |
|---|---|---|---|
| LLM Reasoning (between tools) | ~27s | 27% | 5 reasoning steps × ~5s avg |
| Spark Execution (Validation) | ~23s | 23% | Sample 200 rows on Lambda |
| Spark Execution (Production) | ~18s | 18% | Full 200K rows on Lambda |
| Code Generation | ~10s | 10% | Code Gen Agent (5s) + supervisor overhead |
| Log Extraction | ~7s | 7% | CloudWatch Logs Insights query |
| Tool Invocation Overhead | ~8s | 8% | Cold starts, MCP Lambda routing |
| Result Fetching | ~5s | 5% | S3 read + cold start |
| Other (config, routing) | ~2s | 2% | AgentCore routing, sample extraction |

---

## Detailed Profiling: Run #8 (CSV 22.5MB, 2-Phase Lambda, Second Query)

**Query:** "Count the number of employees grouped by department and performance_rating. Show all combinations."  
**File:** `employee_performance.csv` (22.5 MB, 200,000 rows)  
**Total Time:** 118.8s (wrapper Lambda duration)  
**Agent Time:** 117.0s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 21:33:40.922 | 0.0s | Wrapper Lambda START | — | Cold start: 461ms |
| 21:33:46.313 | 5.4s | **Tool #1: call_code_generation_agent** | 12.6s | Code generation |
| 21:33:58.902 | 18.0s | **Tool #2: extract_python_code** | 4.5s | |
| 21:34:03.421 | 22.5s | **Tool #3: validate_spark_code** | 5.2s | |
| 21:34:08.594 | 27.7s | **Tool #4: execute_spark_code_lambda** (VALIDATION) | 30.1s | Sample 200 rows |
| 21:34:38.669 | 57.7s | **Tool #5: select_execution_platform** | 3.9s | |
| 21:34:42.547 | 61.6s | **Tool #6: execute_spark_code_lambda** (PRODUCTION) | 26.9s | Full 200K rows |
| 21:35:09.493 | 88.6s | **Tool #7: extract_execution_logs** | 13.6s | |
| 21:35:23.115 | 102.2s | **Tool #8: fetch_spark_results** | 16.6s | |
| 21:35:39.677 | 118.8s | Agent complete | — | |

---

## Detailed Profiling: Run #2 (Glue sample_sales, Small Table)

**Query:** "Query the Glue table spark_test_db.sample_sales and show the sum of total_sales grouped by category"  
**Table:** `spark_test_db.sample_sales` (~1 KB, 30 rows)  
**Total Time:** 96.5s (wrapper Lambda duration)  
**Agent Time:** 86.9s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 18:45:12.548 | 0.0s | Wrapper Lambda START | — | Cold start: 433ms |
| 18:45:24.403 | 11.9s | **Tool #1: fetch_glue_table_schema** | 2.6s | Schema + 200-row sample extraction |
| 18:45:27.032 | 14.5s | **Tool #2: call_code_generation_agent** | 10.8s | Code generation |
| 18:45:37.834 | 25.3s | **Tool #3: extract_python_code** | 4.1s | |
| 18:45:41.982 | 29.4s | **Tool #4: validate_spark_code** | 4.6s | |
| 18:45:46.582 | 34.0s | **Tool #5: execute_spark_code_lambda** (VALIDATION) | 45.0s | Sample on Lambda |
| 18:46:31.580 | 79.0s | **Tool #6: execute_spark_code_emr** (PRODUCTION) | 17.4s | EMR execution |
| 18:46:48.987 | 96.4s | Agent complete | — | |

### Notes
- Validation on Lambda took 45s (cold start + Spark init)
- EMR production execution took only 17.4s (EMR was already warm)
- No retries needed — code was correct on first attempt

---

## Detailed Profiling: Run #5 (Glue us_flights 565MB, Best Run)

**Query:** "Query the Glue table spark_test_db.us_flights (565MB, ~5.8M rows) and show the average departure_delay grouped by airline, ordered by delay descending. Show top 10 airlines."  
**Table:** `spark_test_db.us_flights` (565 MB, 5.8M rows)  
**Total Time:** 108.7s (wrapper Lambda duration)  
**Agent Time:** 108.1s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 19:34:16.192 | 0.0s | Wrapper Lambda START | — | Cold start: 430ms |
| 19:34:19.119 | 2.9s | **Tool #1: fetch_glue_table_schema** | 7.1s | Schema + sample extraction from Parquet |
| 19:34:26.244 | 10.1s | **Tool #2: call_code_generation_agent** | 15.5s | Code generation |
| 19:34:41.763 | 25.6s | **Tool #3: extract_python_code** | 5.2s | |
| 19:34:46.952 | 30.8s | **Tool #4: validate_spark_code** | 6.7s | |
| 19:34:53.667 | 37.5s | **Tool #5: execute_spark_code_emr** | 9.6s | EMR failed (code issue) |
| 19:35:03.254 | 47.1s | **Tool #6: execute_spark_code_lambda** (VALIDATION) | 45.9s | Validation with sample on Lambda |
| 19:35:49.154 | 93.0s | **Tool #7: fetch_spark_results** | 15.7s | |
| 19:36:04.829 | 108.6s | Agent complete | — | |

### Notes
- First EMR attempt failed (code issue), agent switched to Lambda validation with sample
- Lambda validation with sample succeeded (45.9s includes cold start + Spark init)
- No production EMR re-execution in this run (agent returned Lambda results)
- This was the fastest successful run for the 565MB dataset

---

## Detailed Profiling: Run #4 (Glue us_flights 565MB, With Retries)

**Query:** Same as Run #5  
**Table:** `spark_test_db.us_flights` (565 MB, 5.8M rows)  
**Total Time:** 181.6s (wrapper Lambda duration)  
**Agent Time:** 180.8s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 19:25:18.288 | 0.0s | Wrapper Lambda START | — | |
| 19:25:21.258 | 3.0s | **Tool #1: fetch_glue_table_schema** | 7.9s | |
| 19:25:29.198 | 10.9s | **Tool #2: call_code_generation_agent** | 16.3s | 1st code gen |
| 19:25:45.520 | 27.2s | **Tool #3: extract_python_code** | 4.4s | |
| 19:25:49.962 | 31.7s | **Tool #4: validate_spark_code** | 9.0s | |
| 19:25:58.977 | 40.7s | **Tool #5: select_execution_platform** | 6.3s | → EMR |
| 19:26:05.233 | 46.9s | **Tool #6: execute_spark_code_emr** | 19.2s | EMR failed |
| 19:26:24.456 | 66.2s | **Tool #7: extract_execution_logs** | 5.0s | |
| 19:26:29.489 | 71.2s | **Tool #8: call_code_generation_agent** | 18.1s | 2nd code gen (fix) |
| 19:26:47.577 | 89.3s | **Tool #9: extract_python_code** | 6.3s | |
| 19:26:53.893 | 95.6s | **Tool #10: validate_spark_code** | 9.8s | |
| 19:27:03.671 | 105.4s | **Tool #11: execute_spark_code_emr** | 18.1s | EMR failed again |
| 19:27:21.758 | 123.5s | **Tool #12: extract_execution_logs** | 5.1s | |
| 19:27:26.833 | 128.5s | **Tool #13: call_code_generation_agent** | 17.4s | 3rd code gen (fix) |
| 19:27:44.248 | 146.0s | **Tool #14: extract_python_code** | 5.9s | |
| 19:27:50.104 | 151.8s | **Tool #15: execute_spark_code_emr** | 18.9s | EMR SUCCESS |
| 19:28:08.954 | 170.7s | **Tool #16: fetch_spark_results** | 10.9s | |
| 19:28:19.847 | 181.6s | Agent complete | — | |

### Notes
- Required 3 code generation iterations to produce correct EMR code
- Each EMR execution took ~18-19s (EMR was warm, fast turnaround)
- Each code gen iteration took ~16-18s (LLM reasoning + Code Gen Agent)
- Total overhead from retries: ~100s additional

---

## Detailed Profiling: Run #6 (Glue us_flights 565MB, Most Retries)

**Query:** Same as Run #4 and #5  
**Table:** `spark_test_db.us_flights` (565 MB, 5.8M rows)  
**Total Time:** 255.7s (wrapper Lambda duration)  
**Agent Time:** 255.2s (AgentCore invocation)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 19:44:34.846 | 0.0s | Wrapper Lambda START | — | |
| 19:44:37.479 | 2.6s | **Tool #1: fetch_glue_table_schema** | 8.3s | |
| 19:44:45.804 | 11.0s | **Tool #2: call_code_generation_agent** | 16.8s | 1st code gen |
| 19:45:02.606 | 27.8s | **Tool #3: extract_python_code** | 3.1s | |
| 19:45:05.749 | 30.9s | **Tool #4: validate_spark_code** | 11.6s | |
| 19:45:17.351 | 42.5s | **Tool #5: execute_spark_code_emr** | 8.6s | EMR failed |
| 19:45:25.985 | 51.1s | **Tool #6: call_code_generation_agent** | 11.3s | 2nd code gen |
| 19:45:37.251 | 62.4s | **Tool #7: extract_python_code** | 2.8s | |
| 19:45:40.052 | 65.2s | **Tool #8: validate_spark_code** | 4.7s | |
| 19:45:44.736 | 69.9s | **Tool #9: execute_spark_code_lambda** | 20.9s | Lambda validation |
| 19:46:05.616 | 90.8s | **Tool #10: call_code_generation_agent** | 19.4s | 3rd code gen |
| 19:46:25.050 | 110.2s | **Tool #11: extract_python_code** | 5.7s | |
| 19:46:30.710 | 115.9s | **Tool #12: validate_spark_code** | 7.8s | |
| 19:46:38.551 | 123.7s | **Tool #13: execute_spark_code_lambda** | 40.1s | Lambda (cold start) |
| 19:47:18.626 | 163.8s | **Tool #14: call_code_generation_agent** | 17.1s | 4th code gen |
| 19:47:35.688 | 180.8s | **Tool #15: extract_python_code** | 8.1s | |
| 19:47:43.795 | 189.0s | **Tool #16: execute_spark_code_lambda** | 38.5s | Lambda execution |
| 19:48:22.256 | 227.4s | **Tool #17: extract_execution_logs** | 3.5s | |
| 19:48:25.706 | 230.9s | **Tool #18: fetch_spark_results** | 24.9s | |
| 19:48:50.569 | 255.7s | Agent complete | — | |

### Notes
- Required 4 code generation iterations
- Mixed execution: EMR (failed) → Lambda validation → Lambda → Lambda (success)
- Longest run due to multiple retries and cold starts

---

## Component Latency Reference

### Spark Lambda (dev-spark-on-lambda)

| Metric | Cold Start | Warm Start |
|---|---|---|
| Lambda Init | 518ms | — |
| JVM + Spark Init | ~14s | ~14s |
| Actual Computation (200 rows) | ~2s | ~2s |
| Actual Computation (200K rows) | ~3-4s | ~3-4s |
| **Total (200 rows)** | **~19.5s** | **~17s** |
| **Total (200K rows)** | **~20s** | **~18s** |
| Memory Used | 1468 MB / 3008 MB | 1468 MB / 3008 MB |

### MCP Tool Lambda (dev-spark-tool-execute-spark-on-lambda)

| Metric | Cold Start | Warm Start |
|---|---|---|
| Lambda Init | 307ms | — |
| Invoke Spark Lambda + wait | ~22s | ~18s |
| **Total** | **~23s** | **~18s** |
| Memory Used | 96 MB / 256 MB | 96 MB / 256 MB |

### Code Generation Agent (spark_code_generator)

| Metric | Value |
|---|---|
| AgentCore routing | ~2-3s |
| LLM code generation | 5-8s |
| **Total** | **5-10s** |

### EMR Serverless

| Metric | Value |
|---|---|
| Job submission overhead | ~2s |
| Warm start execution (small query) | ~15-18s |
| Cold start execution | ~30-60s |
| 565MB dataset (5.8M rows, group by) | ~15-19s (warm) |

### Fetch Spark Results (dev-spark-tool-fetch-spark-results)

| Metric | Cold Start | Warm Start |
|---|---|---|
| Lambda Init | 344ms | — |
| S3 read + parse | 126ms | ~100ms |
| **Total** | **~470ms** | **~100ms** |

### LLM Reasoning Overhead (Supervisor Agent)

| Step | Avg Duration | Notes |
|---|---|---|
| Initial planning | 2-3s | Decides workflow approach |
| Between tool calls | 3-5s | Decides next tool + formats params |
| Final response formatting | 5-7s | Streams JSON response |
| **Per-tool overhead** | **~4s** | Added to each tool invocation |

---

## Optimization Opportunities

### Quick Wins (Low Effort, High Impact)

| # | Optimization | Potential Savings | Effort |
|---|---|---|---|
| 1 | Skip validation for simple queries (< 3 operations) | 23s per run | Medium |
| 2 | Skip `extract_execution_logs` on success | 7-14s per run | Low |
| 3 | Return print output inline from Spark Lambda response | Enables #2 | Low |
| 4 | Use Haiku for supervisor orchestration | ~15s per run | Low |

### Medium-Term (Higher Effort)

| # | Optimization | Potential Savings | Effort |
|---|---|---|---|
| 5 | Provisioned concurrency on Spark Lambda | 17s first call | $$$ |
| 6 | Lambda SnapStart (if supported for containers) | ~14s per call | Medium |
| 7 | Single-phase for small files (<50MB) | 23s per run | Medium |
| 8 | Reduce system prompt size | ~5s per run | Low |

### Key Insight: Spark Init Dominates

The JVM + SparkSession initialization (~14s) is the single largest fixed cost per Lambda invocation. The actual data processing for 200 rows vs 200K rows differs by only ~2s. This means:

- **Validation adds ~20s of pure overhead** (Spark init) for minimal benefit on simple queries
- **Two Lambda invocations** (validation + production) cost ~34s in Spark init alone
- **EMR warm execution** (~18s) is comparable to Lambda for medium datasets

### Projected Optimized Times

| Scenario | Current | With Skip Validation | With All Optimizations |
|---|---|---|---|
| Simple CSV query (22.5MB) | 99s | ~76s | ~45s |
| Complex CSV query (22.5MB) | 117s | 117s (keep validation) | ~80s |
| Glue table (small, 30 rows) | 87s | ~65s | ~40s |
| Glue table (565MB, first success) | 108s | 108s (EMR needed) | ~80s |
| Glue table (565MB, with retries) | 181-255s | 181-255s | 150-200s |
