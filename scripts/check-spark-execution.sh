#!/bin/bash

# Script to check Spark Lambda execution details

REGION=${AWS_REGION:-us-east-1}
LOG_GROUP="/aws/lambda/dev-spark-on-lambda"

echo "=== Spark Lambda Execution Trace ==="
echo ""
echo "Checking logs from the last 10 minutes..."
echo ""

# Get the most recent log streams
echo "Step 1: Finding recent log streams..."
STREAMS=$(aws logs describe-log-streams \
    --log-group-name $LOG_GROUP \
    --order-by LastEventTime \
    --descending \
    --max-items 3 \
    --region $REGION \
    --query 'logStreams[*].logStreamName' \
    --output text \
    --no-cli-pager)

echo "Found streams:"
echo "$STREAMS"
echo ""

# Get logs from the most recent stream
LATEST_STREAM=$(echo "$STREAMS" | awk '{print $1}')
echo "Step 2: Getting logs from latest stream: $LATEST_STREAM"
echo ""

# Fetch and parse logs
aws logs get-log-events \
    --log-group-name $LOG_GROUP \
    --log-stream-name "$LATEST_STREAM" \
    --limit 500 \
    --region $REGION \
    --no-cli-pager 2>&1 | \
    python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for event in data.get('events', []):
        print(event['message'])
except:
    pass
" | head -200

echo ""
echo "=== End of logs ==="
