import React, { useState, useEffect, useCallback } from 'react';
import { 
  Modal,
  FormField,
  Input,
  Textarea,
  Select,
  Multiselect,
  SpaceBetween,
  Box,
  Button
} from '@cloudscape-design/components';

const ManageBlueprintItemForm = ({ visible, onDismiss, item, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    service_type: '',
    actions: [],
    prompt: '',
    code: '',
    naturalLanguageInput: ''
  });
  const [isSaving, setIsSaving] = useState(false);

  // Prepopulate form when item changes
  useEffect(() => {
    if (item) {
      setFormData({
        name: item.name || '',
        description: item.description || '',
        category: item.category || '',
        service_type: item.service_type || '',
        actions: item.actions || [],
        prompt: item.prompt || '',
        code: item.code || '',
        naturalLanguageInput: item.naturalLanguageInput || ''
      });
    }
  }, [item]);

  const categoryOptions = [
    { label: 'AWS Services', value: 'aws-services' },
    { label: 'Functions', value: 'functions' },
    { label: 'Build your own tool', value: 'custom-tool' }
  ];

  const getActionOptions = () => {
    if (formData.service_type === 'rds') {
      return [
        { label: 'Insert', value: 'insert' },
        { label: 'Update', value: 'update' },
        { label: 'Delete', value: 'delete' },
        { label: 'Select', value: 'select' }
      ];
    }
    return [
      { label: 'Create Record', value: 'create' },
      { label: 'Read Record', value: 'read' },
      { label: 'Update Record', value: 'update' },
      { label: 'Delete Record', value: 'delete' },
      { label: 'List Records', value: 'list' },
      { label: 'Search For Record', value: 'search' }
    ];
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        action: 'update',
        key: { 
          tool_id: { S: item.tool_id },
          service_type: { S: item.service_type }
        },
        item: {
          name: { S: formData.name },
          description: { S: formData.description },
          category: { S: formData.category },
          service_type: { S: formData.service_type },
          actions: { L: formData.actions.map(a => ({ S: a })) },
          prompt: { S: formData.prompt },
          code: { S: formData.code },
          naturalLanguageInput: { S: formData.naturalLanguageInput || '' },
          nlpPrompt: { S: formData.naturalLanguageInput || '' },
          item_type: { S: 'blueprint' }
        }
      };

      const response = await fetch('https://77a9252l49.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        alert('Blueprint updated successfully!');
        onSave();
      } else {
        throw new Error('Failed to update blueprint');
      }
    } catch (error) {
      console.error('Error updating blueprint:', error);
      alert('Error updating blueprint. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const updatePromptWithActions = useCallback((selectedActions, serviceType) => {
    if (selectedActions && selectedActions.length > 0 && serviceType) {
      // For DynamoDB service type, use the specific prompt format
      if (serviceType === 'dynamodb') {
        const actionLabels = selectedActions.map(a => {
          const actionOption = getActionOptions().find(opt => opt.value === a);
          return actionOption ? actionOption.label : a;
        }).join(', ');
        
        const dynamoDBPrompt = `Create individual functions for DynamoDB for each of the actions: ${actionLabels}. Just return the individual code and not not entire python code, use boto3 client approach to generate the code, ensure that dynamodb type_code is included for the attribute, prefix all the functions with @mcp.tool(). Only generate the required code do not provide any additional context, use the following as a reference code 
import boto3
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import os

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    """Generic Lambda function for DynamoDB CRUD operations."""
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {})
    
    try:
        body = json.loads(event['body']) if event.get('body') else event
        
        table_name = body.get('table_name')
        action = body.get('action')
        
        if not table_name or not action:
            return cors_response(400, {'error': 'table_name and action are required'})
        
        if action == 'add':
            return add_record(table_name, body.get('data', {}))
        elif action == 'list':
            return list_records(table_name, body.get('limit'))
        elif action == 'get':
            return get_record(table_name, body.get('key'))
        elif action == 'update':
            return update_record(table_name, body.get('key'), body.get('data', {}))
        elif action == 'delete':
            return delete_record(table_name, body.get('key'))
        else:
            return cors_response(400, {'error': f'Unsupported action: {action}'})
    
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def add_record(table_name, data):
    """Add record to DynamoDB table."""
    try:
        if not data:
            return cors_response(400, {'error': 'data is required'})
        
        # Convert to DynamoDB format
        item = {}
        for key, value in data.items():
            item[key] = convert_to_dynamodb_type(value)
        
        # Add ID and timestamp if not provided
        if 'id' not in item:
            item['id'] = {'S': str(uuid.uuid4())}
        if 'created_at' not in item:
            item['created_at'] = {'S': datetime.now().isoformat()}
        
        dynamodb.put_item(TableName=table_name, Item=item)
        
        return cors_response(201, {
            'message': 'Record added successfully',
            'item': convert_from_dynamodb_format(item)
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def list_records(table_name, limit=None):
    """List records from DynamoDB table."""
    try:
        params = {'TableName': table_name}
        if limit:
            params['Limit'] = limit
            
        response = dynamodb.scan(**params)
        
        # Convert items from DynamoDB format
        items = [convert_from_dynamodb_format(item) for item in response['Items']]
        
        return cors_response(200, {
            'items': items,
            'count': response['Count']
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def get_record(table_name, key):
    """Get single record from DynamoDB table."""
    try:
        if not key:
            return cors_response(400, {'error': 'key is required'})
        
        # Convert key to DynamoDB format
        dynamodb_key = {k: convert_to_dynamodb_type(v) for k, v in key.items()}
        
        response = dynamodb.get_item(TableName=table_name, Key=dynamodb_key)
        
        item = None
        if 'Item' in response:
            item = convert_from_dynamodb_format(response['Item'])
        
        return cors_response(200 if 'Item' in response else 404, {
            'item': item,
            'found': 'Item' in response
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def update_record(table_name, key, data):
    """Update record in DynamoDB table."""
    try:
        if not key or not data:
            return cors_response(400, {'error': 'key and data are required'})
        
        # Convert key to DynamoDB format
        dynamodb_key = {k: convert_to_dynamodb_type(v) for k, v in key.items()}
        
        # Build update expression dynamically
        update_expression = "SET "
        expression_values = {}
        expression_names = {}
        
        for field, value in data.items():
            if field not in key:  # Don't update key fields
                attr_name = f"#{field}"
                attr_value = f":{field}"
                
                update_expression += f"{attr_name} = {attr_value}, "
                expression_values[attr_value] = convert_to_dynamodb_type(value)
                expression_names[attr_name] = field
        
        # Add updated timestamp
        update_expression += "#updated_at = :updated_at"
        expression_values[':updated_at'] = {'S': datetime.now().isoformat()}
        expression_names['#updated_at'] = 'updated_at'
        print(dynamodb_key)
        print(update_expression)
        print(expression_values)
        response = dynamodb.update_item(
            TableName=table_name,
            Key=dynamodb_key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return cors_response(200, {
            'message': 'Record updated successfully',
            'item': convert_from_dynamodb_format(response['Attributes'])
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def delete_record(table_name, key):
    """Delete record from DynamoDB table."""
    try:
        if not key:
            return cors_response(400, {'error': 'key is required'})
        
        # Convert key to DynamoDB format
        dynamodb_key = {k: convert_to_dynamodb_type(v) for k, v in key.items()}
        
        response = dynamodb.delete_item(
            TableName=table_name,
            Key=dynamodb_key,
            ReturnValues='ALL_OLD'
        )
        
        deleted_item = None
        if 'Attributes' in response:
            deleted_item = convert_from_dynamodb_format(response['Attributes'])
        
        return cors_response(200, {
            'message': 'Record deleted successfully',
            'deleted_item': deleted_item
        })
    except Exception as e:
        return cors_response(500, {'error': str(e)})

def convert_to_dynamodb_type(value):
    """Convert Python value to DynamoDB type format."""
    if isinstance(value, str):
        return {'S': value}
    elif isinstance(value, (int, float)):
        return {'N': str(value)}
    elif isinstance(value, bool):
        return {'BOOL': value}
    elif isinstance(value, list):
        return {'L': [convert_to_dynamodb_type(item) for item in value]}
    elif isinstance(value, dict):
        return {'M': {k: convert_to_dynamodb_type(v) for k, v in value.items()}}
    elif value is None:
        return {'NULL': True}
    else:
        return {'S': str(value)}

def convert_from_dynamodb_format(item):
    """Convert DynamoDB item to regular Python dict."""
    result = {}
    for key, value in item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = float(value['N']) if '.' in value['N'] else int(value['N'])
        elif 'BOOL' in value:
            result[key] = value['BOOL']
        elif 'L' in value:
            result[key] = [convert_from_dynamodb_format({'item': item})['item'] for item in value['L']]
        elif 'M' in value:
            result[key] = convert_from_dynamodb_format(value['M'])
        elif 'NULL' in value:
            result[key] = None
    return result

def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Return response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body)
    }`;
        
        setFormData(prev => ({
          ...prev,
          prompt: dynamoDBPrompt
        }));
      }
    }
  }, []);

  const selectedCategoryOption = categoryOptions.find(c => c.value === formData.category);
  const selectedActionOptions = formData.actions.map(a => getActionOptions().find(opt => opt.value === a)).filter(Boolean);

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      header="Edit Blueprint"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={onDismiss}>Cancel</Button>
            <Button 
              variant="primary" 
              onClick={handleSave}
              loading={isSaving}
            >
              Save
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        <FormField label="Name">
          <Input
            value={formData.name}
            onChange={({ detail }) => setFormData({
              ...formData,
              name: detail.value
            })}
          />
        </FormField>

        <FormField label="Description">
          <Textarea
            value={formData.description}
            onChange={({ detail }) => setFormData({
              ...formData,
              description: detail.value
            })}
            rows={2}
          />
        </FormField>

        <FormField label="Category">
          <Select
            selectedOption={selectedCategoryOption}
            onChange={({ detail }) => setFormData({
              ...formData,
              category: detail.selectedOption.value
            })}
            options={categoryOptions}
          />
        </FormField>

        <FormField label="Service Type">
          <Input
            value={formData.service_type}
            readOnly
            disabled
          />
        </FormField>

        {formData.category === 'aws-services' && (
          <FormField label="Actions">
            <Multiselect
              selectedOptions={selectedActionOptions}
              onChange={({ detail }) => {
                const newActions = detail.selectedOptions.map(opt => opt.value);
                setFormData({
                  ...formData,
                  actions: newActions
                });
                updatePromptWithActions(newActions, formData.service_type);
              }}
              options={getActionOptions()}
            />
          </FormField>
        )}

        {formData.service_type === 'rds' && formData.actions.includes('select') && (
          <FormField 
            label="What are you trying to achieve?" 
            description="Describe in natural language what you want to accomplish with the Select operation"
          >
            <Textarea
              value={formData.naturalLanguageInput || ''}
              onChange={({ detail }) => setFormData({
                ...formData,
                naturalLanguageInput: detail.value
              })}
              placeholder="Example: I want to retrieve all customer records from the users table where the status is active"
              rows={3}
              resize="vertical"
            />
          </FormField>
        )}

        <FormField label="Prompt">
          <Textarea
            value={formData.prompt}
            onChange={({ detail }) => setFormData({
              ...formData,
              prompt: detail.value
            })}
            rows={4}
          />
        </FormField>

        <FormField label="Code">
          <Textarea
            value={formData.code}
            onChange={({ detail }) => setFormData({
              ...formData,
              code: detail.value
            })}
            rows={6}
          />
        </FormField>
      </SpaceBetween>
    </Modal>
  );
};

export default ManageBlueprintItemForm;