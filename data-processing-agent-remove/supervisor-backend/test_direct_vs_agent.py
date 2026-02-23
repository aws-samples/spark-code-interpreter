"""Compare direct tool call vs agent-based call"""

import sys
sys.path.append('../backend')

from test_agent_gateway import gateway_client, get_full_tools_list
from strands import Agent
import json
import uuid

test_code = """import ray
ray.init()
numbers = list(range(1, 11))
even_numbers = [n for n in numbers if n % 2 == 0]
total = sum(even_numbers)
print(f"Sum: {total}")
"""

print("=" * 60)
print("TEST 1: Direct tool call")
print("=" * 60)
try:
    with gateway_client:
        result = gateway_client.call_tool_sync(
            tool_use_id=f"test-{uuid.uuid4().hex}",
            name="ray-code-validation-execution___validate_ray_code",
            arguments={
                "code": test_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        )
        print("✅ Direct call result:")
        print(f"Type: {type(result)}")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result.content[0].text if hasattr(result, 'content') and result.content else str(result))
except Exception as e:
    print(f"❌ Direct call error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST 2: Agent-based call")
print("=" * 60)
try:
    with gateway_client:
        tools = get_full_tools_list(gateway_client)
        agent = Agent(
            model="us.amazon.nova-premier-v1:0",
            tools=tools,
            system_prompt="Execute the Ray code using the validation tool. Return the result.",
        )
        
        payload = {
            "code": test_code,
            "ray_cluster_ip": "172.31.4.12"
        }
        
        result = agent(f"Execute this code: {json.dumps(payload)}")
        print("✅ Agent call result:")
        print(result)
except Exception as e:
    print(f"❌ Agent call error: {e}")
    import traceback
    traceback.print_exc()
