from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
client = GatewayClient(region_name='us-east-1')
gateway_name = 'code-interpreter-gateway'

cognito_result = client.create_oauth_authorizer_with_cognito(gateway_name)
authorizer_configuration = cognito_result["authorizer_config"]

gateway = client.create_mcp_gateway(
	name=gateway_name,
	role_arn=None,
	authorizer_config=authorizer_configuration,
	enable_semantic_search=True,
)

print(f"MCP Endpoint: {gateway}")
print(f"OAuth Credentials:")
print(f"  Client ID: {cognito_result['client_info']['client_id']}")
print(f"  Scope: {cognito_result['client_info']['scope']}")

