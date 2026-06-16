#!/bin/bash

# Update wrapper Lambda with correct S3 configuration
# Run this after refreshing AWS credentials

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Update S3 Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}This will update the wrapper Lambda to use session-based S3 structure:${NC}"
echo ""
echo "Structure:"
echo "  s3://spark-data-817323390093-us-east-1/"
echo "    └── {session-id}/"
echo "        ├── scripts/     (generated code)"
echo "        └── output/      (execution results)"
echo ""

# Deploy the updated Lambda
echo -e "${YELLOW}Deploying updated Lambda...${NC}"
cd "$(dirname "$0")"
./deploy-agent-wrapper.sh

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test the Updated Configuration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Test with:"
echo "  aws lambda invoke \\"
echo "    --function-name dev-spark-agent-wrapper \\"
echo "    --payload '{\"prompt\":\"what is 5+5\"}' \\"
echo "    /tmp/test.json"
echo ""
echo "Then check S3:"
echo "  aws s3 ls s3://spark-data-817323390093-us-east-1/ --recursive | tail -20"
echo ""
echo "Results will be in:"
echo "  s3://spark-data-817323390093-us-east-1/{session-id}/output/"
echo ""
