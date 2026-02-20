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

const OnboardRestAPI = ({ onCancel, credentials }) => {
  const [apis, setApis] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [selectedApi, setSelectedApi] = useState(null);
  const [documentation, setDocumentation] = useState('');
  const [exportLoading, setExportLoading] = useState(false);
  const [stages, setStages] = useState([]);
  const [selectedStage, setSelectedStage] = useState(null);
  const [stagesLoading, setStagesLoading] = useState(false);
  const [gateways, setGateways] = useState([]);
  const [gatewayData, setGatewayData] = useState([]);
  const [selectedGateway, setSelectedGateway] = useState(null);
  const [loadingGateways, setLoadingGateways] = useState(false);
  const [toolName, setToolName] = useState('');
  const [toolDescription, setToolDescription] = useState('');
  const [onboarding, setOnboarding] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const pageSize = 10;

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
          action: 'list_restapi'
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      setApis(data.apis || []);
    } catch (err) {
      console.error('API call error:', err);
      setError(`Failed to load REST APIs: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    callAPI();
  }, []);

  const filteredApis = apis.filter(api => 
    !searchQuery || 
    api.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    api.id?.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  const paginatedApis = filteredApis.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  const loadGateways = async () => {
    console.log('🚀 loadGateways called');
    setLoadingGateways(true);
    try {
      console.log('📤 Calling gateways API...');
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

      console.log('📥 Gateway API response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('📋 Raw backend response:', data);
      console.log('📋 First item from backend:', data[0]);
      console.log('📋 Keys in first item:', Object.keys(data[0] || {}));
      
      // Store complete gateway data (same as OnboardLambda)
      setGatewayData(data);
      
      // Create options with names only (same as OnboardLambda)
      const gatewayOptions = data.map(gateway => ({
        label: gateway.name,
        value: gateway.name
      }));
      console.log('✅ Gateway options created:', gatewayOptions);
      setGateways(gatewayOptions);
    } catch (err) {
      console.error('❌ Error loading gateways:', err);
      setGateways([]);
      setGatewayData([]);
    } finally {
      console.log('✅ loadGateways completed, setting loading to false');
      setLoadingGateways(false);
    }
  };

  const fetchStages = async (restApiId) => {
    console.log('🚀 fetchStages called with restApiId:', restApiId);
    setStagesLoading(true);
    setStages([]);
    setSelectedStage(null);
    
    try {
      const payload = {
        action: 'get_stage',
        api_id: restApiId
      };
      console.log('Calling get_stage API with payload:', payload);
      
      const response = await fetch('https://f2d565nd20.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const responseText = await response.text();
      console.log('Raw response text:', responseText);
      
      const data = JSON.parse(responseText);
      console.log('Parsed stages response:', data);
      console.log('data.stages:', data.stages);
      console.log('Type of data.stages:', typeof data.stages);
      console.log('Is data.stages an array?', Array.isArray(data.stages));
      
      // Convert stages to dropdown options - data is directly the stages array
      const stageOptions = (Array.isArray(data) ? data : []).map(stage => {
        console.log('Processing stage:', stage);
        return {
          label: stage.stage_name,
          value: stage.stage_name,
          deploymentId: stage.deploymentId
        };
      }).filter(stage => stage.label && stage.value);
      
      console.log('Final stageOptions:', stageOptions);
      setStages(stageOptions);
    } catch (err) {
      console.error('❌ Get stages error:', err);
      console.error('Error details:', err.message, err.stack);
      setStages([]);
    } finally {
      console.log('✅ fetchStages completed, setting stagesLoading to false');
      setStagesLoading(false);
    }
  };

  const handleExportAPI = async (stageOption = null) => {
    const stageToUse = stageOption || selectedStage;
    
    if (!stageToUse) {
      alert('Please select a stage first');
      return;
    }

    setExportLoading(true);
    setDocumentation('');
    
    try {
      const payload = {
        action: 'export_restapi',
        api_id: selectedApi.id,
        stage: stageToUse.value
      };
      console.log('Calling export_restapi API with payload:', payload);
      
      const response = await fetch('https://f2d565nd20.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setDocumentation(JSON.stringify(data, null, 2));
    } catch (err) {
      console.error('Export API error:', err);
      setDocumentation(`Error: ${err.message}`);
    } finally {
      setExportLoading(false);
    }
  };

  const handleOnboardAPI = async () => {
    setOnboarding(true);
    setError(null);
    
    try {
      // Get gateway ID from selected gateway
      const gatewayId = gatewayData.find(g => g.name === selectedGateway?.value)?.gatewayId;
      
      console.log('🔍 Onboard API Debug Info:');
      console.log('Selected Gateway Object:', selectedGateway);
      console.log('Selected Gateway Value:', selectedGateway?.value);
      console.log('Available Gateway Data:', gatewayData);
      console.log('Found Gateway ID:', gatewayId);
      console.log('Tool Name:', toolName);
      console.log('Tool Description:', toolDescription);
      console.log('Documentation Length:', documentation?.length);
      console.log('Documentation Content:', documentation);
      
      const payload = {
        action: 'onboard_api',
        gatewayIdentifier: gatewayId,
        name: toolName,
        description: toolDescription,
        inlinePayload: documentation,
        credentialProviderConfigurations: [{ credentialProviderType: "GATEWAY_IAM_ROLE" }],
        client_id: credentials?.username,        // Username
        client_secret: credentials?.password,    // Password  
        client_name: selectedGateway?.value,     // Gateway name
        cognito_domain: 'us-east-1_zNTJHiWSu'   // Pool ID
      };
      
      console.log('📤 Complete Payload being sent:');
      console.log(JSON.stringify(payload, null, 2));
      
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
      console.log('REST API onboarded successfully:', result);
      setSuccessMessage(`REST API "${selectedApi?.name}" onboarded successfully to gateway!`);
      setShowModal(false);
      
    } catch (e) {
      console.error('Onboarding error:', e);
      setError(`Onboarding failed: ${e.message}`);
    } finally {
      setOnboarding(false);
    }
  };

  const handleOnboard = async (api) => {
    setSelectedApi(api);
    setDocumentation('');
    setSelectedStage(null);
    setSelectedGateway(null);
    setToolName('');
    setToolDescription('');
    
    // Load gateways first, then fetch stages, then show modal (same as OnboardLambda)
    loadGateways();
    await fetchStages(api.id);
    setShowModal(true);
  };

  const columnDefinitions = [
    {
      id: 'name',
      header: 'API Name',
      cell: item => item.name || 'N/A',
      sortingField: 'name'
    },
    {
      id: 'id',
      header: 'API ID',
      cell: item => item.id || 'N/A',
      sortingField: 'id'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <Button
          iconName="upload"
          variant="icon"
          onClick={() => handleOnboard(item)}
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
          REST APIs
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
          placeholder="Search REST APIs..."
          type="search"
        />

        <Table
          items={paginatedApis}
          columnDefinitions={columnDefinitions}
          loading={loading}
          loadingText="Loading REST APIs..."
          header={
            <Header 
              counter={`(${filteredApis.length})`}
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
              Available REST APIs
            </Header>
          }
          pagination={
            filteredApis.length > pageSize ? (
              <Pagination
                currentPageIndex={currentPageIndex}
                pagesCount={Math.ceil(filteredApis.length / pageSize)}
                onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
              />
            ) : null
          }
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center">
              <b>No REST APIs found</b>
            </Box>
          }
        />
      </SpaceBetween>
      
      <Modal
        visible={showModal}
        onDismiss={() => setShowModal(false)}
        header="REST API Documentation"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button 
                variant="primary"
                onClick={handleOnboardAPI}
                disabled={!toolName || !toolDescription || !selectedGateway || !selectedStage || onboarding || !documentation}
                loading={onboarding}
              >
                Onboard API
              </Button>
              <Button onClick={() => setShowModal(false)}>Close</Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween direction="vertical" size="m">
          <FormField label="API ID">
            <Input value={selectedApi?.id || ''} readOnly />
          </FormField>
          
          <FormField label="API Name">
            <Input value={selectedApi?.name || ''} readOnly />
          </FormField>
          
          <FormField label="Stage">
            <Select
              selectedOption={selectedStage}
              onChange={({ detail }) => {
                setSelectedStage(detail.selectedOption);
                if (detail.selectedOption) {
                  // Automatically call export API when stage is selected
                  handleExportAPI(detail.selectedOption);
                }
              }}
              options={stages}
              placeholder={stagesLoading ? "Loading stages..." : stages.length === 0 ? "No stages available" : "Select a stage"}
              loading={stagesLoading}
              disabled={stagesLoading}
              empty="No stages available"
            />
          </FormField>
          
          <FormField label="Tool Name">
            <Input
              value={toolName}
              onChange={({ detail }) => setToolName(detail.value)}
              placeholder="Enter tool name"
            />
          </FormField>
          
          <FormField label="Tool Description">
            <Textarea
              value={toolDescription}
              onChange={({ detail }) => setToolDescription(detail.value)}
              placeholder="Enter tool description"
              rows={3}
            />
          </FormField>
          
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
              empty="No gateways available"
            />
            {selectedGateway && (
              <Box margin={{ top: 'xs' }} color="text-status-info">
                <strong>Selected Gateway ID:</strong> {selectedGateway.value}
              </Box>
            )}
          </FormField>
          
          <FormField label="Documentation">
            <Textarea
              value={documentation}
              readOnly
              rows={15}
              placeholder={exportLoading ? "Loading documentation..." : "Documentation will appear here"}
              spellcheck={false}
              style={{
                fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace',
                fontSize: '13px',
                lineHeight: '1.4'
              }}
            />
          </FormField>
        </SpaceBetween>
      </Modal>
    </Container>
  );
};

export default OnboardRestAPI;