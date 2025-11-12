"""Test gateway connection locally"""

import sys
sys.path.append('../backend')

from test_agent_gateway import gateway_client
import json

test_code = """import ray
ray.init()

numbers = list(range(1, 11))
even_numbers = [n for n in numbers if n % 2 == 0]
total = sum(even_numbers)
print(f"Sum of even numbers: {total}")
"""

print("Testing gateway validation tool...")
print(f"Code:\n{test_code}\n")

try:
    with gateway_client:
        result = gateway_client.call_tool_sync(
            "ray-code-validation-execution___validate_ray_code",
            arguments={
                "code": test_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        )
        
        print("✅ Result:")
        print(result.content[0].text if result.content else str(result))
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
