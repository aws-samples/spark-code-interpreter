
import boto3
import json

agent_arn='arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/ray_code_interpreter-oTKmLH9IB9'
agentcore_client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1'
)
payload = {
    "prompt": "Session ID: test_session_123\n\ngenerate code to find the top 10 prime numbers",
    "ray_cluster_ip": "100.27.32.218"
}

boto3_response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    qualifier="DEFAULT",
    runtimeSessionId="ray_code_interpreter_test_session_123",
    payload=json.dumps(payload)
)
if "text/event-stream" in boto3_response.get("contentType", ""):
    content = []
    for line in boto3_response["response"].iter_lines(chunk_size=1):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                print(line)
                content.append(line)
    print("\n".join(content))
else:
    try:
        events = []
        for event in boto3_response.get("response", []):
            events.append(event)
    except Exception as e:
        events = [f"Error reading EventStream: {e}"]
    print(json.loads(events[0].decode("utf-8")))


