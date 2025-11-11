import React, { useState, useEffect } from 'react';
import { Modal, Box, SpaceBetween, FormField, Input, Select, Button } from '@cloudscape-design/components';

const PostgresConnectionModal = ({ visible, onDismiss, onSave, existingConnection = null }) => {
  const [connectionName, setConnectionName] = useState('');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('5432');
  const [database, setDatabase] = useState('postgres');
  const [authMethod, setAuthMethod] = useState({ label: 'Secrets Manager ARN', value: 'secrets_manager' });
  const [secretArn, setSecretArn] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const authOptions = [
    { label: 'Secrets Manager ARN', value: 'secrets_manager' },
    { label: 'IAM Authentication', value: 'iam' },
    { label: 'Username/Password', value: 'user_password' }
  ];

  useEffect(() => {
    if (existingConnection) {
      setConnectionName(existingConnection.name);
      setHost(existingConnection.host || '');
      setPort(existingConnection.port?.toString() || '5432');
      setDatabase(existingConnection.database || 'postgres');
      setSecretArn(existingConnection.secret_arn || '');
      const authOpt = authOptions.find(a => a.value === existingConnection.auth_method) || authOptions[0];
      setAuthMethod(authOpt);
    }
  }, [existingConnection, visible]);

  const handleTestConnection = async () => {
    if (!host) {
      setTestResult({ success: false, message: 'Host is required' });
      return;
    }

    if (authMethod.value === 'secrets_manager' && !secretArn) {
      setTestResult({ success: false, message: 'Secret ARN is required' });
      return;
    }

    if (authMethod.value === 'user_password' && (!username || !password)) {
      setTestResult({ success: false, message: 'Username and password are required' });
      return;
    }

    setTestLoading(true);
    setTestResult(null);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/postgres/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          port: parseInt(port),
          database,
          auth_method: authMethod.value,
          secret_arn: authMethod.value === 'secrets_manager' ? secretArn : undefined,
          username: authMethod.value === 'user_password' ? username : undefined,
          password: authMethod.value === 'user_password' ? password : undefined
        })
      });

      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({ success: false, message: 'Failed to test connection: ' + err.message });
    } finally {
      setTestLoading(false);
    }
  };

  const handleSave = async () => {
    if (!connectionName || !host) {
      setError('Connection name and host are required');
      return;
    }

    if (authMethod.value === 'secrets_manager' && !secretArn) {
      setError('Secret ARN is required');
      return;
    }

    if (authMethod.value === 'user_password' && (!username || !password)) {
      setError('Username and password are required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/postgres/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: connectionName,
          host,
          port: parseInt(port),
          database,
          auth_method: authMethod.value,
          secret_arn: authMethod.value === 'secrets_manager' ? secretArn : undefined,
          username: authMethod.value === 'user_password' ? username : undefined,
          password: authMethod.value === 'user_password' ? password : undefined,
          is_update: !!existingConnection
        })
      });

      const data = await response.json();
      if (data.success) {
        onSave && onSave(data.connection);
        handleClose();
      } else {
        setError(data.error || 'Failed to create connection');
      }
    } catch (err) {
      setError('Failed to create connection: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!existingConnection) {
      setConnectionName('');
      setHost('');
      setPort('5432');
      setDatabase('postgres');
      setAuthMethod({ label: 'Secrets Manager ARN', value: 'secrets_manager' });
      setSecretArn('');
      setUsername('');
      setPassword('');
    }
    setError(null);
    onDismiss();
  };

  return (
    <Modal
      visible={visible}
      onDismiss={handleClose}
      header={existingConnection ? "Configure PostgreSQL Connection" : "Add PostgreSQL Connection"}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={handleClose}>Cancel</Button>
            <Button variant="primary" onClick={handleSave} loading={loading}>
              {existingConnection ? "Save & Reconnect" : "Save Connection"}
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      <SpaceBetween size="m">
        <FormField label="Connection Name" description="Unique name for this connection">
          <Input
            value={connectionName}
            onChange={({ detail }) => setConnectionName(detail.value)}
            placeholder="e.g., aurora-prod"
            disabled={!!existingConnection}
          />
        </FormField>

        <FormField label="Host" description="PostgreSQL server hostname or endpoint">
          <Input
            value={host}
            onChange={({ detail }) => setHost(detail.value)}
            placeholder="e.g., cluster.region.rds.amazonaws.com"
          />
        </FormField>

        <FormField label="Port">
          <Input
            value={port}
            onChange={({ detail }) => setPort(detail.value)}
            type="number"
          />
        </FormField>

        <FormField label="Database" description="Default database to connect to">
          <Input
            value={database}
            onChange={({ detail }) => setDatabase(detail.value)}
            placeholder="postgres"
          />
        </FormField>

        <FormField label="Authentication Method">
          <Select
            selectedOption={authMethod}
            onChange={({ detail }) => setAuthMethod(detail.selectedOption)}
            options={authOptions}
          />
        </FormField>

        {authMethod.value === 'secrets_manager' && (
          <FormField label="Secrets Manager ARN" description="ARN of the secret containing credentials">
            <Input
              value={secretArn}
              onChange={({ detail }) => setSecretArn(detail.value)}
              placeholder="arn:aws:secretsmanager:region:account:secret:name"
            />
          </FormField>
        )}

        {authMethod.value === 'user_password' && (
          <>
            <FormField label="Username">
              <Input
                value={username}
                onChange={({ detail }) => setUsername(detail.value)}
                placeholder="postgres"
              />
            </FormField>
            <FormField label="Password">
              <Input
                value={password}
                onChange={({ detail }) => setPassword(detail.value)}
                type="password"
                placeholder="Enter password"
              />
            </FormField>
          </>
        )}

        {authMethod.value === 'iam' && (
          <Box color="text-status-info">
            IAM authentication will use the AWS credentials from your environment.
            Ensure your IAM role has rds-db:connect permission.
          </Box>
        )}

        <Button onClick={handleTestConnection} loading={testLoading} iconName="status-positive">
          Test Connection
        </Button>

        {testResult && (
          <Box color={testResult.success ? "text-status-success" : "text-status-error"}>
            {testResult.success ? '✓ ' : '✗ '}{testResult.message}
          </Box>
        )}

        {error && (
          <Box color="text-status-error">{error}</Box>
        )}
      </SpaceBetween>
    </Modal>
  );
};

export default PostgresConnectionModal;
