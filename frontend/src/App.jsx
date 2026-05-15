import React, { useState, useEffect } from 'react';
import {
  AppLayout, ContentLayout, Header, SpaceBetween, Container,
  Button, Textarea, Alert, Tabs, Box, Badge, FileUpload, FormField, Select
} from '@cloudscape-design/components';
import CodeEditor from './components/CodeEditor.jsx';
import ExecutionResults from './components/ExecutionResults.jsx';
import SessionHistory from './components/SessionHistory.jsx';
import CsvUploadModal from './components/CsvUploadModal.jsx';
import GlueTableSelector from './components/GlueTableSelector.jsx';
import PostgresTableSelector from './components/PostgresTableSelector.jsx';
import PostgresConnectionModal from './components/PostgresConnectionModal.jsx';
import Settings from './components/Settings.jsx';
import { generateCode, executeCode, uploadCsvFile, getSessionHistory, getSparkStatus } from './services/api';
import { v4 as uuidv4 } from 'uuid';

function App() {
  const [sessionId] = useState(uuidv4());
  const [executionEngine, setExecutionEngine] = useState('auto');
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
  const [sparkStatus, setSparkStatus] = useState(null);
  const [uploadedCsv, setUploadedCsv] = useState(null);
  const [showCsvUploadModal, setShowCsvUploadModal] = useState(false);
  const [showPostgresModal, setShowPostgresModal] = useState(false);
  const [editingConnection, setEditingConnection] = useState(null);
  const [csvUploadLoading, setCsvUploadLoading] = useState(false);
  const [sessionHistory, setSessionHistory] = useState(null);
  const [showAdditionalConnections, setShowAdditionalConnections] = useState(false);
  const [progressStages, setProgressStages] = useState([]);
  const [currentStage, setCurrentStage] = useState(null);
  const [progressSessionId, setProgressSessionId] = useState(null);

  useEffect(() => {
    checkSparkStatus();
    const interval = setInterval(checkSparkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Poll for progress while loading
  useEffect(() => {
    if (!loading || !progressSessionId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/progress/${progressSessionId}`);
        const data = await res.json();
        if (data.stages && data.stages.length > 0) {
          setProgressStages(data.stages);
          setCurrentStage(data.current_stage);
        }
      } catch (e) { /* ignore polling errors */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [loading, progressSessionId]);

  const checkSparkStatus = async () => {
    try {
      const status = await getSparkStatus();
      setSparkStatus(status);
    } catch (e) {
      setSparkStatus({ lambda_status: 'unknown', emr_status: 'unknown' });
    }
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) { setError('Please enter a prompt'); return; }
    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    setProgressStages([]);
    setCurrentStage(null);
    setProgressSessionId(sessionId);

    try {
      const s3InputPath = uploadedCsv ? uploadedCsv.s3_path : null;
      const s3SamplePath = uploadedCsv ? uploadedCsv.s3_sample_path : null;

      const response = await generateCode(
        prompt, sessionId, s3InputPath, s3SamplePath,
        selectedTables.length > 0 ? selectedTables : null,
        selectedPostgresTables.length > 0 ? selectedPostgresTables : null,
        executionEngine
      );

      if (!response.success) throw new Error(response.error || 'Code generation failed');

      if (response.result) {
        const sparkData = response.result;
        setGeneratedCode(sparkData.spark_code || '');
        setEditedCode(sparkData.spark_code || '');
        setExecutionResult({
          code: sparkData.spark_code,
          result: sparkData.actual_results || [],
          execution_output: sparkData.execution_output || [],
          success: sparkData.execution_result === 'success',
          execution_platform: response.execution_platform || 'lambda',
          s3_output_path: sparkData.s3_output_path,
          execution_message: sparkData.execution_message || '',
          timestamp: new Date().toISOString(),
        });
        setActiveTab('results');
        setSuccessMessage('Code generated and executed successfully!');
      }
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setProgressSessionId(null);
    }
  };

  const handleExecute = async (e) => {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    if (!editedCode.trim()) { setError('No code to execute'); return; }
    setExecuting(true);
    setError(null);

    try {
      const s3OutputPath = uploadedCsv
        ? uploadedCsv.s3_path.replace(/\/[^/]+$/, '/output/')
        : `s3://spark-data-914787431788-us-east-1/output/${sessionId}`;

      const response = await executeCode(editedCode, sessionId, s3OutputPath, executionEngine);

      if (response.success && response.result) {
        const sparkData = response.result;
        setExecutionResult({
          code: editedCode,
          result: sparkData.actual_results || [],
          execution_output: sparkData.execution_output || [],
          success: sparkData.execution_result === 'success',
          execution_platform: response.execution_platform || 'lambda',
          s3_output_path: sparkData.s3_output_path,
          execution_message: sparkData.execution_message || '',
          timestamp: new Date().toISOString(),
        });
      } else {
        throw new Error(response.error || 'Execution failed');
      }
      setActiveTab('results');
    } catch (err) {
      setError(err.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleCsvUpload = async (file) => {
    setCsvUploadLoading(true);
    setError(null);
    try {
      const response = await uploadCsvFile(file.name, file.content, sessionId);
      setUploadedCsv({ filename: file.name, preview: response.preview, s3_path: response.s3_path, s3_sample_path: response.s3_sample_path });
      setSuccessMessage(`CSV "${file.name}" uploaded successfully!`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      setError(`CSV upload failed: ${err.message}`);
    } finally {
      setCsvUploadLoading(false);
    }
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    const reader = new FileReader();
    reader.onload = (e) => { setEditedCode(e.target.result); setSuccessMessage('File loaded!'); setTimeout(() => setSuccessMessage(''), 3000); };
    reader.readAsText(files[0]);
  };

  const handleSaveCode = () => {
    const blob = new Blob([editedCode], { type: 'text/plain' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'spark_code.py';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  const handleCopyCode = async () => {
    try { await navigator.clipboard.writeText(editedCode); setSuccessMessage('Copied!'); setTimeout(() => setSuccessMessage(null), 3000); }
    catch { setError('Failed to copy'); }
  };

  const loadHistory = async () => {
    try { setSessionHistory(await getSessionHistory(sessionId)); } catch { setError('Failed to load history'); }
  };

  const tabs = [
    {
      id: 'generate', label: 'Generate Code',
      content: (
        <Container header={<Header variant="h2">Generate Spark Code</Header>}>
          <SpaceBetween size="l">
            {uploadedCsv && (
              <Alert type="info" dismissible onDismiss={() => setUploadedCsv(null)} header={`Using CSV: ${uploadedCsv.filename}`}>
                <Box variant="small"><pre style={{ fontSize: '11px', maxHeight: '100px', overflow: 'auto' }}>{uploadedCsv.preview}</pre></Box>
              </Alert>
            )}
            <FormField label="Describe your data processing task">
              <Textarea value={prompt} onChange={({ detail }) => setPrompt(detail.value)}
                placeholder="Example: Load the CSV and group by category showing sum of price and quantity" rows={6} />
            </FormField>
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={() => setShowCsvUploadModal(true)}>Upload CSV</Button>
                <Button variant="primary" onClick={handleGenerate} loading={loading} disabled={!prompt.trim()}>
                  Generate &amp; Execute
                </Button>
              </SpaceBetween>
            </Box>

            {loading && (
              <Container>
                <SpaceBetween size="s">
                  <Box variant="h4">Processing...</Box>
                  {progressStages.length === 0 && (
                    <Box variant="small" color="text-status-inactive">Initializing agent... (this may take a moment)</Box>
                  )}
                  {progressStages.map((stage, i) => (
                    <Box key={i} variant="small">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box color={stage.status === 'complete' ? 'text-status-success' : stage.status === 'error' ? 'text-status-error' : 'text-status-info'}>
                          {stage.status === 'complete' ? '✅' : stage.status === 'error' ? '❌' : '⏳'}
                        </Box>
                        <Box><strong>{stage.stage.replace(/_/g, ' ')}</strong></Box>
                        <Box color="text-status-inactive">{stage.message}</Box>
                        {stage.duration_s && <Box color="text-status-inactive">({stage.duration_s}s)</Box>}
                      </SpaceBetween>
                    </Box>
                  ))}
                  <Box variant="small" color="text-status-inactive">
                    This typically takes 2-3 minutes
                  </Box>
                </SpaceBetween>
              </Container>
            )}
          </SpaceBetween>
        </Container>
      ),
    },
    {
      id: 'editor', label: 'Code Editor',
      content: (
        <Container header={<Header variant="h2">Edit Code</Header>}>
          <SpaceBetween size="l">
            <SpaceBetween direction="horizontal" size="s">
              <FormField label="Upload Python file">
                <FileUpload onChange={({ detail }) => handleFileUpload(detail.value)} value={[]}
                  i18nStrings={{ uploadButtonText: () => "Choose file", dropzoneText: () => "Drop file", removeFileAriaLabel: (e) => `Remove ${e+1}`, errorIconAriaLabel: "Error" }}
                  accept=".py,.txt" />
              </FormField>
              <FormField label="Execution Engine">
                <Select selectedOption={{ label: executionEngine.charAt(0).toUpperCase() + executionEngine.slice(1), value: executionEngine }}
                  onChange={({ detail }) => setExecutionEngine(detail.selectedOption.value)}
                  options={[{ label: 'Auto', value: 'auto' }, { label: 'Lambda', value: 'lambda' }, { label: 'EMR', value: 'emr' }]} />
              </FormField>
            </SpaceBetween>
            <CodeEditor code={editedCode} onChange={setEditedCode} language="python" />
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={handleCopyCode}>Copy</Button>
                <Button onClick={handleSaveCode}>Save</Button>
                <Button onClick={() => setEditedCode(generatedCode)}>Reset</Button>
                <Button variant="primary" onClick={handleExecute} loading={executing} disabled={!editedCode.trim()}>Execute Code</Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </Container>
      ),
    },
    { id: 'results', label: 'Execution Results', content: <ExecutionResults result={executionResult} /> },
    {
      id: 'history', label: 'Session History',
      content: (
        <Box>
          {!sessionHistory && <Box textAlign="center" padding="l"><Button onClick={loadHistory}>Load History</Button></Box>}
          {sessionHistory && <SessionHistory sessionId={sessionId} history={sessionHistory} onRefresh={loadHistory}
            onExecuteCode={(code) => { setEditedCode(code); setActiveTab('editor'); }} />}
        </Box>
      ),
    },
    { id: 'settings', label: 'Settings', content: <Settings /> },
  ];

  return (
    <>
      <AppLayout
        navigationHide={false}
        navigation={
          <SpaceBetween size="l">
            <GlueTableSelector key={resetKey} sessionId={sessionId}
              onTablesSelected={(tables) => { setSelectedTables(tables); setSuccessMessage(`Selected ${tables.length} Glue table(s)`); setTimeout(() => setSuccessMessage(null), 3000); }} />

            {postgresConnection && (
              <PostgresTableSelector key={resetKey} sessionId={sessionId} connection={postgresConnection}
                onTablesSelected={(tables) => { setSelectedPostgresTables(tables); setSuccessMessage(`Selected ${tables.length} PostgreSQL table(s)`); setTimeout(() => setSuccessMessage(null), 3000); }}
                onDisconnect={() => { setPostgresConnection(null); setSelectedPostgresTables([]); }}
                onConfigure={() => { setEditingConnection(postgresConnection); setShowPostgresModal(true); }} />
            )}

            <Container header={<Header variant="h3" actions={<Button iconName={showAdditionalConnections ? "angle-up" : "angle-down"} variant="icon" onClick={() => setShowAdditionalConnections(!showAdditionalConnections)} />}>Additional Connections</Header>}>
              {showAdditionalConnections && (
                <SpaceBetween direction="horizontal" size="m">
                  <Button variant="normal" onClick={() => { setEditingConnection(null); setShowPostgresModal(true); }} disabled={!!postgresConnection}>
                    <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                      <img src="/aurora.png" alt="PostgreSQL" style={{width: '24px', height: '24px'}} /><Box>PostgreSQL</Box>
                    </SpaceBetween>
                  </Button>
                  <Button variant="normal" disabled>
                    <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                      <img src="/snowflake.png" alt="Snowflake" style={{width: '24px', height: '24px'}} /><Box>Snowflake</Box>
                    </SpaceBetween>
                  </Button>
                  <Button variant="normal" disabled>
                    <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                      <img src="/databricks.png" alt="Databricks" style={{width: '24px', height: '24px'}} /><Box>Databricks</Box>
                    </SpaceBetween>
                  </Button>
                </SpaceBetween>
              )}
            </Container>

            {selectedTables.length > 0 && (
              <Container>
                <SpaceBetween size="xs">
                  <Box variant="awsui-key-label">Selected Glue Tables</Box>
                  {selectedTables.map((t, i) => (
                    <Box key={i} fontSize="body-s">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box>{t.database}.{t.table}</Box>
                        <Button variant="icon" iconName="close" onClick={() => setSelectedTables(selectedTables.filter((_, idx) => idx !== i))} />
                      </SpaceBetween>
                    </Box>
                  ))}
                </SpaceBetween>
              </Container>
            )}

            {selectedPostgresTables.length > 0 && (
              <Container>
                <SpaceBetween size="xs">
                  <Box variant="awsui-key-label">Selected PostgreSQL Tables</Box>
                  {selectedPostgresTables.map((t, i) => (
                    <Box key={i} fontSize="body-s">
                      <SpaceBetween direction="horizontal" size="xs">
                        <Box>{t.connection_name}: {t.database}.{t.schema}.{t.table}</Box>
                        <Button variant="icon" iconName="close" onClick={() => setSelectedPostgresTables(selectedPostgresTables.filter((_, idx) => idx !== i))} />
                      </SpaceBetween>
                    </Box>
                  ))}
                </SpaceBetween>
              </Container>
            )}
          </SpaceBetween>
        }
        toolsHide
        content={
          <ContentLayout header={
            <Header variant="h1" info={
              <SpaceBetween direction="horizontal" size="xs">
                <Badge color={sparkStatus?.lambda_status === 'ready' ? 'green' : 'grey'}>Lambda {(sparkStatus?.lambda_status || 'checking...').replace(/_/g, ' ')}</Badge>
                <Badge color={sparkStatus?.emr_status === 'ready' ? 'green' : 'grey'}>EMR {(sparkStatus?.emr_status || 'checking...').replace(/_/g, ' ')}</Badge>
              </SpaceBetween>
            }>Spark Code Interpreter</Header>
          }>
            <SpaceBetween size="l">
              {error && <Alert type="error" dismissible onDismiss={() => setError(null)}>{error}</Alert>}
              {successMessage && <Alert type="success" dismissible onDismiss={() => setSuccessMessage(null)}>{successMessage}</Alert>}
              <Tabs activeTabId={activeTab} onChange={({ detail }) => setActiveTab(detail.activeTabId)} tabs={tabs} />
            </SpaceBetween>
          </ContentLayout>
        }
      />
      <CsvUploadModal visible={showCsvUploadModal} onDismiss={() => setShowCsvUploadModal(false)} onUpload={handleCsvUpload} loading={csvUploadLoading} />
      <PostgresConnectionModal visible={showPostgresModal} onDismiss={() => { setShowPostgresModal(false); setEditingConnection(null); }}
        existingConnection={editingConnection}
        onSave={(conn) => { setPostgresConnection(conn); setSuccessMessage(`Connection '${conn.name}' saved`); setTimeout(() => setSuccessMessage(null), 3000); setResetKey(prev => prev + 1); setEditingConnection(null); }} />
    </>
  );
}

export default App;
