#!/bin/bash

# Test agent invocation directly

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"
PROMPT=${1:-"what is 5+5"}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Agent Direct Invocation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Agent ARN: $AGENT_ARN"
echo "Prompt: $PROMPT"
echo ""

# Create test Python script
cat > /tmp/test_agent.py <<'PYEOF'
import boto3
import json
import uuid
import sys

# Get prompt from command line
prompt = sys.argv[1] if len(sys.argv) > 1 else "what is 5+5"

# Create client
client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(read_timeout=180)
)

# Generate session ID
session_id = f'test-{uuid.uuid4().hex}'

# Prepare payload
payload = {
    'prompt': prompt,
    'session_id': session_id
}

print(f'Testing agent invocation...')
print(f'Session ID: {session_id}')
print(f'Payload: {json.dumps(payload, indent=2)}')
print()

try:
    # Invoke agent
    response = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu',
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    # Read response
    result = response['response'].read().decode('utf-8')
    print('✅ Response received!')
    print('='*80)
    print(result)
    print('='*80)
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

PYEOF

# Run the test
python3 /tmp/test_agent.py "$PROMPT"

# Cleanup
rm /tmp/test_agent.py
