# Agent Invocation Fix - Callback Handlers

## Issue

The code generator agent wrapper was using synchronous `invoke()` method which doesn't exist. Agents in strands-agents use `invoke_async()` for invocation.

## Problem

```python
# WRONG - invoke() doesn't exist
@tool
def generate_code(requirements: str) -> str:
    result = code_agent.invoke(requirements)  # ❌ AttributeError
    return str(result.message)
```

## Solution

Updated agent wrappers to use `invoke_async()` with proper async handling:

```python
# CORRECT - use invoke_async() with event loop
@tool
def generate_code(requirements: str) -> str:
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(code_agent.invoke_async(requirements))
        # Extract content properly
        if hasattr(result.message, 'content'):
            content = result.message.content[0].text if result.message.content else str(result.message)
        else:
            content = str(result.message)
        return content
    finally:
        loop.close()
```

## What Was Fixed

### 1. generate_code Tool
- Changed from `code_agent.invoke()` to `code_agent.invoke_async()`
- Added event loop handling for sync tool context
- Proper content extraction from response

### 2. validate_code Tool
- Changed from `validator_agent.invoke()` to `validator_agent.invoke_async()`
- Added event loop handling
- Proper content extraction from response

### 3. discover_data Tool
- Already working (direct session access, no agent invocation)

## How It Works Now

### Synchronous Tool Context
Tools are called synchronously by the supervisor, but sub-agents need async invocation:

```python
@tool
def generate_code(requirements: str) -> str:
    # Tool is called synchronously
    # But agent needs async invocation
    
    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run async invocation in sync context
        result = loop.run_until_complete(
            code_agent.invoke_async(requirements)
        )
        return extract_content(result)
    finally:
        loop.close()
```

### Response Extraction
Properly extract content from agent response:

```python
if hasattr(result.message, 'content'):
    # Response has structured content
    content = result.message.content[0].text if result.message.content else str(result.message)
else:
    # Response is simple message
    content = str(result.message)
```

## Workflow

```
SupervisorAgent (async)
    ↓
Calls tool: generate_code(requirements)  [sync]
    ↓
Tool creates event loop
    ↓
Runs: code_agent.invoke_async(requirements)  [async]
    ↓
Extracts content from response
    ↓
Returns string to supervisor  [sync]
```

## Benefits

✅ **Proper Async Handling**: Uses invoke_async() correctly
✅ **Event Loop Management**: Creates/closes loops properly
✅ **Content Extraction**: Handles different response formats
✅ **Error Handling**: Try/finally ensures loop cleanup
✅ **Sync/Async Bridge**: Tools work in sync context with async agents

## Testing

```bash
python3 test_agent_invocation.py
```

Expected output:
```
✓ CodeGeneratorAgent created
✓ Agent invoked successfully
✅ CodeGeneratorAgent invocation works correctly
✅ Supervisor tools are properly configured
```

## Summary

✅ **Fixed generate_code tool** - Uses invoke_async with event loop
✅ **Fixed validate_code tool** - Uses invoke_async with event loop
✅ **Proper callback handling** - Event loops managed correctly
✅ **Content extraction** - Handles response formats properly
✅ **All agent wrappers working** - discover_data, generate_code, validate_code

The agent invocation now works correctly with proper async handling and callback management.
