#!/bin/bash

# Verification Script for Applied Fixes
# Run this to verify all fixes were applied correctly

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verifying Applied Fixes${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

PASS=0
FAIL=0

# Test 1: Check Spark Supervisor Dockerfile CMD
echo -e "${YELLOW}Test 1: Spark Supervisor Dockerfile CMD${NC}"
if grep -q 'CMD \["opentelemetry-instrument", "python", "spark_supervisor_agent.py"\]' agent-code/spark-supervisor-agent/Dockerfile; then
    echo -e "${GREEN}✅ PASS: Dockerfile CMD is correct${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: Dockerfile CMD is incorrect${NC}"
    echo "Expected: CMD [\"opentelemetry-instrument\", \"python\", \"spark_supervisor_agent.py\"]"
    echo "Found:"
    grep "CMD" agent-code/spark-supervisor-agent/Dockerfile
    FAIL=$((FAIL+1))
fi
echo ""

# Test 2: Check Code Generation Dockerfile CMD
echo -e "${YELLOW}Test 2: Code Generation Dockerfile CMD${NC}"
if grep -q 'CMD \["opentelemetry-instrument", "python", "agents.py"\]' agent-code/code-generation-agent/Dockerfile; then
    echo -e "${GREEN}✅ PASS: Dockerfile CMD is correct${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: Dockerfile CMD is incorrect${NC}"
    echo "Expected: CMD [\"opentelemetry-instrument\", \"python\", \"agents.py\"]"
    echo "Found:"
    grep "CMD" agent-code/code-generation-agent/Dockerfile
    FAIL=$((FAIL+1))
fi
echo ""

# Test 3: Check IAM automation in Spark Supervisor agent_deployment.py
echo -e "${YELLOW}Test 3: IAM Automation in Spark Supervisor${NC}"
if grep -q "SparkAgentComprehensivePolicy" agent-code/spark-supervisor-agent/agent_deployment.py; then
    echo -e "${GREEN}✅ PASS: IAM automation code present${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: IAM automation code missing${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 4: Check IAM automation in Code Gen agent_deployment.py
echo -e "${YELLOW}Test 4: IAM Automation in Code Generation${NC}"
if grep -q "CodeGenAgentPolicy" agent-code/code-generation-agent/agent_deployment.py; then
    echo -e "${GREEN}✅ PASS: IAM automation code present${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: IAM automation code missing${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 5: Check ECR repository in CloudFormation
echo -e "${YELLOW}Test 5: ECR Repository in CloudFormation${NC}"
if grep -q "SparkLambdaECRRepository:" cloudformation/spark-complete-stack.yml; then
    echo -e "${GREEN}✅ PASS: ECR repository resource present${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: ECR repository resource missing${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 6: Check DependsOn in SparkOnLambda
echo -e "${YELLOW}Test 6: DependsOn in SparkOnLambda${NC}"
if grep -q "DependsOn: SparkLambdaECRRepository" cloudformation/spark-complete-stack.yml; then
    echo -e "${GREEN}✅ PASS: DependsOn clause present${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: DependsOn clause missing${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 7: Check ECR output in CloudFormation
echo -e "${YELLOW}Test 7: ECR Output in CloudFormation${NC}"
if grep -q "SparkLambdaECRRepositoryUri:" cloudformation/spark-complete-stack.yml; then
    echo -e "${GREEN}✅ PASS: ECR output present${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: ECR output missing${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 8: Check deploy-all.sh removed manual EMR permissions
echo -e "${YELLOW}Test 8: Manual EMR Permissions Removed${NC}"
if ! grep -q "Adding EMR permissions to agent execution role" scripts/deploy-all.sh; then
    echo -e "${GREEN}✅ PASS: Manual EMR permission code removed${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: Manual EMR permission code still present${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Test 9: Check deploy-all.sh updated success messages
echo -e "${YELLOW}Test 9: Updated Success Messages${NC}"
if grep -q "deployed (with IAM permissions)" scripts/deploy-all.sh; then
    echo -e "${GREEN}✅ PASS: Success messages updated${NC}"
    PASS=$((PASS+1))
else
    echo -e "${RED}❌ FAIL: Success messages not updated${NC}"
    FAIL=$((FAIL+1))
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Tests Passed: ${GREEN}$PASS${NC}"
echo -e "Tests Failed: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ ALL FIXES VERIFIED SUCCESSFULLY!${NC}"
    echo ""
    echo "You can now run: ./scripts/deploy-all.sh"
    exit 0
else
    echo -e "${RED}❌ SOME FIXES FAILED VERIFICATION${NC}"
    echo ""
    echo "Please review the failed tests above and fix them before deploying."
    exit 1
fi
