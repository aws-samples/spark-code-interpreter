import requests
import base64
import boto3
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

client_id = '392dlpv5hu2bsejav7l09iuvp'

def get_cognito_client_secret():
	client = boto3.client("cognito-idp")
	response = client.describe_user_pool_client(
		UserPoolId='us-east-1_XubTBv9c6',
		ClientId=client_id
	)
	return response["UserPoolClient"]["ClientSecret"]

client_secret = get_cognito_client_secret()
token_url = 'https://agentcore-7aa4b9e8.auth.us-east-1.amazoncognito.com/oauth2/token' 
gateway_url = "https://code-interpreter-gateway-e8qoo8fhzk.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
creds_data = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"

creds_response = requests.post(
	token_url,
	headers={
		"Authorization": f"Basic {credentials}",
		"Content-Type": "application/x-www-form-urlencoded",
	},
	data={"grant_type": "client_credentials"}
)

print(creds_response)

access_token = creds_response.json()['access_token']

gateway_client = MCPClient(lambda: streamablehttp_client(gateway_url, headers={"Authorization": f"Bearer {access_token}"}))

def get_full_tools_list(client):
    """
    List tools w/ support for pagination
    """
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True 
            pagination_token = tmp_tools.pagination_token
    return tools

with gateway_client:
      print(get_full_tools_list(gateway_client))

def validation_agent(question):
	with gateway_client:
		tools = get_full_tools_list(gateway_client)
		agent = Agent(
			model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
			tools=tools,
			system_prompt="execute the provided code on the provided cluster using the tool. If there are any errors, capture the actual error code and error message",
			callback_handler=None
		)
		return agent(question)

payload = str({
    "code": "import ray\nray.init(address=\"auto\")\ndata = [1, 2, 3, 4, 5]\nds = ray.data.from_items(data)\nresult = ds.map(lambda x: x * 2).sum()\nprint(f\"Result: {result}\")",
    "session_id": "test_with_ip",
    "ray_cluster_ip": "172.31.4.12"
  }
)

print(validation_agent(payload))

