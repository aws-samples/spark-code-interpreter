from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import json
import base64
from typing import Dict, Any, Optional

s3 = boto3.client('s3')

@tool
def list_objects(bucket_name: str, prefix: Optional[str] = None, max_keys: Optional[int] = None) -> Dict[str, Any]:
    """List objects in an S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: Prefix to filter objects
        max_keys: Maximum number of objects to return
    
    Returns:
        Dictionary containing objects list
    """
    try:
        params = {'Bucket': bucket_name}
        if prefix:
            params['Prefix'] = prefix
        if max_keys:
            params['MaxKeys'] = max_keys
        
        response = s3.list_objects_v2(**params)
        objects = response.get('Contents', [])
        return {
            'objects': [{'key': obj['Key'], 'size': obj['Size'], 'last_modified': obj['LastModified'].isoformat()} for obj in objects],
            'count': len(objects)
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def search_objects_by_prefix(bucket_name: str, prefix: str, max_keys: Optional[int] = None) -> Dict[str, Any]:
    """Search objects in S3 bucket by prefix.
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: Prefix to search for
        max_keys: Maximum number of objects to return
    
    Returns:
        Dictionary containing matching objects
    """
    try:
        params = {'Bucket': bucket_name, 'Prefix': prefix}
        if max_keys:
            params['MaxKeys'] = max_keys
        
        response = s3.list_objects_v2(**params)
        objects = response.get('Contents', [])
        return {
            'objects': [{'key': obj['Key'], 'size': obj['Size'], 'last_modified': obj['LastModified'].isoformat()} for obj in objects],
            'count': len(objects)
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def get_object(bucket_name: str, key: str) -> Dict[str, Any]:
    """Get an object from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        key: Object key to retrieve
    
    Returns:
        Dictionary containing object content and metadata
    """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        content = response['Body'].read()
        
        # Try to decode as text, otherwise return base64
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            content_str = base64.b64encode(content).decode('utf-8')
        
        return {
            'key': key,
            'content': content_str,
            'content_type': response.get('ContentType', ''),
            'size': response.get('ContentLength', 0),
            'last_modified': response.get('LastModified', '').isoformat() if response.get('LastModified') else ''
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def put_object(bucket_name: str, key: str, content: str, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Put an object to S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        key: Object key to create/update
        content: Content to upload
        content_type: MIME type of the content
    
    Returns:
        Dictionary containing success message
    """
    try:
        params = {'Bucket': bucket_name, 'Key': key, 'Body': content}
        if content_type:
            params['ContentType'] = content_type
        
        s3.put_object(**params)
        return {
            'message': 'Object uploaded successfully',
            'key': key,
            'bucket': bucket_name
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def update_object(bucket_name: str, key: str, content: str, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing object in S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        key: Object key to update
        content: New content
        content_type: MIME type of the content
    
    Returns:
        Dictionary containing success message
    """
    try:
        params = {'Bucket': bucket_name, 'Key': key, 'Body': content}
        if content_type:
            params['ContentType'] = content_type
        
        s3.put_object(**params)
        return {
            'message': 'Object updated successfully',
            'key': key,
            'bucket': bucket_name
        }
    except Exception as e:
        return {'error': str(e)}

@tool
def delete_object(bucket_name: str, key: str) -> Dict[str, Any]:
    """Delete an object from S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        key: Object key to delete
    
    Returns:
        Dictionary containing success message
    """
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        return {
            'message': 'Object deleted successfully',
            'key': key,
            'bucket': bucket_name
        }
    except Exception as e:
        return {'error': str(e)}

# Create the S3 agent
s3_agent = Agent(
    model=BedrockModel(model_id="anthropic.claude-3-sonnet-20240229-v1:0"),
    system_prompt="""You are an S3 assistant that helps users manage objects in S3 buckets.
    You can list, search, get, put, update, and delete objects from any S3 bucket.
    Always ask for the bucket name if not provided. Be helpful and provide clear responses about the operations performed.""",
    tools=[list_objects, search_objects_by_prefix, get_object, put_object, update_object, delete_object]
)

def handler(event: Dict[str, Any], context) -> str:
    """Lambda handler for S3 operations using Strands agent."""
    try:
        prompt = event.get('prompt', '')
        if not prompt:
            return json.dumps({'error': 'No prompt provided'})
        
        response = s3_agent(prompt)
        return str(response)
    
    except Exception as e:
        return json.dumps({'error': str(e)})