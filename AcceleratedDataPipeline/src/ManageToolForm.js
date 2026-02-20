import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Header,
  Table,
  Button,
  SpaceBetween,
  Box,
  TextFilter,
  Pagination,
  Alert,
  Select,
  FormField,
  Textarea,
  Input,
  Modal
} from '@cloudscape-design/components';
// Simple ResizeObserver error suppression
if (process.env.NODE_ENV === 'development') {
  const originalError = console.error;
  console.error = (...args) => {
    if (args[0]?.includes?.('ResizeObserver')) return;
    originalError(...args);
  };
}

const ManageToolForm = ({ onCancel, credentials }) => {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [filteringText, setFilteringText] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [sortingColumn, setSortingColumn] = useState({ sortingField: 'tool_name' });
  const [sortingDescending, setSortingDescending] = useState(false);
  const [deploymentOption, setDeploymentOption] = useState(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [finalPrompt, setFinalPrompt] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [isGeneratingCode, setIsGeneratingCode] = useState(false);
  const [codeGenerationError, setCodeGenerationError] = useState(null);
  const [showCodeModal, setShowCodeModal] = useState(false);
  const [isEditingCode, setIsEditingCode] = useState(false);
  const [editedCode, setEditedCode] = useState('');
  const [editingTool, setEditingTool] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [cloningTool, setCloningTool] = useState(null);
  const [cloneFormData, setCloneFormData] = useState({});
  const [deploymentResult, setDeploymentResult] = useState(null);
  const [saveToDefaultS3, setSaveToDefaultS3] = useState(true);
  const [isDeploying, setIsDeploying] = useState(false);

  const [agentName, setAgentName] = useState('');
  const [isEditingAgentName, setIsEditingAgentName] = useState(false);

  
  // Simple state update without debouncing
  const updateTools = (newTools) => {
    setTools(newTools);
  };

  const generateUUID = () => {
    return crypto.randomUUID();
  };

  const generateAgentName = () => {
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 12);
    const toolNames = selectedItems.map(tool => {
      const action = tool.aws_service_n_action || tool.tool_name || 'tool';
      // Extract service and action parts
      const parts = action.toLowerCase().split(/[\s_-]+/);
      // Take first 3 chars of each part, max 2 parts
      return parts.slice(0, 2).map(part => part.slice(0, 3)).join('');
    }).filter(Boolean).slice(0, 3);
    
    const toolsStr = toolNames.length > 0 ? toolNames.join('_') : 'def';
    return `mcp_${toolsStr}_${timestamp}`;
  };

  const deploymentOptions = [
    { label: 'MCP Server', value: 'mcp_server' },
    { label: 'Strands-Agent', value: 'strands_agent' }
  ];

  const mcpServerPrompt = `Create a Model Context Protocol Server code using FastMCP framework 2.0 https://gofastmcp.com/getting-started/welcome, for just the user provided mcp tools, don't make any changes to the user provided code, keep it as is, return just the code and no additional explanation is required, ensure the any variable by required by the user provided tool is received via body, also keep the @mcp.tool prefix as is, don't expand any annotations

Use the following reference code for MCP Server

# my_mcp_server.py

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b

@mcp.tool()
def greet_user(name: str) -> str:
    """Greet a user by name"""
    return f"Hello, {name}! Nice to meet you."

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

Make sure to include error handling and monitoring. Do not include \`\`\`python or \`\`\` in the response.`;

  const strandsAgentPrompt = `Create a Strands Agent using the framework from https://github.com/strands-agent. Incorporates the user-provided list of tools code as @tool. Don't change the user code, keep it as is, for each selected user function annotate as @tool

Example of Strand Agent custom tool is 
from strands import Agent, tool

# Create a custom tool 
@tool
def weather():
    """ Get weather """ # Dummy implementation
    return "sunny"

Only return the code don't return any additional verbiage, and Don't add code to involve the agents in this code. Do not include \`\`\`python or \`\`\` in the response.`;

  useEffect(() => {
    fetchTools();
  }, []);

  const parseDynamoDBItem = (item) => {
    const parsed = {};
    for (const [key, value] of Object.entries(item)) {
      if (value.S) parsed[key] = value.S;
      else if (value.N) parsed[key] = Number(value.N);
      else if (value.BOOL) parsed[key] = value.BOOL;
      else if (value.L) parsed[key] = value.L.map(listItem => listItem.S || listItem.N || listItem);
    }
    return parsed;
  };

  const fetchTools = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'list' })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        const parsedTools = data.items.map(item => parseDynamoDBItem(item));
        updateTools(parsedTools);
      } else {
        updateTools([]);
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
      setError(`Failed to load tools: ${error.message}`);
      updateTools([]);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (tool) => {
    setEditingTool(tool);
    setEditFormData({
      tool_name: tool.tool_name || '',
      language: tool.language || '',
      code: tool.code || '',
      blueprint_id: tool.blueprint_id || ''
    });
  };

  const handleSaveTool = async () => {
    try {
      const payload = {
        action: 'update',
        tool_id: editingTool.tool_id,
        system_type: editingTool.system_type,
        action_name: editingTool.action_name,
        aws_service_n_action: editingTool.aws_service_n_action,
        language: editingTool.language,
        code: editFormData.code,
        name: editFormData.tool_name
      };

      const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        setEditingTool(null);
        alert('Tool updated successfully!');
        fetchTools();
      } else {
        alert('Failed to update tool');
      }
    } catch (error) {
      console.error('Error updating tool:', error);
      alert('Error updating tool');
    }
  };

  const handleClone = (tool) => {
    const newToolId = generateUUID();
    
    setCloningTool({
      ...tool,
      tool_id: newToolId
    });
    
    const randomNumber = Math.floor(Math.random() * 10000);
    
    setCloneFormData({
      tool_name: `${tool.tool_name || 'Cloned Tool'} ${randomNumber}`,
      language: tool.language || '',
      code: tool.code || ''
    });
  };

  const handleDelete = async (tool) => {
    if (window.confirm(`Are you sure you want to delete "${tool.tool_name || 'this tool'}"?`)) {
      try {
        const payload = {
          action: 'delete',
          tool_id: tool.tool_id,
          aws_service_n_action: tool.aws_service_n_action
        };

        const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          alert('Tool deleted successfully!');
          fetchTools();
        } else {
          alert('Failed to delete tool');
        }
      } catch (error) {
        console.error('Error deleting tool:', error);
        alert('Error deleting tool');
      }
    }
  };

  const handleSaveClone = async () => {
    try {
      const payload = {
        action: 'create',
        tool_id: cloningTool.tool_id,
        system_type: cloningTool.system_type,
        action_name: cloningTool.action_name,
        aws_service_n_action: cloningTool.aws_service_n_action,
        language: cloningTool.language,
        code: cloneFormData.code,
        blueprint_id: cloningTool.blueprint_id,
        name: cloneFormData.tool_name
      };

      const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        setCloningTool(null);
        alert('Tool cloned successfully!');
        fetchTools();
      } else {
        alert('Failed to clone tool');
      }
    } catch (error) {
      console.error('Error cloning tool:', error);
      alert('Error cloning tool');
    }
  };

  const handleSelectionChange = ({ detail }) => {
    setSelectedItems(detail.selectedItems);
  };

  const columns = [
    {
      id: 'tool_name',
      header: 'Tool Name',
      cell: item => item.tool_name || 'N/A',
      sortingField: 'tool_name',
      isRowHeader: true
    },
    {
      id: 'aws_service_n_action',
      header: 'Action',
      cell: item => item.aws_service_n_action || 'N/A',
      sortingField: 'aws_service_n_action'
    },
    {
      id: 'code',
      header: 'Code',
      cell: item => {
        const code = item.code || '';
        return code.length > 100 ? `${code.substring(0, 100)}...` : code || 'N/A';
      },
      sortingField: 'code'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <div style={{ display: 'flex', gap: '4px' }}>
          <Button
            iconName="edit"
            variant="icon"
            onClick={() => handleEdit(item)}
            ariaLabel={`Edit ${item.tool_name || 'tool'}`}
          />
          <Button
            iconName="copy"
            variant="icon"
            onClick={() => handleClone(item)}
            ariaLabel={`Clone ${item.tool_name || 'tool'}`}
          />
          <Button
            iconName="remove"
            variant="icon"
            onClick={() => handleDelete(item)}
            ariaLabel={`Delete ${item.tool_name || 'tool'}`}
          />
        </div>
      )
    }
  ];

  const filteredItems = tools.filter(item => {
    const searchText = filteringText.toLowerCase();
    return (
      (item.tool_name || '').toLowerCase().includes(searchText) ||
      (item.aws_service_n_action || '').toLowerCase().includes(searchText) ||
      (item.code || '').toLowerCase().includes(searchText)
    );
  });

  const sortedItems = [...filteredItems].sort((a, b) => {
    const field = sortingColumn.sortingField;
    const aValue = a[field] || '';
    const bValue = b[field] || '';
    const result = aValue.toString().localeCompare(bValue.toString());
    return sortingDescending ? -result : result;
  });



  const pageSize = 10;
  const paginatedItems = sortedItems.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );





  const handleDeployCode = () => {
    if (deploymentOption?.value !== 'mcp_server') {
      alert('Deployment is only available for MCP Server framework type.');
      return;
    }

    const codeToDeploy = isEditingCode ? editedCode : generatedCode;
    
    if (!codeToDeploy.trim()) {
      alert('No code to deploy. Please generate code first.');
      return;
    }

    if (!credentials.username || !credentials.password) {
      alert('Please configure credentials first from the Profile menu.');
      return;
    }
    handleConfirmDeploy();
  };

  const handleConfirmDeploy = async () => {
    setIsDeploying(true);
    
    const codeToDeploy = isEditingCode ? editedCode : generatedCode;
    
    // Comment out HTTP endpoint - replaced with WebSocket
    /*
    try {
      const deploymentPayload = {
        mcp_server_code: codeToDeploy,
        requirements_txt: "mcp>=1.10.0\nboto3\nbedrock-agentcore\nbedrock-agentcore-starter-toolkit",
        username: credentials.username,
        password: credentials.password,
        agent_name: agentName
      };

      const response = await fetch('https://7kmgdphmr6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(deploymentPayload)
      });
    */
    
    // Use WebSocket for real-time deployment (same pattern as Generate Code)
    console.log('Initializing WebSocket connection for deployment...');
    const websocket = new WebSocket('wss://o8jf6ctc32.execute-api.us-east-1.amazonaws.com/dev/');
    
    websocket.onopen = () => {
      console.log('✅ DEPLOYMENT WebSocket connection established successfully!');
      console.log('🔗 Deployment WebSocket readyState:', websocket.readyState);
      console.log('🚀 Starting deployment process...');
      
      try {
        const message = {
          action: 'deploy',
          mcp_server_code: codeToDeploy,
          requirements_txt: "mcp>=1.10.0\nboto3\nbedrock-agentcore\nbedrock-agentcore-starter-toolkit",
          username: credentials.username,
          password: credentials.password,
          agent_name: agentName
        };
        
        console.log('📤 Sending deployment message:', message);
        websocket.send(JSON.stringify(message));
        console.log('✅ Deployment message sent successfully!');
      } catch (error) {
        console.error('❌ Error sending deployment message:', error);
        alert('Failed to send deployment request. Please try again.');
        setIsDeploying(false);
        websocket.close();
      }
    };
    
    websocket.onmessage = (event) => {
      console.log('📨 Deployment WebSocket message received:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('📋 Parsed deployment data:', data);
        
        // Handle different status updates
        if (data.status) {
          console.log(`🔄 Deployment Status: ${data.status} - ${data.message || 'No message'}`);
          
          if (data.status === 'COMPLETED') {
            console.log('✅ Deployment completed successfully!');
            console.log('🎯 Agent ARN:', data.agent_arn);
            console.log('🆔 Agent ID:', data.agent_id);
            
            // Save deployment result
            const deploymentInfo = {
              deployment_uuid: generateUUID(),
              agent_arn: data.agent_arn,
              agent_id: data.agent_id,
              status: data.final_status || 'COMPLETED',
              region: 'us-east-1',
              selected_tools: selectedItems.map(tool => ({
                tool_id: tool.tool_id,
                tool_name: tool.tool_name
              })),
              deployment_timestamp: new Date().toISOString()
            };
            
            setDeploymentResult(deploymentInfo);
            
            // Store deployment info in DynamoDB
            fetch('https://qbugcyn47d.execute-api.us-east-1.amazonaws.com/dev', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                action: 'store',
                deployment_info: deploymentInfo
              })
            }).catch(error => console.error('❌ Error storing deployment info:', error));
            
            if (window.confirm(`Deployment successful! Agent ARN: ${data.agent_arn}\n\nClick OK to continue.`)) {
              // Close modals and reload tools
              setShowCodeModal(false);

              setIsDeploying(false);
              setIsEditingCode(false);
              setEditedCode('');
              fetchTools();
            }
            websocket.close();
            
          } else if (data.status === 'FAILED' || data.status === 'ERROR') {
            console.log('❌ Deployment failed:', data.message || data.error);
            if (window.confirm(`Deployment failed: ${data.message || data.error}\n\nClick OK to continue.`)) {
              setIsDeploying(false);
            }
            websocket.close();
          }
        } else if (data.message === 'Forbidden') {
          console.log('❌ WebSocket connection forbidden');
          alert('WebSocket connection forbidden. Please check API Gateway configuration.');
          setIsDeploying(false);
          websocket.close();
        }
        
      } catch (error) {
        console.error('❌ Error parsing deployment WebSocket message:', error, 'Raw data:', event.data);
        // Try to handle as plain text
        if (typeof event.data === 'string') {
          console.log('📄 Treating as plain text:', event.data);
        }
      }
    };
    
    websocket.onerror = (error) => {
      console.error('❌ Deployment WebSocket error:', error);
      alert('Deployment WebSocket connection failed. Please try again.');
      setIsDeploying(false);
    };
    
    websocket.onclose = (event) => {
      console.log('🔌 Deployment WebSocket connection closed', event);
      setIsDeploying(false);
      // Only show error if we haven't completed deployment and it's not a normal close
      if (event.code !== 1000 && event.code !== 1001) {
        console.log('⚠️ Unexpected deployment WebSocket closure');
      }
    };
    
    // Add connection timeout (same as code generation)
    const connectionTimeout = setTimeout(() => {
      if (websocket.readyState === WebSocket.CONNECTING) {
        websocket.close();
        alert('Deployment connection timeout. Please try again.');
        setIsDeploying(false);
      }
    }, 10000); // 10 second timeout
    
    // Clear timeout when connection opens
    const originalOnOpen = websocket.onopen;
    websocket.onopen = (event) => {
      clearTimeout(connectionTimeout);
      if (originalOnOpen) originalOnOpen(event);
    };
  };

  const handleEditCode = () => {
    setEditedCode(generatedCode);
    setIsEditingCode(true);
  };

  const handleSaveCode = () => {
    setGeneratedCode(editedCode);
    setIsEditingCode(false);
    alert('Code saved successfully!');
  };

  const handleCancelEdit = () => {
    setIsEditingCode(false);
    setEditedCode('');
  };

  const buildFinalPrompt = () => {
    const toolsInfo = selectedItems.map(tool => 
      `Tool Name: ${tool.tool_name || 'N/A'}\nCode: ${tool.code || 'N/A'}`
    ).join('\n\n');
    
    return `${promptText}\n\nSelected Tools:\n${toolsInfo}`;
  };

  const handleGenerateCode = () => {
    const finalPromptText = buildFinalPrompt();
    setFinalPrompt(finalPromptText);
    setGeneratedCode('');
    setCodeGenerationError(null);
    setIsGeneratingCode(true);
    setShowCodeModal(true);
    setIsEditingCode(false);
    setEditedCode('');
    setAgentName(generateAgentName());
    setIsEditingAgentName(false);
    
    const websocket = new WebSocket('wss://kx2t8z3082.execute-api.us-east-1.amazonaws.com/dev/');
    
    websocket.onopen = () => {
      console.log('WebSocket connected for code generation');
      try {
        const selectedLanguages = [...new Set(selectedItems.map(tool => tool.language).filter(Boolean))];
        const message = {
          action: 'generate',
          language: selectedLanguages.length > 0 ? selectedLanguages[0] : 'python',
          prompt: finalPromptText
        };
        console.log('Sending WebSocket message:', message);
        websocket.send(JSON.stringify(message));
      } catch (error) {
        console.error('Error sending message:', error);
        setCodeGenerationError('Failed to send request. Please try again.');
        setIsGeneratingCode(false);
        websocket.close();
      }
    };
    
    websocket.onmessage = (event) => {
      console.log('WebSocket message received:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed WebSocket data:', data);
        
        // Handle different response formats
        if (data.type === 'content_block_delta' && data.delta?.text) {
          console.log('Content delta text:', data.delta.text);
          setGeneratedCode(prev => {
            const newCode = prev + data.delta.text;
            console.log('Updated generated code length:', newCode.length);
            return newCode;
          });
        } else if (data.type === 'message_delta' && data.delta?.stop_reason === 'end_turn') {
          console.log('Generation completed');
          setIsGeneratingCode(false);
          // Don't close websocket here, let it close naturally
        } else if (data.type === 'error') {
          console.log('WebSocket error received:', data);
          setCodeGenerationError(data.message || 'Unknown error occurred');
          setIsGeneratingCode(false);
          websocket.close();
        } else if (data.content) {
          // Handle direct content response
          console.log('Direct content received:', data.content);
          setGeneratedCode(prev => prev + data.content);
        } else if (data.text) {
          // Handle direct text response
          console.log('Direct text received:', data.text);
          setGeneratedCode(prev => prev + data.text);
        } else if (data.message) {
          // Handle message response
          console.log('Message received:', data.message);
          setGeneratedCode(prev => prev + data.message);
        } else {
          console.log('Unhandled message type or format:', data);
          // Try to append any string content
          if (typeof data === 'string') {
            setGeneratedCode(prev => prev + data);
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
        // Try to handle as plain text
        if (typeof event.data === 'string') {
          console.log('Treating as plain text:', event.data);
          setGeneratedCode(prev => prev + event.data);
        } else {
          setCodeGenerationError('Error parsing response');
          setIsGeneratingCode(false);
          websocket.close();
        }
      }
    };
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setCodeGenerationError('Connection failed. Please check your network and try again.');
      setIsGeneratingCode(false);
    };
    
    websocket.onclose = (event) => {
      console.log('WebSocket connection closed', event);
      setIsGeneratingCode(false);
      // Only show error if we haven't received any code and it's not a normal close
      if (event.code !== 1000 && event.code !== 1001 && !generatedCode) {
        setCodeGenerationError('Connection closed unexpectedly. Please try again.');
      }
    };
    
    // Add connection timeout
    const connectionTimeout = setTimeout(() => {
      if (websocket.readyState === WebSocket.CONNECTING) {
        websocket.close();
        setCodeGenerationError('Connection timeout. Please try again.');
        setIsGeneratingCode(false);
      }
    }, 10000); // 10 second timeout
    
    // Clear timeout when connection opens
    const originalOnOpen = websocket.onopen;
    websocket.onopen = (event) => {
      clearTimeout(connectionTimeout);
      if (originalOnOpen) originalOnOpen(event);
    };
  };

  // Show clone form if cloning a tool
  if (cloningTool) {
    return (
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <Button onClick={() => setCloningTool(null)}>
                Back
              </Button>
            }
          >
            Clone Tool: {cloningTool.tool_name || 'Unnamed Tool'}
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <FormField label="Tool ID">
            <Input
              value={cloningTool.tool_id}
              readOnly
            />
          </FormField>

          <FormField label="Blueprint ID">
            <Input
              value={cloningTool.blueprint_id}
              readOnly
            />
          </FormField>

          <FormField label="Action">
            <Input
              value={cloningTool.aws_service_n_action || 'N/A'}
              readOnly
            />
          </FormField>

          <FormField label="Tool Name">
            <Input
              value={cloneFormData.tool_name}
              onChange={({ detail }) => setCloneFormData(prev => ({ ...prev, tool_name: detail.value }))}
              data-lpignore="true"
              autoComplete="off"
            />
          </FormField>

          <FormField label="Language">
            <Input
              value={cloneFormData.language}
              readOnly
            />
          </FormField>

          <FormField label="Code">
            <Textarea
              value={cloneFormData.code}
              onChange={({ detail }) => setCloneFormData(prev => ({ ...prev, code: detail.value }))}
              rows={15}
              resize="vertical"
              data-lpignore="true"
              autoComplete="off"
            />
          </FormField>

          <SpaceBetween direction="horizontal" size="xs">
            <Button
              variant="primary"
              onClick={handleSaveClone}
            >
              Save Clone
            </Button>
            <Button onClick={() => setCloningTool(null)}>
              Cancel
            </Button>
          </SpaceBetween>
        </SpaceBetween>
      </Container>
    );
  }

  // Show edit form if editing a tool
  if (editingTool) {
    return (
      <Container
        header={
          <Header
            variant="h2"
            actions={
              <Button onClick={() => setEditingTool(null)}>
                Back
              </Button>
            }
          >
            Edit Tool: {editingTool.tool_name || 'Unnamed Tool'}
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <FormField label="Tool Name">
            <Input
              value={editFormData.tool_name}
              onChange={({ detail }) => setEditFormData(prev => ({ ...prev, tool_name: detail.value }))}
              data-lpignore="true"
              autoComplete="off"
            />
          </FormField>

          <FormField label="Action">
            <Input
              value={editingTool.aws_service_n_action || 'N/A'}
              readOnly
            />
          </FormField>

          <FormField label="Language">
            <Input
              value={editFormData.language}
              readOnly
            />
          </FormField>

          <FormField label="Blueprint ID">
            <Input
              value={editFormData.blueprint_id}
              readOnly
            />
          </FormField>

          <FormField label="Code">
            <Textarea
              value={editFormData.code}
              onChange={({ detail }) => setEditFormData(prev => ({ ...prev, code: detail.value }))}
              rows={15}
              resize="vertical"
              data-lpignore="true"
              autoComplete="off"
            />
          </FormField>

          <SpaceBetween direction="horizontal" size="xs">
            <Button
              variant="primary"
              onClick={handleSaveTool}
            >
              Save
            </Button>
            <Button onClick={() => setEditingTool(null)}>
              Cancel
            </Button>
          </SpaceBetween>
        </SpaceBetween>
      </Container>
    );
  }

  return (
    <Container
      header={
        <Header
          variant="h2"
          counter={`(${tools.length})`}
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={fetchTools} iconName="refresh">
                Refresh
              </Button>
              <Button onClick={onCancel}>
                Back
              </Button>
            </SpaceBetween>
          }
        >
          Manage Tools
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

        <Box margin={{ bottom: 'l' }} color="text-body-secondary">
          Select one or multiple tools from the table below to deploy as an MCP Server or Strands Agent. Choose your preferred framework type and generate the deployment code.
        </Box>

        {selectedItems.length > 0 && (
          <Container>
            <SpaceBetween direction="vertical" size="m">
              <Header variant="h3">
                Generate Code For: ({selectedItems.length})
              </Header>
              <FormField label="Framework Type">
                <Select
                  selectedOption={deploymentOption}
                  onChange={({ detail }) => {
                    setDeploymentOption(detail.selectedOption);
                    if (detail.selectedOption?.value === 'mcp_server') {
                      setPromptText(mcpServerPrompt);
                      setShowPrompt(true);
                      setIsEditingPrompt(false);
                      setSaveToDefaultS3(true);
                    } else if (detail.selectedOption?.value === 'strands_agent') {
                      setPromptText(strandsAgentPrompt);
                      setShowPrompt(true);
                      setIsEditingPrompt(false);
                      setSaveToDefaultS3(true);
                    } else {
                      setShowPrompt(false);
                    }
                  }}
                  options={deploymentOptions}
                  placeholder="Choose framework type..."
                />
              </FormField>

            </SpaceBetween>
          </Container>
        )}

        {selectedItems.length > 0 && showPrompt && (
          <Container>
            <SpaceBetween direction="vertical" size="m">
              <Header variant="h3">
                {deploymentOption?.value === 'mcp_server' ? 'MCP Server Generation Prompt' : 'Strands Agent Generation Prompt'}
              </Header>
              

              <FormField label="Prompt">
                <div style={{ position: 'relative' }}>
                  <Textarea
                    value={promptText || ''}
                    onChange={({ detail }) => setPromptText(detail.value)}
                    rows={5}
                    resize="vertical"
                    readOnly={!isEditingPrompt}
                    placeholder="Framework prompt will appear here..."
                  />
                  <div style={{ 
                    position: 'absolute', 
                    bottom: '8px', 
                    right: '8px', 
                    zIndex: 1
                  }}>
                    {!isEditingPrompt ? (
                      <Button
                        iconName="edit"
                        variant="icon"
                        onClick={() => setIsEditingPrompt(true)}
                        ariaLabel="Edit prompt"
                      />
                    ) : (
                      <Button
                        iconName="check"
                        variant="icon"
                        onClick={() => setIsEditingPrompt(false)}
                        ariaLabel="Save prompt"
                      />
                    )}
                  </div>
                </div>
              </FormField>
              
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="primary"
                  onClick={handleGenerateCode}
                  loading={isGeneratingCode}
                  iconName="gen-ai"
                >
                  Generate Code
                </Button>
              </SpaceBetween>
              
              {codeGenerationError && (
                <Alert
                  statusIconAriaLabel="Error"
                  type="error"
                  dismissible
                  onDismiss={() => setCodeGenerationError(null)}
                >
                  {codeGenerationError}
                </Alert>
              )}
              

            </SpaceBetween>
          </Container>
        )}

        <Table
          items={paginatedItems}
          columnDefinitions={columns}
          loading={loading}
          loadingText="Loading tools..."
          selectionType="multi"
          selectedItems={selectedItems}
          onSelectionChange={handleSelectionChange}
          sortingColumn={sortingColumn}
          sortingDescending={sortingDescending}
          onSortingChange={({ detail }) => {
            setSortingColumn(detail.sortingColumn);
            setSortingDescending(detail.isDescending);
          }}
          header={
            <Header counter={`(${tools.length})`}>
              Tools
            </Header>
          }
          filter={
            <TextFilter
              filteringText={filteringText}
              onChange={({ detail }) => {
                setFilteringText(detail.filteringText);
                setCurrentPageIndex(1);
              }}
              placeholder="Search tools..."
              filteringAriaLabel="Filter tools"
              data-lpignore="true"
            />
          }
          pagination={
            <Pagination
              currentPageIndex={currentPageIndex}
              pagesCount={Math.ceil(sortedItems.length / pageSize)}
              onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
              ariaLabels={{
                nextPageLabel: 'Next page',
                previousPageLabel: 'Previous page',
                pageLabel: pageNumber => `Page ${pageNumber} of all pages`
              }}
            />
          }
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center">
              <SpaceBetween size="m">
                <b>No tools found</b>
                <p>No tools match the current filter criteria.</p>
                <Button onClick={fetchTools} iconName="refresh">
                  Refresh
                </Button>
              </SpaceBetween>
            </Box>
          }
        />
        
        <Modal
          onDismiss={() => {
            setShowCodeModal(false);
            setIsEditingCode(false);
            setEditedCode('');
          }}
          visible={showCodeModal}
          size="max"
          header="Generated Code"
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                {!isGeneratingCode && (
                  <Button
                    variant="primary"
                    iconName="upload"
                    onClick={handleDeployCode}
                    loading={isDeploying}
                    disabled={deploymentOption?.value !== 'mcp_server'}
                  >
                    Deploy
                  </Button>
                )}

                <Button
                  onClick={() => {
                    setShowCodeModal(false);
                    setIsEditingCode(false);
                    setEditedCode('');
                  }}
                >
                  Close
                </Button>
              </SpaceBetween>
            </Box>
          }
        >
          <SpaceBetween direction="vertical" size="m">
            <FormField label="Agent Name">
              <div style={{ position: 'relative' }}>
                <Textarea
                  value={agentName}
                  onChange={({ detail }) => setAgentName(detail.value)}
                  readOnly={!isEditingAgentName}
                  rows={1}
                  resize="none"
                  placeholder="Agent name will be generated..."
                />
                <div style={{ 
                  position: 'absolute', 
                  bottom: '8px', 
                  right: '8px', 
                  zIndex: 1
                }}>
                  {!isEditingAgentName ? (
                    <Button
                      iconName="edit"
                      variant="icon"
                      onClick={() => setIsEditingAgentName(true)}
                      ariaLabel="Edit agent name"
                    />
                  ) : (
                    <Button
                      iconName="check"
                      variant="icon"
                      onClick={() => setIsEditingAgentName(false)}
                      ariaLabel="Save agent name"
                    />
                  )}
                </div>
              </div>
            </FormField>
            
            <FormField label="Generated Code">
              <div style={{ position: 'relative' }}>
                {!isGeneratingCode && (
                  <div style={{ 
                    position: 'absolute', 
                    top: '8px', 
                    right: '8px', 
                    zIndex: 1,
                    display: 'flex',
                    gap: '4px'
                  }}>
                    {codeGenerationError && (
                      <Button
                        iconName="refresh"
                        variant="icon"
                        onClick={handleGenerateCode}
                        ariaLabel="Retry code generation"
                      />
                    )}
                    {!isEditingCode ? (
                      <Button
                        iconName="edit"
                        variant="icon"
                        onClick={handleEditCode}
                        ariaLabel="Edit code"
                      />
                    ) : (
                      <>
                        <Button
                          iconName="check"
                          variant="icon"
                          onClick={handleSaveCode}
                          ariaLabel="Save code"
                        />
                        <Button
                          iconName="close"
                          variant="icon"
                          onClick={handleCancelEdit}
                          ariaLabel="Cancel edit"
                        />
                      </>
                    )}
                  </div>
                )}
                <Textarea
                  value={isEditingCode ? editedCode : generatedCode}
                  onChange={isEditingCode ? ({ detail }) => setEditedCode(detail.value) : undefined}
                  readOnly={!isEditingCode}
                  rows={25}
                  resize="vertical"
                  placeholder="Generated code will appear here..."
                  data-lpignore="true"
                  autoComplete="off"
                  style={{
                    fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "Courier New", monospace',
                    fontSize: '14px',
                    lineHeight: '1.4',
                    tabSize: 2,
                    paddingTop: '40px'
                  }}
                />
              </div>
            </FormField>
          </SpaceBetween>
        </Modal>
        

      </SpaceBetween>
    </Container>
  );
};

export default ManageToolForm;