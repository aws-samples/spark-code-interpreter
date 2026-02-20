from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import json
from typing import Dict, Any, Optional

dynamodb = boto3.resource('dynamodb')

@tool
def list_records(table_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
    """List all records from a DynamoDB table.
    
    Args:
        table_name: Name of the DynamoDB table
        limit: Maximum number of records to return
    
    Returns:
        Dictionary containing items and count
    """
    try:
        table = dynamodb.Table(table_name)
        params = {}
        if limit:
            params['Limit'] = limit
        
        response = table.scan(**params)
        return {
            'items': response['Items'],
            'count': response['Count']
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def search_records(table_name: str, filter_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
    """Search records in a DynamoDB table using filter expressions.
    
    Args:
        table_name: Name of the DynamoDB table
        filter_expression: DynamoDB filter expression
        expression_values: Values for the filter expression
    
    Returns:
        Dictionary containing matching items and count
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_values
        )
        return {
            'items': response['Items'],
            'count': response['Count']
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def get_record(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """Get a single record from a DynamoDB table by key.
    
    Args:
        table_name: Name of the DynamoDB table
        key: Primary key of the record to retrieve
    
    Returns:
        Dictionary containing the item or error message
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key=key)
        return {
            'item': response.get('Item'),
            'found': 'Item' in response
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def add_record(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new record to a DynamoDB table.
    
    Args:
        table_name: Name of the DynamoDB table
        item: Record data to insert
    
    Returns:
        Dictionary containing success message and item
    """
    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item=item)
        return {
            'message': 'Record added successfully',
            'item': item
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def update_record(table_name: str, key: Dict[str, Any], update_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing record in a DynamoDB table.
    
    Args:
        table_name: Name of the DynamoDB table
        key: Primary key of the record to update
        update_expression: DynamoDB update expression
        expression_values: Values for the update expression
    
    Returns:
        Dictionary containing success message and updated item
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        return {
            'message': 'Record updated successfully',
            'item': response['Attributes']
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def delete_record(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a record from a DynamoDB table.
    
    Args:
        table_name: Name of the DynamoDB table
        key: Primary key of the record to delete
    
    Returns:
        Dictionary containing success message and deleted item
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.delete_item(
            Key=key,
            ReturnValues='ALL_OLD'
        )
        return {
            'message': 'Record deleted successfully',
            'deleted_item': response.get('Attributes')
        }
    except Exception as e:
        return {'error': str(e)}

# Create the DynamoDB agent
dynamodb_agent = Agent(
    model=BedrockModel(model_id="anthropic.claude-3-sonnet-20240229-v1:0"),
    system_prompt="""You are a DynamoDB assistant that helps users manage records in DynamoDB tables.
    You can list, search, get, add, update, and delete records from any DynamoDB table.
    Always ask for the table name if not provided. Be helpful and provide clear responses about the operations performed.""",
    tools=[list_records, search_records, get_record, add_record, update_record, delete_record]
)

def handler(event: Dict[str, Any], context) -> str:
    """Lambda handler for DynamoDB operations using Strands agent."""
    try:
        prompt = event.get('prompt', '')
        if not prompt:
            return json.dumps({'error': 'No prompt provided'})
        
        response = dynamodb_agent(prompt)
        return str(response)
    
    except Exception as e:
        return json.dumps({'error': str(e)})