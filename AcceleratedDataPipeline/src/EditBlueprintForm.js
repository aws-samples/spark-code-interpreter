import React, { useState, useEffect, useRef } from 'react';
import { 
  Container, 
  Header, 
  Table,
  Button,
  FormField,
  Textarea,
  Select,
  SpaceBetween,
  Box,
  TextFilter,
  Pagination,
  Toggle,
  ProgressBar
} from '@cloudscape-design/components';
import ManageBlueprintItemForm from './ManageBlueprintItemForm';

const EditBlueprintForm = ({ onCancel, selectedBlueprint }) => {
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [currentBlueprint, setCurrentBlueprint] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState(null);
  const [generateIndividual, setGenerateIndividual] = useState(true);
  const [isEditingPrompt, setIsEditingPrompt] = useState(false);
  const [actionPrompts, setActionPrompts] = useState([]);
  const actionPromptsRef = useRef([]);
  const [ws, setWs] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedCode, setGeneratedCode] = useState('');
  const [generationStatus, setGenerationStatus] = useState('idle');
  const [actionCodeResults, setActionCodeResults] = useState({});
  const [currentGeneratingAction, setCurrentGeneratingAction] = useState(null);
  const [currentActionIndex, setCurrentActionIndex] = useState(0);
  const [filteringText, setFilteringText] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [sortingColumn, setSortingColumn] = useState({ sortingField: 'name' });
  const [sortingDescending, setSortingDescending] = useState(false);
  const [toolId, setToolId] = useState(null);
  const [actionToolIds, setActionToolIds] = useState({});

  const generateUUID = () => {
    return crypto.randomUUID();
  };

  // WebSocket debugging and testing function
  const testWebSocketConnection = () => {
    console.log('🔍 Testing WebSocket connection...');
    
    const testWs = new WebSocket('wss://1bqwfi0qpa.execute-api.us-east-1.amazonaws.com/dev/');
    
    const connectionStart = Date.now();
    
    testWs.onopen = () => {
      const connectionTime = Date.now() - connectionStart;
      console.log(`✅ WebSocket test connection successful in ${connectionTime}ms`);
      console.log('Connection details:', {
        readyState: testWs.readyState,
        protocol: testWs.protocol,
        url: testWs.url,
        extensions: testWs.extensions
      });
      
      // Test sending a message
      try {
        const testMessage = {
          action: 'ping',
          timestamp: Date.now()
        };
        testWs.send(JSON.stringify(testMessage));
        console.log('📤 Test message sent successfully');
      } catch (error) {
        console.error('❌ Error sending test message:', error);
      }
      
      // Close test connection after 2 seconds
      setTimeout(() => {
        testWs.close();
        console.log('🔒 Test connection closed');
      }, 2000);
    };
    
    testWs.onerror = (error) => {
      const connectionTime = Date.now() - connectionStart;
      console.error(`❌ WebSocket test connection failed after ${connectionTime}ms:`, error);
      console.error('Error details:', {
        type: error.type,
        target: error.target,
        timeStamp: error.timeStamp
      });
      
      // Check common issues
      console.log('🔍 Debugging checklist:');
      console.log('1. Network connectivity:', navigator.onLine ? '✅ Online' : '❌ Offline');
      console.log('2. HTTPS context:', window.location.protocol === 'https:' ? '✅ HTTPS' : '⚠️ HTTP');
      console.log('3. WebSocket support:', 'WebSocket' in window ? '✅ Supported' : '❌ Not supported');
      console.log('4. URL format:', testWs.url);
    };
    
    testWs.onclose = (event) => {
      const connectionTime = Date.now() - connectionStart;
      console.log(`🔒 WebSocket test connection closed after ${connectionTime}ms:`, {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      
      // Interpret close codes
      const closeCodes = {
        1000: 'Normal closure',
        1001: 'Going away',
        1002: 'Protocol error',
        1003: 'Unsupported data',
        1006: 'Abnormal closure (no close frame)',
        1011: 'Server error',
        1012: 'Service restart',
        1013: 'Try again later',
        1014: 'Bad gateway',
        1015: 'TLS handshake failure'
      };
      
      console.log(`Close code meaning: ${closeCodes[event.code] || 'Unknown code'}`);
    };
    
    testWs.onmessage = (event) => {
      console.log('📥 Test message received:', event.data);
    };
    
    // Connection timeout for test
    setTimeout(() => {
      if (testWs.readyState === WebSocket.CONNECTING) {
        console.error('❌ Test connection timeout after 5 seconds');
        testWs.close();
      }
    }, 5000);
  };

  // Auto-generate language options from common programming languages
  const languageOptions = [
    'python', 'javascript', 'typescript', 'java', 'csharp', 'go', 'rust', 'php'
  ].map(lang => ({
    label: lang.charAt(0).toUpperCase() + lang.slice(1),
    value: lang
  }));

  const parseDynamoDBItem = (item) => {
    const parsed = {};
    for (const [key, value] of Object.entries(item)) {
      if (value.S) parsed[key] = value.S;
      else if (value.L) parsed[key] = value.L.map(listItem => listItem.S);
      else if (value.N) parsed[key] = Number(value.N);
      else if (value.BOOL) parsed[key] = value.BOOL;
    }
    return parsed;
  };

  const fetchBlueprints = async () => {
    try {
      const response = await fetch('https://77a9252l49.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'list' })
      });

      if (response.ok) {
        const data = await response.json();
        const parsedItems = (data.items || []).map(item => parseDynamoDBItem(item));
        setBlueprints(parsedItems);
      }
    } catch (error) {
      console.error('Error fetching blueprints:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBlueprints();
  }, []);



  const processNextAction = (actionIndex) => {
    const prompts = actionPromptsRef.current;
    
    if (actionIndex >= prompts.length) {
      setIsGenerating(false);
      setGenerationStatus('completed');
      setCurrentGeneratingAction(null);
      setCurrentActionIndex(0);
      console.log('All actions completed successfully');
      return;
    }
    
    const actionItem = prompts[actionIndex];
    console.log(`Processing ${actionIndex + 1}/${prompts.length}: ${actionItem.action}`);
    
    setCurrentActionIndex(actionIndex);
    setCurrentGeneratingAction(actionItem.action);
    setActionCodeResults(prev => ({
      ...prev,
      [actionItem.action]: { code: '', status: 'generating' }
    }));
    
    // Create WebSocket with improved connection handling
    const websocket = new WebSocket('wss://1bqwfi0qpa.execute-api.us-east-1.amazonaws.com/dev/');
    let isConnectionSuccessful = false;
    let messageReceived = false;
    
    // Connection timeout with better error handling
    const connectionTimeout = setTimeout(() => {
      if (!isConnectionSuccessful) {
        console.error(`WebSocket connection timeout for ${actionItem.action}`);
        websocket.close();
        setActionCodeResults(prev => ({
          ...prev,
          [actionItem.action]: { 
            code: `Connection timeout after 10 seconds for ${actionItem.action}`, 
            status: 'error' 
          }
        }));
        // Continue to next action after timeout
        setTimeout(() => processNextAction(actionIndex + 1), 1000);
      }
    }, 10000);
    
    // Message timeout - if no response after connection
    let messageTimeout;
    
    websocket.onopen = () => {
      isConnectionSuccessful = true;
      clearTimeout(connectionTimeout);
      console.log(`✅ WebSocket connected for ${actionItem.action}`);
      
      try {
        const message = {
          action: 'generate_mcp_tool',
          prompt: actionItem.prompt || '',
          language: selectedLanguage?.value || 'python'
        };
        
        console.log(`📤 Sending message for ${actionItem.action}:`, message);
        websocket.send(JSON.stringify(message));
        
        // Set message timeout after sending
        messageTimeout = setTimeout(() => {
          if (!messageReceived) {
            console.error(`No response received for ${actionItem.action} after 30 seconds`);
            websocket.close();
            setActionCodeResults(prev => ({
              ...prev,
              [actionItem.action]: { 
                code: `No response received for ${actionItem.action}`, 
                status: 'error' 
              }
            }));
            setTimeout(() => processNextAction(actionIndex + 1), 1000);
          }
        }, 30000);
        
      } catch (error) {
        console.error(`Error sending message for ${actionItem.action}:`, error);
        setActionCodeResults(prev => ({
          ...prev,
          [actionItem.action]: { 
            code: `Error sending request: ${error.message}`, 
            status: 'error' 
          }
        }));
        websocket.close();
        setTimeout(() => processNextAction(actionIndex + 1), 1000);
      }
    };
    
    websocket.onmessage = (event) => {
      messageReceived = true;
      clearTimeout(messageTimeout);
      
      try {
        const data = JSON.parse(event.data);
        console.log(`📥 Message received for ${actionItem.action}:`, data.type);
        
        if (data.type === 'content_block_delta' && data.delta?.text) {
          setActionCodeResults(prev => ({
            ...prev,
            [actionItem.action]: {
              ...prev[actionItem.action],
              code: (prev[actionItem.action]?.code || '') + data.delta.text,
              status: 'generating'
            }
          }));
        } else if (data.type === 'message_delta' && data.delta?.stop_reason === 'end_turn') {
          console.log(`✅ Generation completed for ${actionItem.action}`);
          setActionCodeResults(prev => ({
            ...prev,
            [actionItem.action]: {
              ...prev[actionItem.action],
              status: 'completed'
            }
          }));
          websocket.close();
          // Add small delay before processing next action
          setTimeout(() => processNextAction(actionIndex + 1), 500);
        } else if (data.type === 'error') {
          console.error(`API error for ${actionItem.action}:`, data);
          setActionCodeResults(prev => ({
            ...prev,
            [actionItem.action]: { 
              code: `API Error: ${data.message || 'Unknown error'}`, 
              status: 'error' 
            }
          }));
          websocket.close();
          setTimeout(() => processNextAction(actionIndex + 1), 1000);
        }
      } catch (parseError) {
        console.error(`Error parsing message for ${actionItem.action}:`, parseError);
        setActionCodeResults(prev => ({
          ...prev,
          [actionItem.action]: { 
            code: `Error parsing response: ${parseError.message}`, 
            status: 'error' 
          }
        }));
      }
    };
    
    websocket.onerror = (error) => {
      clearTimeout(connectionTimeout);
      clearTimeout(messageTimeout);
      
      console.error(`❌ WebSocket error for ${actionItem.action}:`, {
        error: error,
        type: error.type,
        target: error.target,
        timeStamp: error.timeStamp,
        readyState: websocket.readyState,
        url: websocket.url
      });
      
      // Detailed error analysis
      let errorMessage = `WebSocket connection failed for ${actionItem.action}`;
      
      if (!navigator.onLine) {
        errorMessage += ' - No internet connection';
      } else if (websocket.readyState === WebSocket.CONNECTING) {
        errorMessage += ' - Connection timeout';
      } else if (websocket.readyState === WebSocket.CLOSING) {
        errorMessage += ' - Connection closing';
      } else if (websocket.readyState === WebSocket.CLOSED) {
        errorMessage += ' - Connection closed';
      }
      
      console.log('🔍 Connection diagnostics:', {
        online: navigator.onLine,
        protocol: window.location.protocol,
        wsSupport: 'WebSocket' in window,
        readyState: websocket.readyState,
        wsUrl: websocket.url
      });
      
      setActionCodeResults(prev => ({
        ...prev,
        [actionItem.action]: { 
          code: errorMessage, 
          status: 'error' 
        }
      }));
      // Continue to next action after error
      setTimeout(() => processNextAction(actionIndex + 1), 1000);
    };
    
    websocket.onclose = (event) => {
      clearTimeout(connectionTimeout);
      clearTimeout(messageTimeout);
      
      if (event.code !== 1000 && event.code !== 1001) {
        console.error(`❌ WebSocket closed unexpectedly for ${actionItem.action}:`, {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        
        // Only update status if not already completed or error
        setActionCodeResults(prev => {
          const currentStatus = prev[actionItem.action]?.status;
          if (currentStatus !== 'completed' && currentStatus !== 'error') {
            return {
              ...prev,
              [actionItem.action]: { 
                code: `Connection closed unexpectedly (Code: ${event.code})`, 
                status: 'error' 
              }
            };
          }
          return prev;
        });
      } else {
        console.log(`✅ WebSocket closed cleanly for ${actionItem.action}`);
      }
    };
  };

  const handleEdit = (blueprint) => {
    setEditingItem(blueprint);
    setEditModalVisible(true);
  };

  const handleDelete = async (blueprint) => {
    if (window.confirm(`Are you sure you want to delete "${blueprint.name}"?`)) {
      try {
        const payload = {
          action: 'delete',
          key: blueprint.tool_id,
          service_type: blueprint.service_type
        };

        const response = await fetch('https://77a9252l49.execute-api.us-east-1.amazonaws.com/dev', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (response.ok) {
          alert('Blueprint deleted successfully!');
          fetchBlueprints();
        } else {
          alert('Failed to delete blueprint');
        }
      } catch (error) {
        console.error('Error deleting blueprint:', error);
        alert('Error deleting blueprint');
      }
    }
  };

  const handleSaveItem = () => {
    setEditModalVisible(false);
    setEditingItem(null);
    fetchBlueprints();
  };

  // If selectedBlueprint is passed, show it directly
  useEffect(() => {
    if (selectedBlueprint) {
      setCurrentBlueprint(selectedBlueprint);
      setPrompt(selectedBlueprint.prompt || '');
      setSelectedLanguage({ label: 'Python', value: 'python' });
    }
  }, [selectedBlueprint]);

  // Generate action prompts when blueprint changes
  useEffect(() => {
    if (currentBlueprint && prompt) {
      generateActionPrompts(currentBlueprint);
    }
  }, [currentBlueprint, prompt, generateIndividual]);

  const generateActionPrompts = (blueprint) => {
    if (blueprint.actions && blueprint.actions.length > 0) {
      let basePrompt = prompt;
      
      // Only add DynamoDB suffix for DynamoDB service types
      if (blueprint.service_type?.toLowerCase().includes('dynamodb')) {
        basePrompt = generateIndividual 
          ? `${prompt} - each function must include dynamodb = boto3.client('dynamodb')`
          : `${prompt} - include dynamodb = boto3.client('dynamodb') at the top`;
      }
      
      const prompts = blueprint.actions.map(action => {
        const actionLabel = getActionLabel(action);
        return {
          action: action,
          prompt: `${basePrompt} - Generate code specifically for ${actionLabel} action`
        };
      });

      setActionPrompts(prompts);
      actionPromptsRef.current = prompts;
    }
  };

  const getActionLabel = (action) => {
    // Automatically format action names: 'create' -> 'Create', 'read_all' -> 'Read All'
    return action
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };



  const handleGenerateCode = () => {
    // Always start fresh generation without checking existing WebSocket state
    console.log('Starting code generation');
    startCodeGeneration();
  };

  const startCodeGeneration = () => {
    console.log('🚀 Starting code generation process');
    
    // Reset all generation states
    setIsGenerating(true);
    setGenerationStatus('generating');
    setCurrentActionIndex(0);
    setCurrentGeneratingAction(null);

    if (generateIndividual) {
      // Use current actionPrompts state, not ref
      const currentPrompts = actionPrompts;
      
      if (!currentPrompts || currentPrompts.length === 0) {
        console.error('No action prompts available for generation');
        setIsGenerating(false);
        setGenerationStatus('error');
        alert('No actions available for code generation. Please check your blueprint configuration.');
        return;
      }
      
      // Update ref to ensure processNextAction has latest data
      actionPromptsRef.current = currentPrompts;
      
      console.log(`📋 Starting generation for ${currentPrompts.length} actions:`);
      console.log('Actions to process:', currentPrompts.map(p => p.action));
      
      // Generate UUID for each action
      const actionIds = {};
      currentPrompts.forEach(item => {
        actionIds[item.action] = generateUUID();
      });
      setActionToolIds(actionIds);
      
      // Initialize action results with proper status tracking
      const initialResults = {};
      currentPrompts.forEach(item => {
        initialResults[item.action] = { 
          code: '', 
          status: 'pending',
          startTime: null,
          endTime: null
        };
      });
      setActionCodeResults(initialResults);
      
      console.log('🔄 Initialized action results, starting sequential processing...');
      
      // Start processing with a small delay to ensure state is set
      setTimeout(() => {
        console.log('⏱️ Starting first action processing');
        processNextAction(0);
      }, 200);
      
    } else {
      // Handle single code generation with improved error handling
      console.log('📝 Starting single code generation');
      
      const singleToolId = generateUUID();
      setToolId(singleToolId);
      setGeneratedCode('');
      
      // Create WebSocket for single generation
      const websocket = new WebSocket('wss://1bqwfi0qpa.execute-api.us-east-1.amazonaws.com/dev/');
      let connectionTimeout;
      
      connectionTimeout = setTimeout(() => {
        console.error('Single generation connection timeout');
        websocket.close();
        setGenerationStatus('error');
        setIsGenerating(false);
        alert('Connection timeout. Please try again.');
      }, 10000);
      
      websocket.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('✅ Single generation WebSocket connected');
        
        let finalPrompt = prompt || '';
        
        // Only add DynamoDB suffix for DynamoDB service types
        if (currentBlueprint?.service_type?.toLowerCase().includes('dynamodb')) {
          finalPrompt = `${prompt || ''} - include dynamodb = boto3.client('dynamodb') at the top`;
        }
        
        const message = {
          action: 'generate_mcp_tool',
          prompt: finalPrompt,
          language: selectedLanguage?.value || 'python'
        };
        console.log('📤 Single generation message:', message);
        websocket.send(JSON.stringify(message));
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'content_block_delta' && data.delta?.text) {
            setGeneratedCode(prev => prev + data.delta.text);
          } else if (data.type === 'message_delta' && data.delta?.stop_reason === 'end_turn') {
            console.log('✅ Single generation completed');
            setGenerationStatus('completed');
            setIsGenerating(false);
            websocket.close();
          } else if (data.type === 'error') {
            console.error('Single generation API error:', data);
            setGenerationStatus('error');
            setIsGenerating(false);
            websocket.close();
          }
        } catch (error) {
          console.error('Error parsing single generation response:', error);
          setGenerationStatus('error');
          setIsGenerating(false);
        }
      };
      
      websocket.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('Single generation WebSocket error:', error);
        setGenerationStatus('error');
        setIsGenerating(false);
      };
      
      websocket.onclose = (event) => {
        clearTimeout(connectionTimeout);
        if (event.code !== 1000 && event.code !== 1001) {
          console.error('Single generation WebSocket closed unexpectedly:', event);
          setGenerationStatus('error');
          setIsGenerating(false);
        }
      };
    }
  };





  const retryAction = (action) => {
    const actionIndex = actionPromptsRef.current.findIndex(item => item.action === action);
    if (actionIndex !== -1) {
      console.log(`Retrying action: ${action}`);
      
      // Reset WebSocket connection if exists
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        setWs(null);
      }
      
      setActionCodeResults(prev => ({
        ...prev,
        [action]: {
          code: '',
          status: 'generating'
        }
      }));
      
      const retryActionItem = actionPromptsRef.current[actionIndex];
      setCurrentGeneratingAction(retryActionItem.action);
      
      // Create fresh WebSocket connection
      const websocket = new WebSocket('wss://1bqwfi0qpa.execute-api.us-east-1.amazonaws.com/dev/');
      let hasResponse = false;
      
      const timeout = setTimeout(() => {
        if (!hasResponse) {
          websocket.close();
          setActionCodeResults(prev => ({
            ...prev,
            [action]: {
              ...prev[action],
              status: 'error',
              code: 'Timeout - no response'
            }
          }));
          setCurrentGeneratingAction(null);
        }
      }, 5000);
      
      websocket.onopen = () => {
        console.log(`Fresh WebSocket connection established for retry: ${action}`);
        const message = {
          action: 'generate_mcp_tool',
          prompt: retryActionItem.prompt || '',
          language: selectedLanguage?.value || 'python'
        };
        console.log('Retry message:', message);
        websocket.send(JSON.stringify(message));
      };
      
      websocket.onmessage = (event) => {
        hasResponse = true;
        clearTimeout(timeout);
        
        const data = JSON.parse(event.data);
        
        if (data.type === 'content_block_delta' && data.delta?.text) {
          setActionCodeResults(prev => ({
            ...prev,
            [action]: {
              ...prev[action],
              code: (prev[action]?.code || '') + data.delta.text,
              status: 'generating'
            }
          }));
        } else if (data.type === 'message_delta' && data.delta?.stop_reason === 'end_turn') {
          setActionCodeResults(prev => ({
            ...prev,
            [action]: {
              ...prev[action],
              status: 'completed'
            }
          }));
          
          websocket.close();
          setCurrentGeneratingAction(null);
          console.log(`Retry completed for action: ${action}`);
        }
      };
      
      websocket.onclose = () => {
        console.log(`WebSocket closed for retry: ${action}`);
      };
      
      websocket.onerror = () => {
        console.log(`WebSocket error for retry: ${action}`);
        clearTimeout(timeout);
        setActionCodeResults(prev => ({
          ...prev,
          [action]: {
            ...prev[action],
            status: 'error',
            code: 'Error generating code'
          }
        }));
        setCurrentGeneratingAction(null);
      };
    }
  };

  const saveCodeToAPI = async (toolUuid, actionName, code) => {
    const payload = {
      action: 'create',
      tool_id: toolUuid,
      system_type: currentBlueprint.service_type,
      action_name: actionName,
      language: selectedLanguage.value,
      code: code,
      blueprint_id: currentBlueprint.tool_id,
      name: `${currentBlueprint.name} For ${getActionLabel(actionName)} Tool`
    };

    try {
      const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        console.log(`Saved ${actionName} code successfully`);
        return true;
      } else {
        console.error(`Failed to save ${actionName} code`);
        return false;
      }
    } catch (error) {
      console.error(`Error saving ${actionName} code:`, error);
      return false;
    }
  };

  const handleSaveCode = async () => {
    if (generateIndividual) {
      // Toggle ON: Save each action separately
      const savePromises = Object.entries(actionCodeResults)
        .filter(([action, result]) => result.status === 'completed' && result.code)
        .map(([action, result]) => {
          const toolUuid = actionToolIds[action];
          return saveCodeToAPI(toolUuid, action, result.code);
        });

      const results = await Promise.all(savePromises);
      const successCount = results.filter(Boolean).length;
      alert(`Saved ${successCount} of ${results.length} actions successfully!`);
    } else {
      // Toggle OFF: Save single combined code
      if (generatedCode && toolId) {
        const success = await saveCodeToAPI(toolId, 'combined', generatedCode);
        alert(success ? 'Code saved successfully!' : 'Failed to save code');
      }
    }
  };

  const getProgressPercentage = () => {
    if (actionPrompts.length === 0) return 0;
    const completedCount = getCompletedActionsCount();
    return Math.round((completedCount / actionPrompts.length) * 100);
  };

  const getCompletedActionsCount = () => {
    return Object.values(actionCodeResults).filter(result => result.status === 'completed').length;
  };

  const getProgressLabel = () => {
    if (currentGeneratingAction) {
      return `Generating ${getActionLabel(currentGeneratingAction)}...`;
    }
    return 'Generating code...';
  };

  const getProgressDescription = () => {
    const completedCount = getCompletedActionsCount();
    const totalCount = actionPrompts.length;
    
    if (completedCount === totalCount) {
      return 'All actions completed successfully';
    } else if (currentGeneratingAction) {
      const actionResult = actionCodeResults[currentGeneratingAction];
      if (actionResult?.code?.includes('Optimizing response')) {
        return `Optimizing ${getActionLabel(currentGeneratingAction)} response...`;
      }
      return `Generating ${getActionLabel(currentGeneratingAction)} code...`;
    }
    return `Processing ${totalCount} actions...`;
  };

  const handleToggleChange = (checked) => {
    setGenerateIndividual(checked);
    if (checked && currentBlueprint) {
      generateActionPrompts(currentBlueprint);
    }
    console.log(`Toggle ${checked ? 'enabled' : 'disabled'} - ${actionPrompts.length} actions available`);
  };



  // Update prompt display based on toggle state
  const getDisplayPrompt = () => {
    if (!prompt) return '';
    
    // Only add DynamoDB instruction for DynamoDB service types
    if (currentBlueprint?.service_type?.toLowerCase().includes('dynamodb')) {
      const instruction = generateIndividual 
        ? ' - each function must include dynamodb = boto3.client(\'dynamodb\')'
        : ' - include dynamodb = boto3.client(\'dynamodb\') at the top';
      return prompt + instruction;
    }
    
    return prompt;
  };

  const columns = [
    {
      id: 'name',
      header: 'Blueprint Name',
      cell: item => <strong>{item.name}</strong>,
      sortingField: 'name',
      isRowHeader: true
    },
    {
      id: 'description',
      header: 'Description',
      cell: item => item.description,
      sortingField: 'description'
    },
    {
      id: 'category',
      header: 'Category',
      cell: item => item.category,
      sortingField: 'category'
    },
    {
      id: 'service_type',
      header: 'Service Type',
      cell: item => item.service_type,
      sortingField: 'service_type'
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
            ariaLabel="Edit"
          />
          <Button
            iconName="remove"
            variant="icon"
            onClick={() => handleDelete(item)}
            ariaLabel="Delete"
          />
        </div>
      )
    }
  ];

  const filteredItems = blueprints.filter(item =>
    item.name?.toLowerCase().includes(filteringText.toLowerCase()) ||
    item.description?.toLowerCase().includes(filteringText.toLowerCase()) ||
    item.service_type?.toLowerCase().includes(filteringText.toLowerCase())
  );

  const sortedItems = [...filteredItems].sort((a, b) => {
    const field = sortingColumn.sortingField;
    const result = (a[field] || '').localeCompare(b[field] || '');
    return sortingDescending ? -result : result;
  });

  // Auto-calculate page size based on screen height or use dynamic sizing
  const pageSize = Math.max(5, Math.floor(window.innerHeight / 80) || 10);
  const paginatedItems = sortedItems.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  // If selectedBlueprint is passed, show form directly
  if (selectedBlueprint) {
    return (
      <Container 
        header={
          <Header variant="h2" actions={<Button onClick={onCancel}>Back</Button>}>
            Generate MCP Tool Code
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <FormField label="Selected Blueprint">
            <Box>
              <strong>{currentBlueprint?.name}</strong> - {currentBlueprint?.description}
            </Box>
          </FormField>

          <FormField label="Language">
            <Select
              selectedOption={selectedLanguage}
              onChange={({ detail }) => setSelectedLanguage(detail.selectedOption)}
              options={languageOptions}
            />
          </FormField>

          <FormField label="Code Generation">
            <Toggle
              onChange={({ detail }) => handleToggleChange(detail.checked)}
              checked={generateIndividual}
            >
              Generate code for each action individually
            </Toggle>
          </FormField>



          <FormField label="Prompt">
            <div style={{ position: 'relative' }}>
              <Textarea
                value={isEditingPrompt ? prompt : getDisplayPrompt()}
                onChange={({ detail }) => setPrompt(detail.value)}
                rows={8}
                resize="vertical"
                readOnly={!isEditingPrompt}
                style={{ paddingRight: '80px' }}
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
              loading={isGenerating}
              disabled={!selectedLanguage}
            >
              Generate Code
            </Button>
            {generationStatus === 'completed' && (
              <Button 
                onClick={handleSaveCode}
              >
                Save
              </Button>
            )}
          </SpaceBetween>

          {generateIndividual && isGenerating && (
            <FormField label="Generation Progress">
              <SpaceBetween direction="vertical" size="xs">
                <ProgressBar
                  value={getProgressPercentage()}
                  label={getProgressLabel()}
                  description={getProgressDescription()}
                />
                <Box fontSize="body-s" color="text-status-info">
                  {getCompletedActionsCount()} of {actionPrompts.length} actions completed
                </Box>
              </SpaceBetween>
            </FormField>
          )}

          {generateIndividual ? (
            Object.entries(actionCodeResults)
              .filter(([action, result]) => result.status !== 'pending')
              .map(([action, result]) => (
                <FormField key={action} label={`Generated Code for ${getActionLabel(action)} Action`}>
                  <div style={{ position: 'relative' }}>
                    <Textarea
                      value={result.code}
                      readOnly
                      rows={15}
                      resize="vertical"
                      placeholder={result.status === 'generating' ? 'Generating code...' : 'Generated code will appear here'}
                    />
                    {result.status === 'error' && (
                      <div style={{ 
                        position: 'absolute', 
                        top: '8px', 
                        right: '8px', 
                        zIndex: 1
                      }}>
                        <Button
                          variant="icon"
                          onClick={() => retryAction(action)}
                          iconName="refresh"
                          ariaLabel="Retry"
                        />
                      </div>
                    )}
                  </div>
                </FormField>
              ))
          ) : (
            generatedCode && (
              <FormField label="Generated Code">
                <Textarea
                  value={generatedCode}
                  readOnly
                  rows={20}
                  resize="vertical"
                />
              </FormField>
            )
          )}
        </SpaceBetween>
      </Container>
    );
  }

  return (
    <>
      <Container 
        header={
          <Header variant="h2" counter={`(${blueprints.length})`} actions={<Button onClick={onCancel}>Back</Button>}>
            Edit Blueprints
          </Header>
        }
      >
        <Table
          items={paginatedItems}
          columnDefinitions={columns}
          loading={loading}
          loadingText="Loading blueprints..."
          sortingColumn={sortingColumn}
          sortingDescending={sortingDescending}
          onSortingChange={({ detail }) => {
            setSortingColumn(detail.sortingColumn);
            setSortingDescending(detail.isDescending);
          }}
          filter={
            <TextFilter
              filteringText={filteringText}
              onChange={({ detail }) => {
                setFilteringText(detail.filteringText);
                setCurrentPageIndex(1);
              }}
              placeholder="Search blueprints..."
            />
          }
          pagination={
            <Pagination
              currentPageIndex={currentPageIndex}
              pagesCount={Math.ceil(sortedItems.length / pageSize)}
              onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
            />
          }
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center">
              <SpaceBetween size="m">
                <b>No blueprints</b>
                <p>No blueprints to display.</p>
              </SpaceBetween>
            </Box>
          }
        />
      </Container>

      <ManageBlueprintItemForm
        visible={editModalVisible}
        onDismiss={() => {
          setEditModalVisible(false);
          setEditingItem(null);
        }}
        item={editingItem}
        onSave={handleSaveItem}
      />
    </>
  );
};

export default EditBlueprintForm;