import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  Button,
  Table,
  Box,
  Alert,
  StatusIndicator,
  Input,
  SpaceBetween,
  Pagination,
  Modal,
  FormField,
  Textarea,
  Select
} from '@cloudscape-design/components';

const OnboardLambda = ({ onCancel, credentials }) => {
  const [functions, setFunctions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const pageSize = 10;
  const [showModal, setShowModal] = useState(false);
  const [selectedFunction, setSelectedFunction] = useState(null);
  const [toolName, setToolName] = useState('');
  const [toolDescription, setToolDescription] = useState('');
  const [inputSchema, setInputSchema] = useState('');
  const [schemaInputType, setSchemaInputType] = useState({ label: 'Manual Input', value: 'manual' });
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [userPrompt, setUserPrompt] = useState('');
  const [generatedResponse, setGeneratedResponse] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [showGeneratedResponse, setShowGeneratedResponse] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [lambdaParameters, setLambdaParameters] = useState([]);
  const [gateways, setGateways] = useState([]);
  const [gatewayData, setGatewayData] = useState([]);
  const [selectedGateway, setSelectedGateway] = useState(null);
  const [loadingGateways, setLoadingGateways] = useState(false);
  const [onboarding, setOnboarding] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  const loadGateways = async () => {
    setLoadingGateways(true);
    try {
      const response = await fetch('https://mrg5d7itwh.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          action: 'list_gateway'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Raw backend response:', data);
      console.log('First item from backend:', data[0]);
      console.log('Keys in first item:', Object.keys(data[0] || {}));
      
      // Store complete gateway data
      setGatewayData(data);
      
      // Create options with names only
      const gatewayOptions = data.map(gateway => ({
        label: gateway.name,
        value: gateway.name
      }));
      setGateways(gatewayOptions);
    } catch (err) {
      console.error('Gateway loading error:', err);
      setError(`Failed to load gateways: ${err.message}`);
    } finally {
      setLoadingGateways(false);
    }
  };

  const callAPI = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('https://f2d565nd20.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          action: 'list_lambda'
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      setFunctions(data.functions || []);
    } catch (err) {
      console.error('API call error:', err);
      setError(`Failed to load Lambda functions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    callAPI();
  }, []);

  const filteredFunctions = functions.filter(func => 
    !searchQuery || 
    func.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    func.runtime?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const paginatedFunctions = filteredFunctions.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  const handleOnboard = () => {
    if (selectedItems.length === 0) {
      setError('Please select a Lambda function to onboard');
      return;
    }
    console.log('Onboarding function:', selectedItems[0]);
    // TODO: Implement onboarding logic
  };

  const columnDefinitions = [
    {
      id: 'name',
      header: 'Function Name',
      cell: item => item.name || 'N/A',
      sortingField: 'name'
    },
    {
      id: 'runtime',
      header: 'Runtime',
      cell: item => item.runtime || 'N/A',
      sortingField: 'runtime'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <Button
          iconName="upload"
          variant="icon"
          onClick={() => {
            setSelectedFunction(item);
            setToolName('');
            setToolDescription('');
            setInputSchema('');
            setSchemaInputType({ label: 'Manual Input', value: 'manual' });
            setUserPrompt('');
            setShowGeneratedResponse(false);
            setGeneratedResponse('');
            setSelectedGateway(null);
            loadGateways();
            setShowModal(true);
          }}
          ariaLabel="Onboard"
        />
      )
    }
  ];

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <Button onClick={onCancel}>
              Back
            </Button>
          }
        >
          Lambda Functions
        </Header>
      }
    >
      {error && (
        <Alert
          statusIconAriaLabel="Error"
          type="error"
          dismissible
          onDismiss={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert
          statusIconAriaLabel="Success"
          type="success"
          dismissible
          onDismiss={() => setSuccessMessage(null)}
        >
          {successMessage}
        </Alert>
      )}

      <SpaceBetween direction="vertical" size="l">
        <Input
          value={searchQuery}
          onChange={({ detail }) => {
            setSearchQuery(detail.value);
            setCurrentPageIndex(1);
          }}
          placeholder="Search Lambda functions..."
          type="search"
        />

        {loading ? (
          <Box margin={{ vertical: 'xs' }} textAlign="center">
            <StatusIndicator type="loading">Loading Lambda functions...</StatusIndicator>
          </Box>
        ) : (
          <Table
            items={paginatedFunctions}
            columnDefinitions={columnDefinitions}
            header={
              <Header 
                counter={`(${filteredFunctions.length})`}
actions={
                  <Button
                    iconName="refresh"
                    variant="icon"
                    onClick={callAPI}
                    loading={loading}
                    ariaLabel="Refresh"
                  />
                }
              >
                Available Lambda Functions
              </Header>
            }
            pagination={
              <Pagination
                currentPageIndex={currentPageIndex}
                pagesCount={Math.ceil(filteredFunctions.length / pageSize)}
                onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
              />
            }
            empty={
              <Box margin={{ vertical: 'xs' }} textAlign="center">
                <b>No Lambda functions found</b>
              </Box>
            }
          />
        )}
      </SpaceBetween>

      <Modal
        visible={showModal}
        onDismiss={() => setShowModal(false)}
        header="Onboard Lambda Function"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={() => setShowModal(false)}>Cancel</Button>
              <Button 
                variant="primary" 
                onClick={async () => {
                  setOnboarding(true);
                  setError(null);
                  
                  try {
                    // Generate inlinePayload based on schema input type
                    let inlinePayload;
                    if (schemaInputType.value === 'manual') {
                      try {
                        const schema = JSON.parse(inputSchema);
                        inlinePayload = [{
                          name: toolName,
                          description: toolDescription,
                          inputSchema: schema
                        }];
                      } catch (e) {
                        throw new Error('Invalid JSON schema');
                      }
                    } else {
                      // Generate from parameters
                      inlinePayload = lambdaParameters.map(param => {
                        const requiredFields = param.required ? [param.name] : [];
                        return {
                          name: `${toolName}_${param.name}`,
                          description: `${toolDescription} using ${param.name}`,
                          inputSchema: {
                            type: "object",
                            properties: {
                              [param.name]: { type: param.dataType?.value || "string" }
                            },
                            ...(requiredFields.length > 0 && { required: requiredFields })
                          }
                        };
                      });
                    }
                    
                    console.log('Selected Gateway:', selectedGateway);
                    console.log('Gateway Identifier being sent:', selectedGateway?.value);
                    
                    const gatewayId = gatewayData.find(g => g.name === selectedGateway?.value)?.gatewayId;
                    console.log('Onboard API - Gateway ID being sent:', gatewayId);
                    
                    const payload = {
                      action: 'onboard_lambda',
                      gatewayIdentifier: gatewayId,
                      name: selectedFunction?.name,
                      targetConfiguration: {
                        mcp: {
                          lambda: {
                            lambdaArn: selectedFunction?.arn,
                            toolSchema: {
                              inlinePayload: inlinePayload
                            }
                          }
                        }
                      },
                      credentialProviderConfigurations: [{ credentialProviderType: "GATEWAY_IAM_ROLE" }]
                    };
                    
                    const response = await fetch('https://mrg5d7itwh.execute-api.us-east-1.amazonaws.com/dev', {
                      method: 'POST',
                      mode: 'cors',
                      headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                      },
                      body: JSON.stringify(payload)
                    });
                    
                    if (!response.ok) {
                      const errorData = await response.json();
                      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
                    
                    const result = await response.json();
                    console.log('Lambda onboarded successfully:', result);
                    setSuccessMessage(`Lambda function "${selectedFunction?.name}" onboarded successfully to gateway!`);
                    setShowModal(false);
                    
                  } catch (e) {
                    console.error('Onboarding error:', e);
                    setError(`Onboarding failed: ${e.message}`);
                  } finally {
                    setOnboarding(false);
                  }
                }}
                disabled={!toolName || !toolDescription || !selectedGateway || (schemaInputType.value === 'manual' ? !inputSchema : (schemaInputType.value === 'prompt' && lambdaParameters.length === 0))}
                loading={onboarding}
              >
                Onboard
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <Box>
            <strong>Lambda Function Details:</strong>
            <br />Name: {selectedFunction?.name}
            <br />Runtime: {selectedFunction?.runtime}
          </Box>
          
          <FormField label="MCP Gateway">
            <Select
              selectedOption={selectedGateway}
              onChange={({ detail }) => {
                const selectedName = detail.selectedOption?.value;
                console.log('Selected Gateway Name:', selectedName);
                console.log('Available gatewayData:', gatewayData);
                console.log('Gateway names in data:', gatewayData.map(g => g.name));
                const gatewayInfo = gatewayData.find(g => g.name === selectedName);
                console.log('Found Gateway Info:', gatewayInfo);
                console.log('Found Gateway ID:', gatewayInfo?.gatewayId);
                setSelectedGateway(detail.selectedOption);
              }}
              options={gateways}
              placeholder="Select an MCP Gateway"
              loading={loadingGateways}
              loadingText="Loading gateways..."
            />
            {selectedGateway && (
              <Box margin={{ top: 'xs' }} color="text-status-info">
                <strong>Selected Gateway ID:</strong> {selectedGateway.value}
              </Box>
            )}
          </FormField>
          
          <FormField label="Tool Name">
            <Input
              value={toolName}
              onChange={({ detail }) => setToolName(detail.value)}
              placeholder="Enter tool name (e.g., get_weather)"
            />
          </FormField>
          
          <FormField label="Tool Description">
            <Input
              value={toolDescription}
              onChange={({ detail }) => setToolDescription(detail.value)}
              placeholder="Enter tool description (e.g., Get weather for a location)"
            />
          </FormField>
          
          <FormField label="Input Schema Method">
            <Select
              selectedOption={schemaInputType}
              onChange={({ detail }) => setSchemaInputType(detail.selectedOption)}
              options={[
                { label: 'Manual Input', value: 'manual' },
                { label: 'Generate', value: 'prompt' }
              ]}
            />
          </FormField>
          
          {schemaInputType.value === 'manual' ? (
            <FormField label="Input Schema (JSON)">
              <Textarea
                value={inputSchema}
                onChange={({ detail }) => setInputSchema(detail.value)}
                placeholder={`{
  "type": "object",
  "properties": {
    "location": {"type": "string"}
  },
  "required": ["location"]
}`}
                rows={8}
              />
            </FormField>
          ) : (
            <>
              <FormField label="Lambda Parameters">
                <SpaceBetween direction="vertical" size="s">
                  {lambdaParameters.map((param, index) => (
                    <Box key={index} padding="s" variant="outlined">
                      <SpaceBetween direction="vertical" size="xs">
                        <SpaceBetween direction="horizontal" size="s">
                          <FormField label="Parameter Name" stretch>
                            <Input
                              value={param.name || ''}
                              onChange={({ detail }) => {
                                const updated = [...lambdaParameters];
                                updated[index] = { ...updated[index], name: detail.value };
                                setLambdaParameters(updated);
                              }}
                              placeholder="e.g., location"
                            />
                          </FormField>
                          <FormField label="Data Type">
                            <Select
                              selectedOption={param.dataType || null}
                              onChange={({ detail }) => {
                                const updated = [...lambdaParameters];
                                updated[index] = { ...updated[index], dataType: detail.selectedOption };
                                setLambdaParameters(updated);
                              }}
                              options={[
                                { label: 'String', value: 'string' },
                                { label: 'Number', value: 'number' },
                                { label: 'Integer', value: 'integer' },
                                { label: 'Boolean', value: 'boolean' },
                                { label: 'Object', value: 'object' },
                                { label: 'Array', value: 'array' }
                              ]}
                              placeholder="Select type"
                            />
                          </FormField>
                          <FormField label="Required">
                            <input
                              type="checkbox"
                              checked={param.required || false}
                              onChange={(e) => {
                                const updated = [...lambdaParameters];
                                updated[index] = { ...updated[index], required: e.target.checked };
                                setLambdaParameters(updated);
                              }}
                            />
                          </FormField>
                          <Box paddingTop="l">
                            <Button
                              iconName="remove"
                              variant="icon"
                              onClick={() => {
                                const updated = lambdaParameters.filter((_, i) => i !== index);
                                setLambdaParameters(updated);
                              }}
                              ariaLabel="Remove parameter"
                            />
                          </Box>
                        </SpaceBetween>
                        <FormField label="Description">
                          <Input
                            value={param.description || ''}
                            onChange={({ detail }) => {
                              const updated = [...lambdaParameters];
                              updated[index] = { ...updated[index], description: detail.value };
                              setLambdaParameters(updated);
                            }}
                            placeholder="Describe this parameter"
                          />
                        </FormField>
                      </SpaceBetween>
                    </Box>
                  ))}
                  <SpaceBetween direction="horizontal" size="s">
                    <Button
                      iconName="add-plus"
                      onClick={() => {
                        setLambdaParameters([...lambdaParameters, { name: '', description: '', dataType: null, required: false }]);
                      }}
                    >
                      Add Parameter
                    </Button>
                    <Button
                      onClick={() => {
                        setIsGenerating(true);
                        setShowGeneratedResponse(true);
                        
                        // Generate inlinePayload from parameters
                        const inlinePayload = lambdaParameters.length > 0 ? lambdaParameters.map(param => {
                          const requiredFields = param.required ? [param.name] : [];
                          return {
                            name: `${toolName}_${param.name}`,
                            description: `${toolDescription} using ${param.name}`,
                            inputSchema: {
                              type: "object",
                              properties: {
                                [param.name]: { type: param.dataType?.value || "string" }
                              },
                              ...(requiredFields.length > 0 && { required: requiredFields })
                            }
                          };
                        }) : [];
                        
                        // Generate target configuration in the required format
                        const targetConfigString = `targetConfiguration={
    "mcp": {
        "lambda": {
            "lambdaArn": "${selectedFunction?.arn || ''}",
            "toolSchema": {
                "inlinePayload": ${JSON.stringify(inlinePayload, null, 16).replace(/^/gm, '                ')}
            }
        }
    }
}`;
                        
                        setGeneratedResponse(targetConfigString);
                        setIsGenerating(false);
                      }}
                      variant="primary"
                      loading={isGenerating}
                    >
                      Generate Target Body
                    </Button>
                  </SpaceBetween>
                </SpaceBetween>
              </FormField>
              
              {showGeneratedResponse && (
                <FormField label="Generated Target Body">
                  <Textarea
                    value={generatedResponse}
                    readOnly
                    placeholder="Generated target body will appear here..."
                    rows={12}
                  />
                </FormField>
              )}
            </>
          )}
        </SpaceBetween>
      </Modal>

      <Modal
        visible={showPromptModal}
        onDismiss={() => setShowPromptModal(false)}
        header="Generate Input Schema from Prompt"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={() => setShowPromptModal(false)}>Cancel</Button>
              <Button 
                variant="primary" 
                onClick={() => {
                  // Generate schema from prompt
                  const generatedSchema = `{
  "type": "object",
  "properties": {
    "input": {"type": "string", "description": "${userPrompt}"}
  },
  "required": ["input"]
}`;
                  setInputSchema(generatedSchema);
                  setShowPromptModal(false);
                }}
                disabled={!userPrompt.trim()}
              >
                Generate Schema
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <FormField label="Describe your Lambda function's expected input">
            <Textarea
              value={userPrompt}
              onChange={({ detail }) => setUserPrompt(detail.value)}
              placeholder="Example: This function needs a location string to get weather data, and an optional units parameter that can be 'celsius' or 'fahrenheit'"
              rows={6}
            />
          </FormField>
        </SpaceBetween>
      </Modal>
    </Container>
  );
};

export default OnboardLambda;