const API_BASE_URL = 'http://localhost:8000';

export const generateCode = async (prompt, sessionId, s3InputPath = null, selectedTables = null, selectedPostgresTables = null, executionEngine = 'auto') => {
  const response = await fetch(`${API_BASE_URL}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      session_id: sessionId,
      s3_input_path: s3InputPath,
      selected_tables: selectedTables,
      selected_postgres_tables: selectedPostgresTables,
      execution_engine: executionEngine,
    }),
  });
  if (!response.ok) throw new Error('Failed to generate code');
  return response.json();
};

export const executeCode = async (code, sessionId, s3OutputPath, executionPlatform = 'lambda') => {
  const response = await fetch(`${API_BASE_URL}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      spark_code: code,
      session_id: sessionId,
      s3_output_path: s3OutputPath,
      execution_platform: executionPlatform,
    }),
  });
  if (!response.ok) throw new Error('Failed to execute code');
  return response.json();
};

export const uploadCsvFile = async (filename, content, sessionId) => {
  const response = await fetch(`${API_BASE_URL}/upload-csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content, session_id: sessionId }),
  });
  if (!response.ok) throw new Error('Failed to upload CSV');
  return response.json();
};

export const getSessionHistory = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/history/${sessionId}`);
  if (!response.ok) throw new Error('Failed to get history');
  return response.json();
};

export const getSparkStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/status`);
  return response.json();
};

export const getSettings = async () => {
  const response = await fetch(`${API_BASE_URL}/settings`);
  return response.json();
};

export const saveSettings = async (settings) => {
  const response = await fetch(`${API_BASE_URL}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!response.ok) throw new Error('Failed to save settings');
  return response.json();
};
