# DynamoDB Agent with Strands Framework

A Strands-powered Lambda function that performs CRUD operations on DynamoDB tables using natural language.

## Usage

The function accepts natural language prompts:

```json
{
  "prompt": "List all records from the users table"
}
```

## Example Prompts

### List Records
- "Show me all records from the products table"
- "List the first 10 items from users table"

### Search Records
- "Find all users where status equals active in the users table"
- "Search for products with price greater than 100"

### Get Record
- "Get the user with id 123 from users table"
- "Retrieve the product with key {id: 'prod-456'}"

### Add Record
- "Add a new user with name John and email john@example.com to users table"
- "Insert a product with id prod-789, name Widget, price 29.99"

### Update Record
- "Update user 123 to set name to Jane in users table"
- "Change the price of product prod-456 to 39.99"

### Delete Record
- "Delete user with id 123 from users table"
- "Remove product prod-456"

## Features

- **Natural Language Interface**: Use conversational prompts instead of JSON structures
- **Strands Framework**: Built on AWS Strands for intelligent agent behavior
- **Amazon Bedrock**: Powered by Claude 3 Sonnet for natural language understanding
- **Flexible Operations**: Supports all DynamoDB CRUD operations
- **Error Handling**: Comprehensive error responses

## Deployment

1. Install dependencies: `pip install -r requirements.txt`
2. Package the function with dependencies
3. Deploy to AWS Lambda with:
   - IAM permissions for DynamoDB access
   - IAM permissions for Amazon Bedrock
   - Python 3.9+ runtime