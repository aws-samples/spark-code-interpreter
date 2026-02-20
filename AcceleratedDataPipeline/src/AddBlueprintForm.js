import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Header, 
  FormField, 
  Select, 
  Button, 
  SpaceBetween,
  Multiselect,
  Textarea,
  Tabs
} from '@cloudscape-design/components';

const AddBlueprintForm = ({ onCancel }) => {
  const [blueprintName, setBlueprintName] = useState('');
  const [blueprintDescription, setBlueprintDescription] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const [selectedActions, setSelectedActions] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [code, setCode] = useState('');
  const [customToolTab, setCustomToolTab] = useState('prompt');

  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [naturalLanguageInput, setNaturalLanguageInput] = useState('');

  const resetForm = () => {
    setBlueprintName('');
    setBlueprintDescription('');
    setSelectedCategory(null);
    setSelectedService(null);
    setSelectedActions([]);
    setPrompt('');
    setCode('');
    setCustomToolTab('prompt');
    setIsEditing(false);
    setNaturalLanguageInput('');
  };

  const categoryOptions = [
    { label: 'AWS Services', value: 'aws-services' },
    { label: 'Functions', value: 'functions' },
    { label: 'Build your own tool', value: 'custom-tool' }
  ];

  const awsServiceOptions = [
    { label: 'S3', value: 's3' },
    { label: 'DynamoDB', value: 'dynamodb' },
    { label: 'RDS', value: 'rds' }
  ];

  const functionOptions = [
    { label: 'Math', value: 'math' },
    { label: 'String', value: 'string' }
  ];

  const getActionOptions = () => {
    if (selectedService?.value === 'rds') {
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

  const getServiceOptions = () => {
    if (selectedCategory?.value === 'aws-services') return awsServiceOptions;
    if (selectedCategory?.value === 'functions') return functionOptions;
    return [];
  };

  const PROMPT_TEMPLATES = {
    FUNCTION: (service) => `Create individual functions for the ${service} operations. Just return the individual function code, always use python3 or boto3 client. do not generate the entire python code just the function , prefix all the functions with @mcp.tool(), do not provide any additional context`,
    AWS_SERVICE: (service, actions) => `Create individual functions for each of the ${service} operations ${actions} for object. Just return the individual function code, always use python3 or boto3 client. do not generate the entire python code just the function , prefix all the functions with @mcp.tool(), do not provide any additional context including \`\`\`python or \`\`\``,
    DYNAMODB: (actions) => `Create individual functions for DynamoDB for each of the actions: ${actions}. Just return the individual code and not not entire python code, use boto3 client approach to generate the code, ensure that dynamodb type_code is included for the attribute, prefix all the functions with @mcp.tool(). Only generate the required code do not provide any additional context, use the following as a reference code 
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
    }`,
    RDS: (actions) => `Create individual functions for each of the RDS operations ${actions} selected by users. Just return the individual function code, always use python3 or boto3 client. do not generate the entire python code just the function , prefix all the functions with @mcp.tool(), do not provide any additional context including \`\`\`python or \`\`\`, Only for action type as select, as the query as paramter, don't hardcode the select query`
  };

  const generateDefaultPrompt = () => {
    const service = selectedService?.label;
    
    if (selectedCategory?.value === 'functions') {
      setPrompt(PROMPT_TEMPLATES.FUNCTION(service));
    } else if (selectedService?.value === 'rds') {
      const actions = selectedActions.map(a => a.label).join(', ');
      setPrompt(PROMPT_TEMPLATES.RDS(actions));
    } else if (selectedService?.value === 'dynamodb') {
      const actions = selectedActions.map(a => a.label).join(', ');
      setPrompt(PROMPT_TEMPLATES.DYNAMODB(actions));
    } else if (selectedService?.value === 's3') {
      const actions = selectedActions.map(a => a.label).join(', ');
      setPrompt(PROMPT_TEMPLATES.AWS_SERVICE(service, actions));
    }
  };

  const API_URL = 'https://77a9252l49.execute-api.us-east-1.amazonaws.com/dev';

  const handleSavePrompt = () => {
    setIsEditing(false);
    // Save logic here
  };

  const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const validateForm = () => {
    if (!blueprintName.trim()) return 'Blueprint Name is required';
    if (!blueprintDescription.trim()) return 'Blueprint Description is required';
    if (!selectedCategory) return 'Category is required';
    
    if (selectedCategory.value === 'custom-tool') {
      if (!prompt.trim() && !code.trim()) return 'Either prompt or code is required';
    } else {
      if (!prompt.trim()) return 'Prompt is required';
    }
    
    if (selectedCategory.value === 'aws-services') {
      if (!selectedService) return 'Service selection is required';
      if (selectedActions.length === 0) return 'At least one action must be selected';
    } else if (selectedCategory.value === 'functions') {
      if (!selectedService) return 'Function type selection is required';
    }
    
    return null;
  };

  const handleAddBlueprint = async () => {
    const validationError = validateForm();
    if (validationError) {
      alert(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const toolId = generateUUID();
      const payload = {
        action: 'add',
        tool_id: toolId,
        name: blueprintName,
        description: blueprintDescription,
        category: selectedCategory.value
      };

      if (selectedCategory.value === 'aws-services') {
        payload.service_type = selectedService.value;
        payload.actions = selectedActions.map(a => a.value);
        payload.prompt = prompt;
        payload.nlpPrompt = naturalLanguageInput || '';
      } else if (selectedCategory.value === 'functions') {
        payload.service_type = selectedService.value;
        payload.prompt = prompt;
      } else if (selectedCategory.value === 'custom-tool') {
        payload.service_type = 'BYOT';
        payload.prompt = prompt || '';
        payload.code = code || '';
      }

      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const createNew = window.confirm('Record was successfully added! Do you want to create a new blueprint?');
        if (createNew) {
          resetForm();
        } else {
          onCancel();
        }
      } else {
        throw new Error('Failed to add blueprint');
      }
    } catch (error) {
      console.error('Error adding blueprint:', error);
      alert('Error adding blueprint. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (selectedActions.length > 0 && selectedService) {
      generateDefaultPrompt();
    }
  }, [selectedActions, selectedService, generateDefaultPrompt]);

  return (
    <Container header={<Header variant="h2">Add Blueprint</Header>}>
      <SpaceBetween direction="vertical" size="l">
        <FormField label="Blueprint Name">
          <Textarea
            value={blueprintName}
            onChange={({ detail }) => setBlueprintName(detail.value)}
            placeholder="Enter blueprint name"
            rows={1}
            resize="none"
          />
        </FormField>

        <FormField label="Blueprint Description">
          <Textarea
            value={blueprintDescription}
            onChange={({ detail }) => setBlueprintDescription(detail.value)}
            placeholder="Enter blueprint description"
            rows={2}
            resize="none"
          />
        </FormField>

        <FormField label="Category">
          <Select
            selectedOption={selectedCategory}
            onChange={({ detail }) => {
              setSelectedCategory(detail.selectedOption);
              setSelectedService(null);
              setSelectedActions([]);
              if (detail.selectedOption?.value === 'custom-tool') {
                setPrompt('');
                setCode('');
                setCustomToolTab('prompt');
                setIsEditing(true);
              } else {
                setPrompt('');
              }
            }}
            options={categoryOptions}
            placeholder="Select Category"
          />
        </FormField>

        {selectedCategory && selectedCategory.value !== 'custom-tool' && (
          <FormField label={selectedCategory.value === 'aws-services' ? 'AWS Service' : 'Function Type'}>
            <Select
              selectedOption={selectedService}
              onChange={({ detail }) => {
                setSelectedService(detail.selectedOption);
                setSelectedActions([]);
                if (selectedCategory?.value === 'functions') {
                  const service = detail.selectedOption?.label;
                  setPrompt(PROMPT_TEMPLATES.FUNCTION(service));
                } else {
                  setPrompt('');
                }
              }}
              options={getServiceOptions()}
              placeholder={`Select ${selectedCategory.label}`}
            />
          </FormField>
        )}

        {selectedService && selectedCategory?.value === 'aws-services' && (
          <FormField label="Actions">
            <Multiselect
              selectedOptions={selectedActions}
              onChange={({ detail }) => {
                setSelectedActions(detail.selectedOptions);
                setPrompt('');
              }}
              options={getActionOptions()}
              placeholder="Select Actions"
            />
          </FormField>
        )}

        {selectedService?.value === 'rds' && selectedActions.some(action => action.value === 'select') && (
          <FormField 
            label="What are you trying to achieve?" 
            description="Describe in natural language what you want to accomplish with the Select operation"
          >
            <Textarea
              value={naturalLanguageInput}
              onChange={({ detail }) => setNaturalLanguageInput(detail.value)}
              placeholder="Example: I want to retrieve all customer records from the users table where the status is active"
              rows={3}
              resize="vertical"
            />
          </FormField>
        )}

        {selectedCategory?.value === 'custom-tool' && (
          <FormField 
            label="Input" 
            description="Provide either a prompt or paste your code"
          >
            <Tabs
              activeTabId={customToolTab}
              onChange={({ detail }) => setCustomToolTab(detail.activeTabId)}
              tabs={[
                {
                  label: 'Prompt',
                  id: 'prompt',
                  content: (
                    <div style={{ position: 'relative' }}>
                      <Textarea
                        value={prompt}
                        onChange={({ detail }) => setPrompt(detail.value)}
                        placeholder="Enter your prompt for generating the MCP tool"
                        rows={6}
                        resize="none"

                      />

                    </div>
                  )
                },
                {
                  label: 'Code',
                  id: 'code',
                  content: (
                    <Textarea
                      value={code}
                      onChange={({ detail }) => setCode(detail.value)}
                      placeholder="Paste your MCP tool code here"
                      rows={6}
                      resize="none"
                    />
                  )
                }
              ]}
            />
          </FormField>
        )}

        {(((selectedActions.length > 0) && (selectedCategory?.value === 'aws-services')) || ((selectedService) && (selectedCategory?.value === 'functions'))) && (
          <FormField 
            label="Prompt" 
            description="Provide instructions for the blueprint implementation"
          >
            <div style={{ position: 'relative' }}>
              <Textarea
                value={prompt}
                onChange={({ detail }) => setPrompt(detail.value)}
                placeholder="Enter your prompt or use the magic wand to auto-generate"
                rows={6}
                resize="none"
                readOnly={!isEditing}
              />
              <div style={{ 
                position: 'absolute', 
                bottom: '8px', 
                right: '8px', 
                zIndex: 1,
                display: 'flex',
                gap: '4px'
              }}>
                {!isEditing ? (
                  <Button
                    iconName="edit"
                    variant="icon"
                    onClick={() => setIsEditing(true)}
                    ariaLabel="Edit prompt"
                  />
                ) : (
                  <Button
                    iconName="check"
                    variant="icon"
                    onClick={handleSavePrompt}
                    ariaLabel="Save prompt"
                  />
                )}

              </div>
            </div>
          </FormField>
        )}

        <SpaceBetween direction="horizontal" size="xs">
          <Button onClick={onCancel}>Cancel</Button>
          <Button 
            variant="primary" 
            onClick={handleAddBlueprint}
            loading={isSubmitting}
            disabled={isSubmitting}
          >
            Add Blueprint
          </Button>
        </SpaceBetween>
      </SpaceBetween>
    </Container>
  );
};

export default AddBlueprintForm;