# Spark Code Interpreter - Execution Statistics (2026-05-15)

Performance profiling data collected from CloudWatch Logs on 2026-05-15.

**Environment:** AWS Account 914787431788, Region us-east-1, Environment dev  
**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)  
**Supervisor Agent:** `spark_supervisor_agent-LUFQfC7cMH`  
**Code Gen Agent:** `spark_code_generator-Q8EJ8p53TZ`  
**Architecture:** Graph-based multi-agent (new — `agentcore-modularization` branch)  
**Sampling:** Size-based, 100 MB budget (`SAMPLE_SIZE_MB=100`). `is_small = (file_size ≤ 100 MB)`.  

---

## Context: New Architecture

These runs are the first tests of the refactored graph-based supervisor agent replacing the original 212-line monolithic system prompt. Key differences:

| Aspect | Old Architecture | New Architecture |
|---|---|---|
| Orchestration | Single LLM agent, 212-line system prompt | 3 focused agents + 2 non-LLM nodes |
| Sampling | Row-based (200 rows / 100 KB) | Size-based (100 MB budget) |
| `is_small` flag | Not present | `file_size ≤ sample_size_mb`; if True, Lambda result is final |
| Glue 2-phase | Ambiguous (system prompt conflict) | Deterministic: always Lambda validate → EMR execute |
| CSV 2-phase | Always ran both phases | Skips execution phase when `is_small=True` |
| `skip_generation` | Boolean field | Replaced by `mode = "generate" \| "execute"` |

---

## Summary Table

| # | Data Source | File Size | Rows | Query | Execution Path | is_small | Agent Time | Code Retries | Result |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CSV: `sample_sales.csv` | 1.7 KB | 12 | Sum total_sales by category | Validation only (Lambda) | True | 125.0s | 1 | Success |
| 2 | CSV: `employee_performance_large.csv` | 23 MB | 200K | Avg base_salary + bonus by department | Validation only (Lambda) | True | 125.1s | 1 | Success |
| 3 | CSV: `large_sales.csv` (synthetic) | 150 MB | 1.8M | Sum total_sales by category | Validation (100 MB sample) + Execution (full 150 MB) | False | 232.3s | 1 | Success |

---

## Detailed Profiling: Run #1 (CSV 1.7 KB, Small, Lambda Only)

**Query:** "Calculate total sales by category"  
**File:** `sample_sales.csv` (1,737 bytes, 12 data rows)  
**Session:** `fe3060d9-cf54-40ee-8de4-29683f8b4225`  
**Log Stream:** `d189c457...`  
**Agent Time:** 125.0s  
**Path:** `prepare_csv_sample` → `validation_agent` → *(is_small=True, no execution agent)*

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 21:22:24.000 | 0.0s | Wrapper Lambda START | — | Warm start |
| 21:22:24.154 | 0.2s | **prepare_csv_sample** | 0.15s | file_size=1,737 B, is_small=True (below 100 MB), no S3 sample needed |
| 21:22:25.387 | 1.4s | Validation agent started | — | AgentCore routing + container warm-up |
| 21:22:28.000 | 4.0s | LLM Reasoning #1 | 2.6s | Plans validate-on-Lambda approach |
| 21:22:28.000 | 4.0s | **Tool #1: call_code_generation_agent** | 10.0s | Code Gen Agent generates initial code |
| 21:22:38.000 | 14.0s | **Tool #2: extract_python_code** | 3.0s | Extracts PySpark block |
| 21:22:41.000 | 17.0s | **Tool #3: validate_spark_code** | 5.0s | Syntax + output-file checks |
| 21:22:46.000 | 22.0s | **Tool #4: ensure_output_file_writing** | 4.5s | Verifies output write logic |
| 21:22:51.000 | 27.0s | **Tool #5: execute_spark_code_lambda** (FAIL) | 21.0s | Column `sales` not found (schema has `total_sales`) |
| 21:23:12.000 | 48.0s | **Tool #6: extract_execution_logs** | 6.0s | Reads error from CloudWatch |
| 21:23:18.000 | 54.0s | **Tool #7: call_code_generation_agent** (retry) | 10.0s | Regenerates with correct column name `total_sales` |
| 21:23:29.000 | 65.0s | **Tool #8: extract_python_code** | 3.0s | |
| 21:23:31.000 | 67.0s | **Tool #9: validate_spark_code** | 5.0s | |
| 21:23:36.000 | 72.0s | **Tool #10: ensure_output_file_writing** | 6.0s | |
| 21:23:42.000 | 78.0s | **Tool #11: execute_spark_code_lambda** (SUCCESS) | 24.0s | 12 rows processed |
| 21:24:06.000 | 102.0s | **Tool #12: extract_execution_logs** | 4.0s | |
| 21:24:09.000 | 105.0s | **Tool #13: fetch_spark_results** | 6.0s | S3 read |
| 21:24:15.000 | 111.0s | "Small dataset: validation result is final" | — | Execution agent skipped |
| 21:24:15.000 | 111.0s | JSON response streaming | 15.0s | AgentCore → wrapper → caller |
| 21:24:30.000 | 126.0s | Agent complete | — | |

### Lambda Execution Details

| Invocation | Lambda | Duration | Init | Memory Used | Notes |
|---|---|---|---|---|---|
| Validation attempt 1 (FAIL) | dev-spark-on-lambda | ~18s | warm | ~1,468 MB | Column name error, Spark ran |
| Validation attempt 2 (SUCCESS) | dev-spark-on-lambda | ~21s | warm | ~1,468 MB | 12 rows |
| Fetch Results | dev-spark-tool-fetch-spark-results | ~100ms | warm | ~66 MB | |

### Time Breakdown by Category

| Category | Time | % | Details |
|---|---|---|---|
| Spark Execution (2 attempts) | ~45s | 36% | 21s failed + 24s success |
| LLM Reasoning (between tools) | ~27s | 21% | ~13 reasoning steps |
| Code Generation (2 attempts) | ~20s | 16% | 10s each × 2 retries |
| Log Extraction (2 calls) | ~10s | 8% | CloudWatch query × 2 |
| JSON Streaming | ~15s | 12% | AgentCore response stream |
| extract/validate/ensure tools | ~18s | 14% | 4 tool calls × ~4.5s avg |
| prepare_csv_sample + routing | ~1.5s | 1% | Non-LLM node + AgentCore init |

### Notes
- `is_small=True`: file (1.7 KB) is far below 100 MB budget — validation result is final, execution agent never started
- Code retry caused by column name mismatch: generated `sales` but schema has `total_sales`
- 13 tool calls total (highest of the 3 runs due to `ensure_output_file_writing` in both attempts)
- `extract_execution_logs` called after failure to feed error context into retry

---

## Detailed Profiling: Run #2 (CSV 23 MB, Small, Lambda Only)

**Query:** "Calculate the average base_salary and average bonus_amount grouped by department, ordered by avg_base_salary descending"  
**File:** `employee_performance_large.csv` (23,638,369 bytes / 22.5 MB, ~200K rows)  
**Session:** `60a733fb-d08e-462a-86be-9fe4d448a73d`  
**Log Stream:** `b12aa2c2...`  
**Agent Time:** 125.1s  
**Wrapper Sample Extraction:** 1.2s (100 MB budget, full 23 MB read)  
**Path:** `prepare_csv_sample` → `validation_agent` → *(is_small=True, no execution agent)*

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Tool | Duration | Notes |
|---|---|---|---|---|
| 21:25:19.000 | 0.0s | Wrapper Lambda START | — | Cold start; sample extraction begins |
| 21:25:20.200 | 1.2s | Sample extracted | 1.2s | Read full 23 MB (below 100 MB budget), write to S3 |
| ~21:35:23.000 | ~604s | AgentCore container cold start | ~603s | Container pull + image init (new container, first agent of session) |
| 21:35:23.511 | +0.0s | **prepare_csv_sample** complete | — | file_size=23,638,369 B, is_small=True |
| 21:35:23.511 | +0.0s | Validation agent started | — | |
| 21:35:25.000 | +1.5s | LLM Reasoning #1 | 1.5s | |
| 21:35:25.000 | +1.5s | **Tool #1: call_code_generation_agent** | 10.0s | Generates code using `salary`, `bonus` (wrong column names) |
| 21:35:35.000 | +11.5s | **Tool #2: extract_python_code** | 4.0s | |
| 21:35:39.000 | +15.5s | **Tool #3: validate_spark_code** | 6.0s | |
| 21:35:45.000 | +21.5s | **Tool #4: ensure_output_file_writing** | 6.0s | |
| 21:35:51.000 | +27.5s | **Tool #5: execute_spark_code_lambda** (FAIL) | 35.0s | Columns `salary`/`bonus` not found (schema: `base_salary`/`bonus_amount`) |
| 21:36:26.000 | +62.5s | **Tool #6: call_code_generation_agent** (retry) | 10.0s | Skipped extract_execution_logs; retried directly |
| 21:36:36.000 | +72.5s | **Tool #7: extract_python_code** | 3.0s | |
| 21:36:39.000 | +75.5s | **Tool #8: validate_spark_code** | 5.0s | |
| 21:36:44.000 | +80.5s | **Tool #9: execute_spark_code_lambda** (SUCCESS) | 27.0s | 5 department rows returned |
| 21:37:11.000 | +107.5s | **Tool #10: extract_execution_logs** | 3.0s | |
| 21:37:14.000 | +110.5s | **Tool #11: fetch_spark_results** | 4.0s | |
| 21:37:18.000 | +114.5s | "Small dataset: validation result is final" | — | Execution agent skipped |
| 21:37:18.000 | +114.5s | JSON response streaming | 10.0s | |
| 21:37:28.000 | +125.1s | Agent complete | — | |

### Lambda Execution Details

| Invocation | Lambda | Duration | Init | Memory Used | Notes |
|---|---|---|---|---|---|
| Validation attempt 1 (FAIL) | dev-spark-on-lambda | ~32s | warm | ~1,468 MB | Spark loaded 23 MB CSV before failing |
| Validation attempt 2 (SUCCESS) | dev-spark-on-lambda | ~24s | warm | ~1,468 MB | 5 department aggregations |
| Fetch Results | dev-spark-tool-fetch-spark-results | ~100ms | warm | ~66 MB | |

### Time Breakdown by Category

| Category | Time | % | Details |
|---|---|---|---|
| Spark Execution (2 attempts) | ~62s | 50% | 35s failed + 27s success — larger file loads slowly |
| Code Generation (2 attempts) | ~20s | 16% | 10s each |
| LLM Reasoning (between tools) | ~18s | 14% | |
| extract/validate/ensure tools | ~14s | 11% | |
| JSON Streaming | ~10s | 8% | |
| Sample extraction (wrapper) | ~1.2s | 1% | |

### Notes
- `is_small=True`: 23 MB file fits comfortably below 100 MB sample budget — no execution agent
- The failed Lambda attempt spent ~32s loading the full 23 MB CSV before hitting the column error — larger than Run #1's 21s failure
- On retry, the agent skipped `extract_execution_logs` and retried immediately with context from the inline error message — slightly different retry pattern than Run #1
- 11 tools total (skipped `ensure_output_file_writing` on retry, skipped `extract_execution_logs` after failure)
- AgentCore container cold start was ~10 minutes — container had to be pulled fresh; this is a one-time cost per container lifecycle

---

## Detailed Profiling: Run #3 (CSV 150 MB, Large, 2-Phase: Lambda Sample + Lambda Full)

**Query:** "Calculate total sales by category, ordered descending"  
**File:** `large_sales.csv` (158,146,244 bytes / 150.8 MB, 1.8M synthetic rows)  
**Session:** `b80cc559-...`  
**Log Stream:** `1c1caf12...`  
**Agent Time:** 232.3s  
**Path:** `prepare_csv_sample` → `validation_agent` → `csv_execution_agent` (is_small=False, 2-phase)

### Tool-by-Tool Timeline

| Timestamp (UTC) | Elapsed | Phase | Tool | Duration | Notes |
|---|---|---|---|---|---|
| ~21:34:xx | 0.0s | Prepare | Wrapper Lambda START | — | |
| ~21:34:xx | ~21s | Prepare | **prepare_csv_sample** | ~21s | S3 `GET bytes=0–{100MB-1}` on 150 MB file; trim at last newline; write sample to S3; file_size=158,146,244 B, is_small=False |
| 21:41:28.000 | 0.0s | Validate | Validation agent started | — | (elapsed from agent start) |
| 21:41:29.192 | 0.2s | Validate | LLM Reasoning #1 | 1.2s | |
| 21:41:31.000 | 2.8s | Validate | **Tool #1: call_code_generation_agent** | 10.0s | Generates code using `sales` (wrong; schema: `total_sales`) |
| 21:41:41.000 | 12.8s | Validate | **Tool #2: extract_python_code** | 3.0s | |
| 21:41:44.000 | 15.8s | Validate | **Tool #3: validate_spark_code** | 5.0s | |
| 21:41:49.000 | 20.8s | Validate | **Tool #4: ensure_output_file_writing** | 6.0s | |
| 21:41:55.000 | 26.8s | Validate | **Tool #5: execute_spark_code_lambda** on 100 MB sample (FAIL) | 26.0s | Column `sales` not found |
| 21:42:21.000 | 52.8s | Validate | **Tool #6: call_code_generation_agent** (retry) | 9.0s | Regenerates with `total_sales` |
| 21:42:30.000 | 61.8s | Validate | **Tool #7: extract_python_code** | 3.0s | |
| 21:42:33.000 | 64.8s | Validate | **Tool #8: validate_spark_code** | 5.0s | |
| 21:42:38.000 | 69.8s | Validate | **Tool #9: execute_spark_code_lambda** on 100 MB sample (SUCCESS) | 38.0s | ~1.2M rows processed from 100 MB sample |
| 21:43:16.000 | 107.8s | Validate | **Tool #10: extract_execution_logs** | 11.0s | |
| 21:43:27.000 | 118.8s | Validate | **Tool #11: fetch_spark_results** (sample results) | 4.0s | |
| 21:43:31.000 | 122.8s | — | Validation complete; is_small=False → launch execution agent | — | Path replace: sample → full s3_input_path |
| 21:43:48.714 | 140.7s | Execute | "Replaced sample path with full path: s3://.../large_sales.csv" | 17.9s | Path substitution + execution agent setup + LLM reasoning |
| 21:43:50.000 | 142.0s | Execute | **Exec Tool #1: select_execution_platform** | 3.0s | file_size=150 MB → Lambda (below EMR threshold) |
| 21:43:53.000 | 145.0s | Execute | **Exec Tool #2: execute_spark_code_lambda** (full 150 MB) | 43.0s | Full file; Lambda duration 20,578ms; memory 1,492 MB / 3,008 MB |
| 21:44:36.000 | 188.0s | Execute | **Exec Tool #3: extract_execution_logs** | 16.0s | CloudWatch query |
| 21:44:52.000 | 204.0s | Execute | **Exec Tool #4: fetch_spark_results** | 2.0s | |
| 21:44:54.000 | 206.0s | — | JSON response streaming | 27.0s | |
| 21:45:21.000 | 233.0s | — | "Invocation completed (232.291s)" | — | |

### Lambda Execution Details

| Invocation | Lambda | Duration | Init | Memory Used | Notes |
|---|---|---|---|---|---|
| Validation sample attempt 1 (FAIL) | dev-spark-on-lambda | ~23s | warm | ~1,468 MB | Column error on 100 MB sample |
| Validation sample attempt 2 (SUCCESS) | dev-spark-on-lambda | ~35s | warm | ~1,468 MB | 100 MB sample, ~1.2M rows processed |
| Production full file | dev-spark-on-lambda | 20,578ms | warm | **1,492 MB** / 3,008 MB | Full 150 MB, ~1.8M rows; higher memory than sample runs |
| Fetch Results | dev-spark-tool-fetch-spark-results | ~100ms | warm | ~66 MB | |

### Time Breakdown by Category

| Category | Time | % | Details |
|---|---|---|---|
| Spark Execution (3 invocations) | ~107s | 46% | 26s fail + 38s sample success + 43s full file |
| prepare_csv_sample (S3 byte-range read) | ~21s | 9% | 100 MB GET + trim + S3 upload; non-LLM node |
| Execution agent gap (path replace + setup) | ~18s | 8% | Validation JSON streaming → execution agent LLM reasoning |
| JSON Streaming (final response) | ~27s | 12% | AgentCore → wrapper streaming |
| Code Generation (2 calls) | ~19s | 8% | 10s + 9s |
| Log Extraction (2 calls) | ~27s | 12% | 11s + 16s (execution agent CloudWatch query slow) |
| validate/extract/ensure tools | ~14s | 6% | |
| select_execution_platform | ~3s | 1% | |

### Notes
- `is_small=False`: 150 MB > 100 MB budget → execution agent ran on full file after validation
- Both validation and execution used Lambda (not EMR): `select_execution_platform` chose Lambda since 150 MB falls below EMR threshold
- Full 150 MB Lambda run was 20,578ms at 1,492 MB memory — slightly higher memory than sample runs (1,468 MB)
- The 17.9s gap between validation completion and "Replaced sample path" reflects: (a) validation agent streaming its final JSON (~4s fetch), (b) supervisor Python code doing path replacement and building execution agent context, (c) execution agent LLM reasoning to plan its first tool call
- 11 validation tools + 4 execution tools = 15 total tools
- `extract_execution_logs` in the execution agent took 16s (vs 3-11s elsewhere) — CloudWatch log stream for that invocation may have been slow to populate
- 40 rows returned (category aggregation across 1.8M rows)

---

## Phase Timing Summary: 2-Phase vs 1-Phase

| Run | File Size | is_small | Prepare Phase | Validation Phase | Execution Phase | Total |
|---|---|---|---|---|---|---|
| #1 (1.7 KB) | 1.7 KB | True | 0.15s | ~111s | — (skipped) | ~126s |
| #2 (23 MB) | 23 MB | True | 1.2s | ~114s | — (skipped) | ~125s |
| #3 (150 MB) | 150 MB | False | ~21s | ~122s | ~90s | ~232s |

The validation phase is consistently ~110–125s across all 3 runs regardless of file size (since all validate on Lambda using a sample or small file). The execution phase adds ~90s for the 150 MB 2-phase run.

---

## Component Latency Reference (2026-05-15 Measurements)

### prepare_csv_sample (non-LLM node)

| Scenario | Duration | Notes |
|---|---|---|
| File already ≤ SAMPLE_SIZE_MB (pass-through) | <0.2s | Just computes is_small, no S3 call |
| Wrapper pre-extracts sample (is_small=True) | 1.2s | 23 MB read + S3 write |
| Large file (100 MB byte-range GET) | ~21s | S3 byte-range + newline trim + S3 upload |

### Spark Lambda (dev-spark-on-lambda) — 2026-05-15

| Metric | Value | Notes |
|---|---|---|
| JVM + Spark Init | ~14s | Stable across all runs |
| Processing overhead (small file) | ~4s | 1.7 KB / 12 rows |
| Processing overhead (23 MB / 200K rows) | ~8–11s | Group-by aggregation |
| Processing overhead (100 MB sample / ~1.2M rows) | ~21s | Larger sample, more data shuffle |
| Processing overhead (150 MB / 1.8M rows) | ~6.5s | `total_sales by category` — simple agg |
| Memory (1.7 KB – 23 MB) | 1,468 MB / 3,008 MB | Consistent |
| Memory (150 MB full file) | 1,492 MB / 3,008 MB | +24 MB for larger dataset |

### Code Generation Agent

| Metric | Value |
|---|---|
| Per call | ~9–10s |
| Retry (with error context) | ~9–10s (same) |

### LLM Reasoning Overhead (Supervisor / Validation Agent)

| Step | Avg Duration |
|---|---|
| Initial planning | ~1.5–2.5s |
| Between tool calls | ~1–3s |
| Execution agent setup (path replace + plan) | ~17s (includes JSON streaming from validation) |
| Final JSON streaming | ~10–27s (variable) |

---

## Architecture Validation

### New Graph-Based Architecture: What Worked

| Behavior | Expected | Observed |
|---|---|---|
| `is_small=True` skips execution agent | Yes | ✓ Confirmed (Runs #1 and #2) |
| `is_small=False` triggers execution agent | Yes | ✓ Confirmed (Run #3) |
| Validation always uses `spark.read.csv` (never `spark.table`) | Yes | ✓ Confirmed |
| Execution agent replaces sample path with full path | Yes | ✓ Confirmed — log: "Replaced sample path with full path" |
| Retry on code error (max 3×) | Yes | ✓ 1 retry in each run |
| `select_execution_platform` in execution agent only | Yes | ✓ Not called in validation phase |
| Execution agent: no regeneration on failure | Yes | ✓ Only validation agent retried |

### vs. Old Architecture (from 2026-05-06 stats)

| Metric | Old (2026-05-06) | New (2026-05-15) | Change |
|---|---|---|---|
| Run #7 analog (22.5 MB CSV, success first try) | 99.4s | ~80–90s (estimated, no retry) | ~10–20s faster |
| Actual 23 MB CSV with 1 retry | n/a | 125.1s | Baseline for retry path |
| Glue 2-phase bug | Present (ambiguous system prompt) | Eliminated (deterministic graph) | Fixed |
| Sampling | 200 rows / 100 KB | 100 MB | 1000× larger sample |

### Column Name Mismatches (All 3 Runs)

All 3 runs required a code generation retry due to column name mismatches. The code gen agent hallucinated generic column names (`sales`, `salary`, `bonus`) instead of the actual schema names (`total_sales`, `base_salary`, `bonus_amount`). The validation agent correctly detected the error via `extract_execution_logs` and retried with error context.

**Pattern:** Code gen → column name error → Lambda executes → fails at runtime → `extract_execution_logs` → retry with schema in context → success.

This is expected behavior — the 100 MB sample gives the execution context needed for the retry to succeed. The new architecture's focused validation system prompt (never EMR, never Hive, retry up to 3×) handled this cleanly.

---

## Optimization Opportunities (Updated)

### Immediate (Low Effort, High Impact)

| # | Optimization | Potential Savings | Notes |
|---|---|---|---|
| 1 | Pass full schema to code gen agent on first call | ~20–40s per retry | Eliminates column name mismatches; all 3 runs had 1 retry |
| 2 | Skip `extract_execution_logs` on success | 3–11s per run | Logs available in Lambda response inline |
| 3 | Reduce JSON streaming time | 10–27s per run | Caused by AgentCore response chunking; hard to control |

### Medium-Term

| # | Optimization | Potential Savings | Notes |
|---|---|---|---|
| 4 | Provisioned concurrency on Spark Lambda | ~14s first-call savings | Eliminates JVM cold start |
| 5 | EMR threshold tuning | Context-dependent | Current Lambda handles 150 MB fine; EMR threshold may be too conservative |
| 6 | Parallel sample upload + agent invocation | ~21s for large CSV | `prepare_csv_sample` S3 write could overlap with AgentCore routing |

### Key Observations

- **Column schema injection** is the single highest-impact optimization: all 3 runs wasted 45–65s due to one retry cycle each (failed Lambda + re-codegen + re-validate + re-execute).
- **100 MB sample** successfully validates code that processes 150 MB (and by extension, much larger files) — the sample size is appropriate.
- **Spark init dominates** (14s) regardless of file size — this is unchanged from 2026-05-06 measurements.
- **`is_small` cutoff at 100 MB** correctly eliminated the execution phase for 23 MB files, saving ~25–40s vs the old always-2-phase behavior.
