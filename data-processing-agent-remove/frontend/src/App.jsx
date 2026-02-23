import React, { useState, useEffect } from 'react';
import {
  AppLayout, ContentLayout, Header, SpaceBetween, Container,
  Button, Textarea, Alert, Tabs, Box, Badge, FileUpload, FormField, Select
} from '@cloudscape-design/components';
import CodeEditor from './components/CodeEditor.jsx';
import ExecutionResults from './components/ExecutionResults.jsx';
import RayDashboard from './components/RayDashboard.jsx';
import SessionHistory from './components/SessionHistory.jsx';
import CsvUploadModal from './components/CsvUploadModal.jsx';
import GlueTableSelector from './components/GlueTableSelector.jsx';
import PostgresTableSelector from './components/PostgresTableSelector.jsx';
import PostgresConnectionModal from './components/PostgresConnectionModal.jsx';
import RayJobsManager from './components/RayJobsManager.jsx';
import Settings from './components/Settings.jsx';
import FrameworkSelector from './components/FrameworkSelector.jsx';
import { generateCode, executeCode, getRayStatus, uploadFile, uploadCsvFile, getSessionHistory, generateSparkCode, executeSparkCode, uploadSparkCsv } from './services/api';
import { v4 as uuidv4 } from 'uuid';

function App() {
  const [sessionId] = useState(uuidv4());
  const [framework, setFramework] = useState('ray'); // 'ray' or 'spark'
  const [executionEngine, setExecutionEngine] = useState('auto'); // 'auto', 'lambda', or 'emr'
  const [prompt, setPrompt] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [editedCode, setEditedCode] = useState('');
  const [executionResult, setExecutionResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedTables, setSelectedTables] = useState([]);
  const [selectedPostgresTables, setSelectedPostgresTables] = useState([]);
  const [postgresConnection, setPostgresConnection] = useState(null);
  const [resetKey, setResetKey] = useState(0);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('generate');
  const [agenticTab, setAgenticTab] = useState('data-discovery');
  const [rayStatus, setRayStatus] = useState(null);
  const [sparkStatus, setSparkStatus] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadedCsv, setUploadedCsv] = useState(null);
  const [showCsvUploadModal, setShowCsvUploadModal] = useState(false);
  const [showPostgresModal, setShowPostgresModal] = useState(false);
  const [editingConnection, setEditingConnection] = useState(null);
  const [csvUploadLoading, setCsvUploadLoading] = useState(false);
  const [sessionHistory, setSessionHistory] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [showAdditionalConnections, setShowAdditionalConnections] = useState(false);

  useEffect(() => {
    // Check both Ray and Spark status on mount
    checkRayStatus();
    checkSparkStatus();
    
    // Set up intervals for both
    const rayInterval = setInterval(checkRayStatus, 30000);
    const sparkInterval = setInterval(checkSparkStatus, 30000);
    
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        checkRayStatus();
        checkSparkStatus();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      clearInterval(rayInterval);
      clearInterval(sparkInterval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const checkRayStatus = async () => {
    try {
      const status = await getRayStatus();
      setRayStatus(status);
    } catch (e) {
      setRayStatus({ status: 'disconnected' });
    }
  };

  const checkSparkStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/spark/status');
      const status = await response.json();
      setSparkStatus(status);
    } catch (e) {
      setSparkStatus({ lambda_status: 'unknown', emr_status: 'unknown' });
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    
    try {
      let response;
      
      if (framework === 'spark') {
        // Spark code generation (includes validation and execution)
        const s3InputPath = uploadedCsv ? `s3://spark-data-260005718447-us-east-1/${uploadedCsv.filename}` : null;
        const s3OutputPath = `s3://spark-data-260005718447-us-east-1/output/${sessionId}`;
        
        response = await generateSparkCode(
          prompt, 
          sessionId, 
          s3InputPath, 
          selectedTables.length > 0 ? selectedTables : null,
          selectedPostgresTables.length > 0 ? selectedPostgresTables : null,
          executionEngine
        );
        
        // Check for errors first
        if (!response.success) {
          throw new Error(response.error || 'Spark generation failed');
        }
        
        // Parse Spark response (contains JSON in result field)
        if (response.result) {
          try {
            const sparkData = response.result;
            
            setGeneratedCode(sparkData.spark_code || '');
            setEditedCode(sparkData.spark_code || '');
            
            // Spark auto-executes, so show results immediately
            setExecutionResult({
              code: sparkData.spark_code,
              result: sparkData.actual_results || [],
              execution_output: sparkData.execution_output || [],
              success: sparkData.execution_result === 'success',
              execution_platform: 'spark',
              s3_output_path: sparkData.s3_output_path,
              timestamp: new Date().toISOString()
            });
            
            setActiveTab('results');
            setSuccessMessage('Spark code generated and executed successfully!');
          } catch (parseErr) {
            // If parsing fails, just show the raw result
            setGeneratedCode(response.result);
            setEditedCode(response.result);
            setActiveTab('editor');
          }
        }
      } else {
        // Ray code generation
        response = await generateCode(prompt, sessionId);
        
        // Ensure code is properly formatted
        let code = response.code;
        
        // If code contains escaped newlines, unescape them
        if (typeof code === 'string' && code.includes('\\n') && !code.includes('\n')) {
          code = code.replace(/\\n/g, '\n').replace(/\\t/g, '\t');
        }
        
        setGeneratedCode(code);
        setEditedCode(code);
        
        // If auto-executed, capture the results IMMEDIATELY
        if (response.auto_executed && response.execution_result) {
          setActiveTab('results');
          
          setExecutionResult({
            success: true,
            result: response.execution_result,
            job_id: response.job_id,
            timestamp: new Date().toISOString()
          });
          
          setSessionHistory(null);
          setUploadedCsv(null);
          setSelectedTables([]);
          setResetKey(prev => prev + 1);
        } else {
          setActiveTab('editor');
        }
      }
      
      let successMsg = 'Code generated and executed successfully!';
      if (response.iterations > 1) {
        successMsg += ` (Fixed after ${response.iterations} iterations)`;
      }
      if (response.csv_file_used) {
        successMsg += ` Using CSV: ${response.csv_file_used}`;
      }
      setSuccessMessage(successMsg);
      setTimeout(() => setSuccessMessage(null), 5000);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    
    if (!editedCode.trim()) {
      setError('No code to execute');
      return;
    }
    
    setExecuting(true);
    setError(null);
    
    try {
      let response;
      
      if (framework === 'spark') {
        // Spark code execution
        const s3OutputPath = `s3://spark-data-260005718447-us-east-1/output/${sessionId}`;
        response = await executeSparkCode(editedCode, sessionId, s3OutputPath, executionEngine);
        
        // Handle Spark response (same structure as generate)
        if (response.success && response.result) {
          const sparkData = response.result;
          setExecutionResult({
            code: editedCode,
            result: sparkData.actual_results || [],
            execution_output: sparkData.execution_output || [],
            success: sparkData.execution_result === 'success',
            execution_platform: 'spark',
            s3_output_path: sparkData.s3_output_path,
            timestamp: new Date().toISOString()
          });
        } else {
          throw new Error(response.error || 'Spark execution failed');
        }
      } else {
        // Ray code execution
        response = await executeCode(editedCode, sessionId);
        setExecutionResult({
          code: editedCode,
          result: response.output || response.result || response.error,
          success: response.success,
          job_id: response.job_id,
          timestamp: new Date().toISOString(),
          images: response.images || [],
          execution_platform: response.execution_platform,
          s3_output_path: response.s3_output_path
        });
      }
      
      setActiveTab('results');
      
      // Refresh session history to show the new execution
      setTimeout(() => {
        loadHistory();
      }, 1000);
      
      // Reset session data sources after execution
      await fetch(`http://localhost:8000/sessions/${sessionId}/reset`, {
        method: 'POST'
      });
      
      // Clear UI state
      setUploadedCsv(null);
      setSelectedTables([]);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;

    const file = files[0];
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const content = e.target.result;
        setEditedCode(content);
        setSuccessMessage(`File "${file.name}" loaded successfully!`);
        setTimeout(() => setSuccessMessage(''), 3000);
      } catch (err) {
        setError(`Failed to load file: ${err.message}`);
      }
    };
    
    reader.onerror = () => {
      setError('Failed to read file');
    };
    
    reader.readAsText(file);
  };

  const handleCsvUpload = async (file) => {
    setCsvUploadLoading(true);
    setError(null);
    
    try {
      let response;
      
      if (framework === 'spark') {
        // Spark CSV upload
        response = await uploadSparkCsv(file.name, file.content, sessionId);
      } else {
        // Ray CSV upload
        response = await uploadCsvFile(file.name, file.content, sessionId);
      }
      
      setUploadedCsv({
        filename: file.name,
        preview: response.preview
      });
      setSuccessMessage(`CSV file "${file.name}" uploaded successfully!`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(`CSV upload failed: ${err.message}`);
    } finally {
      setCsvUploadLoading(false);
    }
  };

  const handleCsvRemoval = () => {
    setUploadedCsv(null);
    setSuccessMessage('CSV file removed');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const handleSaveCode = () => {
    if (!editedCode.trim()) {
      setError('No code to save');
      return;
    }
    
    const blob = new Blob([editedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ray_code.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    setSuccessMessage('Code saved successfully!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const handleCopyCode = async () => {
    if (!editedCode.trim()) {
      setError('No code to copy');
      return;
    }
    
    try {
      await navigator.clipboard.writeText(editedCode);
      setSuccessMessage('Code copied to clipboard!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('Failed to copy code');
    }
  };

  const loadHistory = async () => {
    try {
      const response = await getSessionHistory(sessionId);
      setSessionHistory(response);
    } catch (err) {
      setError('Failed to load history');
    }
  };

  const tabs = [
    {
      id: 'generate',
      label: 'Generate Code',
      content: (
        <Container header={<Header variant="h2">Generate Code</Header>}>
          <SpaceBetween size="l">
            {uploadedCsv && (
              <Alert
                type="info"
                dismissible
                onDismiss={handleCsvRemoval}
                header={`Using CSV: ${uploadedCsv.filename}`}
              >
                <Box variant="small">
                  <pre style={{ fontSize: '11px', maxHeight: '100px', overflow: 'auto' }}>
                    {uploadedCsv.preview}
                  </pre>
                </Box>
              </Alert>
            )}
            
            <FormField label="Describe your data processing task">
              <Textarea
                value={prompt}
                onChange={({ detail }) => setPrompt(detail.value)}
                placeholder="Example: Create a dataset with 10000 rows and calculate squared values..."
                rows={6}
              />
            </FormField>
            
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={() => setShowCsvUploadModal(true)}>
                  Upload CSV
                </Button>
                <Button
                  variant="primary"
                  onClick={handleGenerate}
                  loading={loading}
                  disabled={!prompt.trim()}
                >
                  Generate Code
                </Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </Container>
      )
    },
    {
      id: 'editor',
      label: 'Code Editor',
      content: (
        <Container header={<Header variant="h2">Edit Code</Header>}>
          <SpaceBetween size="l">
            <SpaceBetween direction="horizontal" size="s">
              <FormField label="Upload Python file (optional)">
                <FileUpload
                  onChange={({ detail }) => handleFileUpload(detail.value)}
                  value={[]}
                  i18nStrings={{
                    uploadButtonText: e => e ? "Choose files" : "Choose file",
                    dropzoneText: e => e ? "Drop files" : "Drop file",
                    removeFileAriaLabel: e => `Remove file ${e + 1}`,
                    errorIconAriaLabel: "Error"
                  }}
                  accept=".py,.txt"
                />
              </FormField>
              {framework === 'spark' && (
                <FormField label="Execution Engine">
                  <Select
                    selectedOption={{ label: executionEngine.charAt(0).toUpperCase() + executionEngine.slice(1), value: executionEngine }}
                    onChange={({ detail }) => setExecutionEngine(detail.selectedOption.value)}
                    options={[
                      { label: 'Auto', value: 'auto' },
                      { label: 'Lambda', value: 'lambda' },
                      { label: 'EMR', value: 'emr' }
                    ]}
                  />
                </FormField>
              )}
            </SpaceBetween>
            
            <CodeEditor
              code={editedCode}
              onChange={setEditedCode}
              language="python"
            />
            
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={handleCopyCode}>Copy</Button>
                <Button onClick={handleSaveCode}>Save</Button>
                <Button onClick={() => setEditedCode(generatedCode)}>Reset</Button>
                <Button
                  variant="primary"
                  onClick={handleExecute}
                  loading={executing}
                  disabled={!editedCode.trim()}
                >
                  Execute Code
                </Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </Container>
      )
    },
    {
      id: 'results',
      label: 'Execution Results',
      content: <ExecutionResults result={executionResult} />
    },
    {
      id: 'history',
      label: 'Session History',
      content: (
        <Box>
          {!sessionHistory && (
            <Box textAlign="center" padding="l">
              <Button onClick={loadHistory}>Load History</Button>
            </Box>
          )}
          {sessionHistory && (
            <SessionHistory 
              sessionId={sessionId}
              history={sessionHistory} 
              onRefresh={loadHistory}
              onExecuteCode={(code) => {
                setEditedCode(code);
                setActiveTab('editor');
              }}
            />
          )}
        </Box>
      )
    },
    ...(framework === 'ray' ? [{
      id: 'dashboard',
      label: 'Ray Dashboard',
      content: <RayDashboard dashboardUrl={rayStatus?.dashboard_url} jobId={selectedJobId} onCloseJobLogs={() => setSelectedJobId(null)} />
    }] : []),
    {
      id: 'settings',
      label: 'Settings',
      content: <Settings />
    }
  ];

  return (
    <>
      <AppLayout
        navigationHide={false}
        navigation={
          <SpaceBetween size="l">
            <FrameworkSelector 
              value={framework}
              onChange={setFramework}
            />
            
            {framework === 'spark' && (
              <GlueTableSelector 
                key={resetKey}
                sessionId={sessionId}
                onTablesSelected={(tables) => {
                  setSelectedTables(tables);
                  setSuccessMessage(`Selected ${tables.length} Glue table(s)`);
                  setTimeout(() => setSuccessMessage(null), 3000);
                }}
              />
            )}

            {framework === 'spark' && postgresConnection && (
              <PostgresTableSelector
                key={resetKey}
                sessionId={sessionId}
                connection={postgresConnection}
                onTablesSelected={(tables) => {
                  setSelectedPostgresTables(tables);
                  setSuccessMessage(`Selected ${tables.length} PostgreSQL table(s)`);
                  setTimeout(() => setSuccessMessage(null), 3000);
                }}
                onDisconnect={() => {
                  setPostgresConnection(null);
                  setSelectedPostgresTables([]);
                  setSuccessMessage('Disconnected from PostgreSQL');
                  setTimeout(() => setSuccessMessage(null), 3000);
                }}
                onConfigure={() => {
                  setEditingConnection(postgresConnection);
                  setShowPostgresModal(true);
                }}
              />
            )}
            
            {framework === 'spark' && (
              <Container
                header={
                  <Header
                    variant="h3"
                    actions={
                      <Button
                        iconName={showAdditionalConnections ? "angle-up" : "angle-down"}
                        variant="icon"
                        onClick={() => setShowAdditionalConnections(!showAdditionalConnections)}
                      />
                    }
                  >
                    Additional Connections
                  </Header>
                }
              >
                {showAdditionalConnections && (
                  <SpaceBetween direction="horizontal" size="m">
                    <Button
                      variant="normal"
                      onClick={() => {
                        setEditingConnection(null);
                        setShowPostgresModal(true);
                      }}
                      disabled={!!postgresConnection}
                    >
                      <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                        <img src="/aurora.png" alt="PostgreSQL" style={{width: '24px', height: '24px'}} />
                        <Box>PostgreSQL</Box>
                      </SpaceBetween>
                    </Button>
                    <Button
                      variant="normal"
                      onClick={() => {/* Placeholder for Snowflake connection */}}
                      disabled
                    >
                      <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                        <img src="/snowflake.png" alt="Snowflake" style={{width: '24px', height: '24px'}} />
                        <Box>Snowflake</Box>
                      </SpaceBetween>
                    </Button>
                    <Button
                      variant="normal"
                      onClick={() => {/* Placeholder for Databricks connection */}}
                      disabled
                    >
                      <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                        <img src="/databricks.png" alt="Databricks" style={{width: '24px', height: '24px'}} />
                        <Box>Databricks</Box>
                      </SpaceBetween>
                    </Button>
                  </SpaceBetween>
                )}
              </Container>
            )}
            {framework === 'spark' && selectedTables.length > 0 && (
              <Container>
                <SpaceBetween size="xs">
                  <Box variant="awsui-key-label">Selected Glue Tables</Box>
                  {selectedTables.map((t, i) => (
                    <Box key={i} fontSize="body-s">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box>{t.database}.{t.table}</Box>
                        <Button
                          variant="icon"
                          iconName="close"
                          onClick={() => setSelectedTables(selectedTables.filter((_, idx) => idx !== i))}
                          ariaLabel={`Remove ${t.database}.${t.table}`}
                        />
                      </SpaceBetween>
                    </Box>
                  ))}
                </SpaceBetween>
              </Container>
            )}

            {framework === 'spark' && selectedPostgresTables.length > 0 && (
              <Container>
                <SpaceBetween size="xs">
                  <Box variant="awsui-key-label">Selected PostgreSQL Tables</Box>
                  {selectedPostgresTables.map((t, i) => (
                    <Box key={i} fontSize="body-s">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box>{t.connection_name}: {t.database}.{t.schema}.{t.table}</Box>
                        <Button
                          variant="icon"
                          iconName="close"
                          onClick={() => setSelectedPostgresTables(selectedPostgresTables.filter((_, idx) => idx !== i))}
                          ariaLabel={`Remove ${t.database}.${t.schema}.${t.table}`}
                        />
                      </SpaceBetween>
                    </Box>
                  ))}
                </SpaceBetween>
              </Container>
            )}
            
            {framework === 'ray' && (
              <RayJobsManager 
                onViewDetails={(jobId) => {
                  setSelectedJobId(jobId);
                  setActiveTab('dashboard');
                }}
              />
            )}
          </SpaceBetween>
        }
        toolsHide
        content={
          <ContentLayout
            header={
              <SpaceBetween size="m">
                <Header
                  variant="h1"
                  info={
                    framework === 'ray' ? (
                      <Badge color={rayStatus?.status === 'connected' ? 'green' : 'red'}>
                        Ray {rayStatus?.status || 'checking...'}
                      </Badge>
                    ) : (
                      <SpaceBetween direction="horizontal" size="xs">
                        <Badge color={sparkStatus?.lambda_status === 'ready' ? 'green' : 'grey'}>
                          Spark on Lambda {(sparkStatus?.lambda_status || 'checking...').replace(/_/g, ' ')}
                        </Badge>
                        <Badge color={sparkStatus?.emr_status === 'ready' ? 'green' : 'grey'}>
                          EMR {(sparkStatus?.emr_status || 'checking...').replace(/_/g, ' ')}
                        </Badge>
                      </SpaceBetween>
                    )
                  }
                >
                  Data Processing Agent
                </Header>
                {framework === 'ray' && rayStatus?.ray_version && (
                  <Box variant="small">Ray Version: {rayStatus.ray_version}</Box>
                )}
              </SpaceBetween>
            }
          >
            <SpaceBetween size="l">
              {error && (
                <Alert type="error" dismissible onDismiss={() => setError(null)}>
                  {error}
                </Alert>
              )}
              
              {successMessage && (
                <Alert type="success" dismissible onDismiss={() => setSuccessMessage(null)}>
                  {successMessage}
                </Alert>
              )}
              
              <Tabs
                activeTabId={activeTab}
                onChange={({ detail }) => setActiveTab(detail.activeTabId)}
                tabs={tabs}
              />
              
              {activeTab === 'generate' && (
                <Container header={<Header variant="h2">AI-Powered Data Operations</Header>}>
                  <Tabs
                    activeTabId={agenticTab}
                    onChange={({ detail }) => setAgenticTab(detail.activeTabId)}
                    tabs={[
                      {
                        id: 'data-discovery',
                        label: 'Agentic Data Asset Discovery',
                        content: (
                          <SpaceBetween size="l">
                            <Alert type="info" header="Coming Soon">
                              This feature will enable AI-powered discovery and cataloging of data assets across your organization.
                            </Alert>
                            <Box padding="l" textAlign="center">
                              <Box variant="h3" color="text-status-inactive">
                                Feature in Development
                              </Box>
                              <Box variant="p" color="text-status-inactive" margin={{ top: 's' }}>
                                Automated data asset discovery, classification, and metadata generation will be available in a future release.
                              </Box>
                            </Box>
                          </SpaceBetween>
                        )
                      },
                      {
                        id: 'compliance-validation',
                        label: 'Agentic Compliance Validation',
                        content: (
                          <SpaceBetween size="l">
                            <Alert type="info" header="Coming Soon">
                              This feature will provide AI-powered compliance validation and governance for your data processing workflows.
                            </Alert>
                            <Box padding="l" textAlign="center">
                              <Box variant="h3" color="text-status-inactive">
                                Feature in Development
                              </Box>
                              <Box variant="p" color="text-status-inactive" margin={{ top: 's' }}>
                                Automated compliance checking, policy validation, and governance recommendations will be available in a future release.
                              </Box>
                            </Box>
                          </SpaceBetween>
                        )
                      }
                    ]}
                  />
                </Container>
              )}
            </SpaceBetween>
          </ContentLayout>
        }
      />
      
      <CsvUploadModal
        visible={showCsvUploadModal}
        onDismiss={() => setShowCsvUploadModal(false)}
        onUpload={handleCsvUpload}
        loading={csvUploadLoading}
      />

      <PostgresConnectionModal
        visible={showPostgresModal}
        onDismiss={() => {
          setShowPostgresModal(false);
          setEditingConnection(null);
        }}
        existingConnection={editingConnection}
        onSave={(connection) => {
          setPostgresConnection(connection);
          setSuccessMessage(`Connection '${connection.name}' ${editingConnection ? 'updated' : 'created'} successfully`);
          setTimeout(() => setSuccessMessage(null), 3000);
          setResetKey(prev => prev + 1);
          setEditingConnection(null);
        }}
      />
    </>
  );
}

export default App;
