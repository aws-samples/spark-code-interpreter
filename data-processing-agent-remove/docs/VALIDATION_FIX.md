# Validation & Session Isolation Fixes

## Issues Fixed

### 1. Validation Not Retrying
**Problem**: Agent was returning code even when validation failed, instead of retrying.

**Solution**: 
- Strengthened agent system prompt with explicit MANDATORY WORKFLOW
- Agent must call `validate_code()` and get `success=True` before returning
- If validation fails, agent must fix code and retry (up to 3 attempts)
- If all attempts fail, agent returns error message instead of broken code

### 2. Session Isolation Incomplete
**Problem**: Sessions were using same conversation history, causing context overlap between prompts.

**Solution**:
- Each prompt gets unique `session_id` (format: `{base_session}_{timestamp}`)
- Per strands-agents docs: unique session_id = isolated conversation (no history overlap)
- Data sources snapshot to `prompt_sessions[prompt_id]` for isolation
- Agent invoked with unique `session_id=prompt_id` for complete isolation

### 3. Data Source Clearing
**Problem**: Previous implementation cleared files after execution, preventing re-execution from history.

**Solution**:
- Removed data source clearing after execution
- Data sources persist in session for re-execution
- Each new prompt gets isolated snapshot via `prompt_sessions`
- Re-execution from history uses original prompt's data sources

## Changes Made

### agents.py
- **Strengthened system prompt**: Explicit mandatory workflow with numbered steps
- **Validation enforcement**: Agent MUST get `success=True` before returning code
- **Error handling**: Returns "Validation failed after 3 attempts: [error]" if all retries fail
- **Simplified instructions**: Clearer, more direct language

### main.py
- **Session isolation**: Each prompt gets unique `session_id` for agent invocation
- **Removed context injection**: Prompt is just user request (no session metadata in prompt text)
- **Validation check**: Backend checks for "validation failed" in response
- **Data preservation**: No clearing of `uploaded_csv` or `selected_tables` after execution

## How It Works

### Validation Flow
```
1. User submits prompt
2. Backend creates unique prompt_id
3. Backend snapshots data sources to prompt_sessions[prompt_id]
4. Agent invoked with session_id=prompt_id (isolated)
5. Agent calls get_data_sources(prompt_id)
6. Agent generates code
7. Agent calls validate_code(code)
8. If success=False: Agent fixes code, calls validate_code again (up to 3x)
9. If success=True: Agent returns validated code
10. Backend executes validated code on cluster
```

### Session Isolation
```
Prompt 1: session_id = "abc_1234567890"
  - prompt_sessions["abc_1234567890"] = {csv: file1.csv, tables: []}
  - Agent conversation isolated to this session_id
  
Prompt 2: session_id = "abc_1234567891"  
  - prompt_sessions["abc_1234567891"] = {csv: file2.csv, tables: []}
  - Agent conversation isolated to this session_id (no history from Prompt 1)
```

### Re-execution from History
```
1. User clicks re-execute on Prompt 1
2. Backend uses original prompt_id from history
3. prompt_sessions[original_prompt_id] still has original data sources
4. Code executes with same data sources as original execution
```

## Testing

Run validation test:
```bash
python3 test_validation.py
```

Tests:
1. **Validation Workflow**: Verifies agent validates code before returning
2. **Session Isolation**: Verifies each prompt gets isolated session

## Key Benefits

1. **Reliable Code Generation**: Only validated code is executed
2. **No Context Leakage**: Each prompt is independent (no conversation history overlap)
3. **Re-execution Support**: Data sources persist for history re-execution
4. **Automatic Error Correction**: Agent fixes validation errors automatically (up to 3 attempts)
5. **Clean Architecture**: Follows strands-agents session management best practices

## References

- [Strands-Agents Session Management](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/session-management/)
