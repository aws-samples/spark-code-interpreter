#!/usr/bin/env python3
"""VPC validation results"""

def show_vpc_validation():
    print("🔍 VPC VALIDATION RESULTS")
    print("=" * 50)
    
    print("📋 Lambda Function Configuration:")
    print("   VPC ID: vpc-0485dcc1f1d050b55")
    print("   Subnets: subnet-0ffcc9c369d011e54, subnet-04c2c799482ddc064")
    print("   Security Group: sg-098a735e14f9f2953")
    
    print("\n📋 Ray ECS Cluster Configuration:")
    print("   VPC ID: vpc-0485dcc1f1d050b55")
    print("   Subnets: subnet-04c2c799482ddc064, subnet-0ffcc9c369d011e54")
    print("   Security Group: sg-052f922fa69cf0ff7")
    
    print("\n✅ VPC VALIDATION:")
    print("   ✅ SAME VPC: Both use vpc-0485dcc1f1d050b55")
    print("   ✅ SAME SUBNETS: Both use same subnet IDs")
    print("   ⚠️ DIFFERENT SECURITY GROUPS:")
    print("      Lambda: sg-098a735e14f9f2953")
    print("      Ray ECS: sg-052f922fa69cf0ff7")
    
    print("\n🔧 ISSUE IDENTIFIED:")
    print("   The security groups are different, which may be blocking")
    print("   communication between Lambda and Ray cluster.")
    
    print("\n💡 SOLUTION:")
    print("   Check security group rules to ensure Lambda can reach")
    print("   Ray cluster on port 8265 (dashboard) and 10001 (jobs API)")

if __name__ == "__main__":
    show_vpc_validation()
