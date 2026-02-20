import React, { useState } from 'react';
import {
  Container,
  Header,
  FormField,
  Input,
  Button,
  SpaceBetween,
  Table,
  Box,
  Alert,
  RadioGroup,
  Textarea,
  ExpandableSection,
  StatusIndicator,
  KeyValuePairs
} from '@cloudscape-design/components';

const SemanticSearchForm = ({ onCancel, credentials }) => {
  const [mode, setMode] = useState('search');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [gatewayName, setGatewayName] = useState(`mcp-gateways-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)}`);
  const [authType, setAuthType] = useState('OAuth');
  
  // New state for gateway management
  const [gatewayDetails, setGatewayDetails] = useState(null);
  const [availableTools, setAvailableTools] = useState([]);
  const [gatewayCreating, setGatewayCreating] = useState(false);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [gatewayUrl, setGatewayUrl] = useState('');
  const [availableGateways, setAvailableGateways] = useState([]);
  const [selectedGateway, setSelectedGateway] = useState('');
  const [gatewaySearchQuery, setGatewaySearchQuery] = useState('');

  // Load gateways on component mount since default mode is 'search'
  React.useEffect(() => {
    if (mode === 'search') {
      listGateways();
    }
  }, []);

  const callLambdaAPI = async (payload) => {
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
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();
    return data;
  };

  const createGateway = async () => {
    setGatewayCreating(true);
    setError(null);
    
    try {
      const payload = {
        action: 'create_gateway',
        client_id: credentials.username,
        client_secret: credentials.password,
        client_name: gatewayName,
        cognito_domain: 'us-east-1_zNTJHiWSu',
        authorizer_type: authType === 'OAuth' ? 'CUSTOM_JWT' : 'AWS_IAM'
      };
      
      const gatewayData = await callLambdaAPI(payload);
      setGatewayDetails(gatewayData);
      
      // Clear any previous errors
      setError(null);
      
    } catch (err) {
      console.error('Gateway creation error:', err);
      setError(`Gateway creation failed: ${err.message}`);
    } finally {
      setGatewayCreating(false);
    }
  };

  const listGateways = async () => {
    setToolsLoading(true);
    setError(null);
    
    try {
      const payload = {
        action: 'list_gateway'
      };
      
      const gatewaysData = await callLambdaAPI(payload);
      // Response is now a direct array of gateway objects
      const readyGateways = (Array.isArray(gatewaysData) ? gatewaysData : []).filter(gateway => gateway.status === 'READY');
      setAvailableGateways(readyGateways);
    } catch (err) {
      console.error('List gateways error:', err);
      setError(`Failed to list gateways: ${err.message}`);
    } finally {
      setToolsLoading(false);
    }
  };

  const listTools = async (url = gatewayUrl) => {
    if (!url) {
      setError('Gateway URL is required to list tools');
      return;
    }

    setToolsLoading(true);
    setError(null);
    
    try {
      const payload = {
        action: 'list_tools',
        client_id: credentials.username,
        client_secret: credentials.password,
        cognito_domain: 'us-east-1_zNTJHiWSu',
        gateway_url: url
      };
      
      const toolsData = await callLambdaAPI(payload);
      setAvailableTools(toolsData.tools || []);
    } catch (err) {
      console.error('List tools error:', err);
      setError(`Failed to list tools: ${err.message}`);
    } finally {
      setToolsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    if (!gatewayUrl) {
      setError('Gateway URL is required for search');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const payload = {
        action: 'search',
        client_id: credentials.username,
        client_secret: credentials.password,
        cognito_domain: 'us-east-1_zNTJHiWSu',
        query: query,
        gateway_url: gatewayUrl,
        tool_name: 'x_amz_bedrock_agentcore_search'
      };
      
      const searchData = await callLambdaAPI(payload);
      setResults(searchData.results || []);
    } catch (err) {
      console.error('Search error:', err);
      setError(`Search failed: ${err.message}`);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const searchResultColumns = [
    {
      id: 'name',
      header: 'Tool Name',
      cell: item => item.name || 'N/A',
      sortingField: 'name'
    },
    {
      id: 'description',
      header: 'Description',
      cell: item => item.description || 'N/A',
      sortingField: 'description'
    },
    {
      id: 'score',
      header: 'Relevance Score',
      cell: item => item.score ? item.score.toFixed(3) : 'N/A',
      sortingField: 'score'
    }
  ];

  const toolsColumns = [
    {
      id: 'name',
      header: 'Tool Name',
      cell: item => item.name || 'N/A',
      sortingField: 'name'
    },
    {
      id: 'description',
      header: 'Description',
      cell: item => item.description || 'N/A',
      sortingField: 'description'
    },
    {
      id: 'inputSchema',
      header: 'Input Schema',
      cell: item => item.inputSchema ? JSON.stringify(item.inputSchema, null, 2) : 'N/A'
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
          Semantic Search
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
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

        <FormField label="Mode">
          <RadioGroup
            value={mode}
            onChange={({ detail }) => {
              setMode(detail.value);
              if (detail.value === 'search') {
                listGateways();
              }
            }}
            items={[
              { value: 'create', label: 'Create Gateway' },
              { value: 'search', label: 'Search For Tools' }
            ]}
          />
        </FormField>

        {mode === 'create' && (
          <SpaceBetween direction="vertical" size="s">
            <FormField label="Authentication Type">
              <RadioGroup
                value={authType}
                onChange={({ detail }) => setAuthType(detail.value)}
                items={[
                  { value: 'OAuth', label: 'OAuth' },
                  { value: 'IAM', label: 'IAM' }
                ]}
              />
            </FormField>
            <FormField label="Gateway Name">
              <Input
                value={gatewayName}
                onChange={({ detail }) => {
                  // Only allow alphanumeric and hyphens, max 100 chars
                  const sanitized = detail.value.replace(/[^0-9a-zA-Z-]/g, '').slice(0, 100);
                  setGatewayName(sanitized);
                }}
                placeholder="Enter gateway name (alphanumeric and hyphens only)..."
              />
            </FormField>
          </SpaceBetween>
        )}

        {mode === 'search' && (
          <>
            <FormField label="Search Query">
              <Input
                value={query}
                onChange={({ detail }) => setQuery(detail.value)}
                placeholder="Enter your search query..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSearch();
                  }
                }}
              />
            </FormField>


          </>
        )}

        {gatewayDetails && (
          <ExpandableSection headerText="Gateway Details" defaultExpanded>
            <SpaceBetween direction="vertical" size="s">
              <StatusIndicator type="success">Gateway Created Successfully</StatusIndicator>
              <KeyValuePairs
                columns={2}
                items={[
                  { label: 'Gateway Name', value: gatewayDetails.gateway?.name || gatewayName },
                  { label: 'Gateway ARN', value: gatewayDetails.gateway?.gatewayArn || 'N/A' }
                ]}
              />
            </SpaceBetween>
          </ExpandableSection>
        )}

        {mode === 'search' && availableGateways.length > 0 && (
          <SpaceBetween direction="vertical" size="s">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontWeight: '600', fontSize: '14px', color: '#16191f' }}>
                Available Gateways ({availableGateways.length})
              </label>
              <Button
                iconName="refresh"
                variant="icon"
                onClick={listGateways}
                loading={toolsLoading}
                ariaLabel="Refresh gateway list"
              />
            </div>
            <Input
              value={gatewaySearchQuery}
              onChange={({ detail }) => setGatewaySearchQuery(detail.value)}
              placeholder="Search gateways..."
              type="search"
            />
            <Table
              items={availableGateways.filter(gateway => 
                !gatewaySearchQuery || 
                gateway.name?.toLowerCase().includes(gatewaySearchQuery.toLowerCase()) ||
                gateway.status?.toLowerCase().includes(gatewaySearchQuery.toLowerCase())
              )}
              columnDefinitions={[
                {
                  id: 'select',
                  header: 'Select',
                  cell: item => (
                    <input
                      type="radio"
                      name="gateway"
                      value={item.name}
                      checked={selectedGateway === item.gatewayId}
                      onChange={() => {
                        setSelectedGateway(item.gatewayId);
                        setGatewayUrl(`https://${item.gatewayId}.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`);
                      }}
                    />
                  )
                },
                {
                  id: 'name',
                  header: 'Gateway Name',
                  cell: item => item.name || 'N/A'
                },
                {
                  id: 'status',
                  header: 'Status',
                  cell: item => item.status || 'N/A'
                }
              ]}
              empty={
                <Box margin={{ vertical: 'xs' }} textAlign="center">
                  <b>No gateways found</b>
                </Box>
              }
            />
          </SpaceBetween>
        )}

        {mode === 'search' && selectedGateway && (
          <SpaceBetween direction="horizontal" size="s">
            <Button
              onClick={() => listTools()}
              loading={toolsLoading}
              disabled={!gatewayUrl}
            >
              List Available Tools
            </Button>
          </SpaceBetween>
        )}

        {availableTools.length > 0 && (
          <ExpandableSection headerText={`Available Tools (${availableTools.length})`} defaultExpanded>
            <Table
              items={availableTools}
              columnDefinitions={toolsColumns}
              empty={
                <Box margin={{ vertical: 'xs' }} textAlign="center">
                  <b>No tools available</b>
                </Box>
              }
            />
          </ExpandableSection>
        )}

        <SpaceBetween direction="horizontal" size="s">
          {mode === 'create' && (
            <Button
              variant="primary"
              onClick={createGateway}
              loading={gatewayCreating}
              disabled={!gatewayName.trim()}
            >
              Create Gateway
            </Button>
          )}
          {mode === 'search' && (
            <Button
              variant="primary"
              onClick={handleSearch}
              loading={loading}
              disabled={!query.trim() || !selectedGateway}
            >
              Search Tools
            </Button>
          )}
        </SpaceBetween>

        {mode === 'search' && results.length > 0 && (
          <Table
            items={results}
            columnDefinitions={searchResultColumns}
            header={
              <Header counter={`(${results.length})`}>
                Search Results
              </Header>
            }
            empty={
              <Box margin={{ vertical: 'xs' }} textAlign="center">
                <b>No results found</b>
              </Box>
            }
          />
        )}
      </SpaceBetween>
    </Container>
  );
};

export default SemanticSearchForm;