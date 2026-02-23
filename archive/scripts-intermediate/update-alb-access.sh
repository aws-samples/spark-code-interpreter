#!/bin/bash

# Update ALB Security Group Access Script
# Restricts or opens ALB access to specific IP addresses

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
SG_NAME="${ENVIRONMENT}-spark-alb-sg"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ALB Security Group Access Manager${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get security group ID
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null)

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    echo -e "${RED}❌ Security group not found: $SG_NAME${NC}"
    exit 1
fi

echo "Security Group: $SG_NAME ($SG_ID)"
echo ""

# Show current rules
echo -e "${YELLOW}Current HTTP access rules:${NC}"
aws ec2 describe-security-groups \
    --group-ids $SG_ID \
    --region $REGION \
    --query 'SecurityGroups[0].IpPermissions[?FromPort==`80`].IpRanges[*].[CidrIp,Description]' \
    --output table

echo ""
echo -e "${BLUE}What would you like to do?${NC}"
echo "1) Add my current IP"
echo "2) Add a specific IP"
echo "3) Allow all IPs (0.0.0.0/0)"
echo "4) Remove an IP"
echo "5) Show current rules"
echo "6) Exit"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        # Get current public IP
        echo ""
        echo "Detecting your public IP..."
        MY_IP=$(curl -s https://checkip.amazonaws.com)
        
        if [ -z "$MY_IP" ]; then
            echo -e "${RED}❌ Could not detect your IP${NC}"
            exit 1
        fi
        
        echo "Your IP: $MY_IP"
        echo ""
        read -p "Add this IP to ALB access? (yes/no): " confirm
        
        if [ "$confirm" == "yes" ]; then
            echo "Adding IP $MY_IP/32 to security group..."
            aws ec2 authorize-security-group-ingress \
                --group-id $SG_ID \
                --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=$MY_IP/32,Description='My IP'}]" \
                --region $REGION 2>/dev/null || echo "Rule may already exist"
            
            aws ec2 authorize-security-group-ingress \
                --group-id $SG_ID \
                --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=$MY_IP/32,Description='My IP'}]" \
                --region $REGION 2>/dev/null || echo "Rule may already exist"
            
            echo -e "${GREEN}✅ IP added successfully${NC}"
        fi
        ;;
    
    2)
        echo ""
        read -p "Enter IP address (e.g., 1.2.3.4): " CUSTOM_IP
        read -p "Enter description: " DESCRIPTION
        
        echo "Adding IP $CUSTOM_IP/32 to security group..."
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=$CUSTOM_IP/32,Description='$DESCRIPTION'}]" \
            --region $REGION 2>/dev/null || echo "Rule may already exist"
        
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=$CUSTOM_IP/32,Description='$DESCRIPTION'}]" \
            --region $REGION 2>/dev/null || echo "Rule may already exist"
        
        echo -e "${GREEN}✅ IP added successfully${NC}"
        ;;
    
    3)
        echo ""
        echo -e "${YELLOW}⚠️  This will allow access from ANY IP address${NC}"
        read -p "Are you sure? (yes/no): " confirm
        
        if [ "$confirm" == "yes" ]; then
            echo "Opening access to all IPs..."
            aws ec2 authorize-security-group-ingress \
                --group-id $SG_ID \
                --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=0.0.0.0/0,Description='HTTP from anywhere'}]" \
                --region $REGION 2>/dev/null || echo "Rule may already exist"
            
            aws ec2 authorize-security-group-ingress \
                --group-id $SG_ID \
                --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=0.0.0.0/0,Description='HTTPS from anywhere'}]" \
                --region $REGION 2>/dev/null || echo "Rule may already exist"
            
            echo -e "${GREEN}✅ Access opened to all IPs${NC}"
        fi
        ;;
    
    4)
        echo ""
        read -p "Enter IP address to remove (e.g., 1.2.3.4): " REMOVE_IP
        
        echo "Removing IP $REMOVE_IP/32 from security group..."
        aws ec2 revoke-security-group-ingress \
            --group-id $SG_ID \
            --ip-permissions IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=$REMOVE_IP/32}]" \
            --region $REGION 2>/dev/null || echo "Rule not found"
        
        aws ec2 revoke-security-group-ingress \
            --group-id $SG_ID \
            --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=$REMOVE_IP/32}]" \
            --region $REGION 2>/dev/null || echo "Rule not found"
        
        echo -e "${GREEN}✅ IP removed${NC}"
        ;;
    
    5)
        echo ""
        echo -e "${YELLOW}Current security group rules:${NC}"
        aws ec2 describe-security-groups \
            --group-ids $SG_ID \
            --region $REGION \
            --query 'SecurityGroups[0].IpPermissions' \
            --output table
        ;;
    
    6)
        echo "Exiting..."
        exit 0
        ;;
    
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}Updated security group rules:${NC}"
aws ec2 describe-security-groups \
    --group-ids $SG_ID \
    --region $REGION \
    --query 'SecurityGroups[0].IpPermissions[?FromPort==`80`].IpRanges[*].[CidrIp,Description]' \
    --output table

echo ""
echo -e "${GREEN}Done!${NC}"
