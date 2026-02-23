#!/usr/bin/env python3
"""Test multi-agent system with supervisor"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from agents import (
    create_supervisor_agent,
    create_data_discovery_agent,
    create_code_generator_agent,
    create_code_validator_agent
)

def test_multi_agent_system():
    """Verify multi-agent system is properly configured"""
    print("=" * 60)
    print("MULTI-AGENT SYSTEM VERIFICATION")
    print("=" * 60)
    print()
    
    # Test individual agents
    print("1. Testing specialized agents...")
    
    data_agent = create_data_discovery_agent()
    assert data_agent is not None, "DataDiscoveryAgent not created"
    assert data_agent.name == "DataDiscoveryAgent"
    assert "get_data_sources" in data_agent.tool_names
    print(f"   ✓ {data_agent.name}")
    print(f"     Tools: {data_agent.tool_names}")
    
    code_agent = create_code_generator_agent()
    assert code_agent is not None, "CodeGeneratorAgent not created"
    assert code_agent.name == "CodeGeneratorAgent"
    print(f"   ✓ {code_agent.name}")
    print(f"     Tools: {code_agent.tool_names if code_agent.tool_names else 'None (pure LLM)'}")
    
    validator_agent = create_code_validator_agent()
    assert validator_agent is not None, "CodeValidatorAgent not created"
    assert validator_agent.name == "CodeValidatorAgent"
    assert "execute_ray_code" in validator_agent.tool_names
    print(f"   ✓ {validator_agent.name}")
    print(f"     Tools: {validator_agent.tool_names}")
    
    # Test supervisor
    print()
    print("2. Testing supervisor agent...")
    
    supervisor = create_supervisor_agent()
    assert supervisor is not None, "SupervisorAgent not created"
    assert supervisor.name == "SupervisorAgent"
    assert len(supervisor.tool_names) == 3, "Supervisor should have 3 tools"
    assert "discover_data" in supervisor.tool_names
    assert "generate_code" in supervisor.tool_names
    assert "validate_code" in supervisor.tool_names
    print(f"   ✓ {supervisor.name}")
    print(f"     Tools (agent wrappers): {supervisor.tool_names}")
    
    print()
    print("=" * 60)
    print("✅ MULTI-AGENT SYSTEM VERIFIED")
    print("=" * 60)
    print()
    print("Architecture:")
    print("  SupervisorAgent (orchestrator)")
    print("  ├── discover_data → DataDiscoveryAgent")
    print("  │   └── Tool: get_data_sources")
    print("  ├── generate_code → CodeGeneratorAgent")
    print("  │   └── Pure LLM (no tools)")
    print("  └── validate_code → CodeValidatorAgent")
    print("      └── Tool: execute_ray_code")
    print()
    print("Total Agents: 4 (1 supervisor + 3 specialists)")
    print("Total Tools: 2 (get_data_sources, execute_ray_code)")
    print("Agent Wrappers: 3 (discover_data, generate_code, validate_code)")
    print()
    print("Note: This test does not start any background processes.")

if __name__ == "__main__":
    test_multi_agent_system()
