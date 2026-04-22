import React, { useState, useEffect } from 'react';
import {
  Container, Header, Form, FormField, Input, Button,
  SpaceBetween, Alert, ExpandableSection, Select
} from '@cloudscape-design/components';

const Settings = () => {
  const [settings, setSettings] = useState({
    bedrock_model: '',
    bedrock_region: 'us-east-1',
    code_gen_agent_arn: '',
    s3_bucket: '',
    lambda_function: '',
    emr_application_id: '',
    supervisor_arn: '',
    max_retries: 3,
    file_size_threshold_mb: 100,
    result_preview_rows: 100,
    presigned_url_expiry_hours: 24,
    lambda_timeout_seconds: 300,
    emr_timeout_minutes: 10,
  });
  const [claudeModels, setClaudeModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => { loadSettings(); loadClaudeModels(); }, []);

  const loadClaudeModels = async () => {
    try {
      const res = await fetch('http://localhost:8000/claude-models');
      const data = await res.json();
      setClaudeModels(data.models.map(m => ({ label: m.name, value: m.id })));
    } catch (e) { console.error('Failed to load models:', e); }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch('http://localhost:8000/settings');
      const data = await res.json();
      setSettings({
        bedrock_model: data.global?.bedrock_model || '',
        bedrock_region: data.global?.bedrock_region || 'us-east-1',
        code_gen_agent_arn: data.global?.code_gen_agent_arn || '',
        s3_bucket: data.spark?.s3_bucket || '',
        lambda_function: data.spark?.lambda_function || '',
        emr_application_id: data.spark?.emr_application_id || '',
        supervisor_arn: data.spark?.supervisor_arn || '',
        max_retries: data.spark?.max_retries || 3,
        file_size_threshold_mb: data.spark?.file_size_threshold_mb || 100,
        result_preview_rows: data.spark?.result_preview_rows || 100,
        presigned_url_expiry_hours: data.spark?.presigned_url_expiry_hours || 24,
        lambda_timeout_seconds: data.spark?.lambda_timeout_seconds || 300,
        emr_timeout_minutes: data.spark?.emr_timeout_minutes || 10,
      });
    } catch (e) { setMessage({ type: 'error', content: 'Failed to load settings' }); }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      const payload = {
        global: {
          bedrock_model: settings.bedrock_model,
          bedrock_region: settings.bedrock_region,
          code_gen_agent_arn: settings.code_gen_agent_arn,
        },
        spark: {
          s3_bucket: settings.s3_bucket,
          lambda_function: settings.lambda_function,
          emr_application_id: settings.emr_application_id,
          supervisor_arn: settings.supervisor_arn,
          max_retries: settings.max_retries,
          file_size_threshold_mb: settings.file_size_threshold_mb,
          result_preview_rows: settings.result_preview_rows,
          presigned_url_expiry_hours: settings.presigned_url_expiry_hours,
          lambda_timeout_seconds: settings.lambda_timeout_seconds,
          emr_timeout_minutes: settings.emr_timeout_minutes,
        },
      };
      const res = await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await res.json();
      setMessage(result.success
        ? { type: 'success', content: 'Settings saved' }
        : { type: 'error', content: result.error || 'Save failed' });
    } catch (e) { setMessage({ type: 'error', content: 'Failed to save' }); }
    setLoading(false);
  };

  const field = (label, key, desc, placeholder, type) => (
    <FormField label={label} description={desc}>
      {type === 'number' ? (
        <Input type="number" value={String(settings[key])}
          onChange={({ detail }) => setSettings(p => ({ ...p, [key]: parseInt(detail.value) || 0 }))}
          placeholder={placeholder} />
      ) : (
        <Input value={settings[key]}
          onChange={({ detail }) => setSettings(p => ({ ...p, [key]: detail.value }))}
          placeholder={placeholder} />
      )}
    </FormField>
  );

  return (
    <Container header={<Header variant="h2">Settings</Header>}>
      <SpaceBetween size="l">
        {message && <Alert type={message.type} dismissible onDismiss={() => setMessage(null)}>{message.content}</Alert>}
        <Form>
          <SpaceBetween size="l">
            <ExpandableSection headerText="Model Configuration" defaultExpanded>
              <SpaceBetween size="m">
                <FormField label="Bedrock Model" description="Claude model for code generation">
                  <Select
                    selectedOption={claudeModels.find(m => m.value === settings.bedrock_model) || null}
                    onChange={({ detail }) => setSettings(p => ({ ...p, bedrock_model: detail.selectedOption.value }))}
                    options={claudeModels} placeholder="Select model" />
                </FormField>
                {field('Code Generation Agent ARN', 'code_gen_agent_arn', 'AgentCore runtime for code generation', 'arn:aws:bedrock-agentcore:...')}
                {field('Bedrock Region', 'bedrock_region', 'AWS region', 'us-east-1')}
              </SpaceBetween>
            </ExpandableSection>

            <ExpandableSection headerText="Spark Configuration" defaultExpanded>
              <SpaceBetween size="m">
                {field('Supervisor Agent ARN', 'supervisor_arn', 'Spark Supervisor Agent on AgentCore', 'arn:aws:bedrock-agentcore:...')}
                {field('S3 Bucket', 's3_bucket', 'S3 bucket for data and results', 'spark-data-...')}
                {field('Lambda Function', 'lambda_function', 'Spark-on-Lambda function name', 'dev-spark-on-lambda')}
                {field('EMR Application ID', 'emr_application_id', 'EMR Serverless application', '00g3oapr87misc09')}
              </SpaceBetween>
            </ExpandableSection>

            <ExpandableSection headerText="Execution Tuning">
              <SpaceBetween size="m">
                {field('Max Retries', 'max_retries', 'Retry attempts for failed code generation', '3', 'number')}
                {field('File Size Threshold (MB)', 'file_size_threshold_mb', 'Lambda vs EMR auto-selection threshold', '100', 'number')}
                {field('Result Preview Rows', 'result_preview_rows', 'Max rows shown in results', '100', 'number')}
                {field('Presigned URL Expiry (Hours)', 'presigned_url_expiry_hours', 'S3 download link expiry', '24', 'number')}
                {field('Lambda Timeout (Seconds)', 'lambda_timeout_seconds', 'Spark Lambda timeout', '300', 'number')}
                {field('EMR Timeout (Minutes)', 'emr_timeout_minutes', 'EMR job timeout', '10', 'number')}
              </SpaceBetween>
            </ExpandableSection>

            <Button variant="primary" loading={loading} onClick={saveSettings}>Save Settings</Button>
          </SpaceBetween>
        </Form>
      </SpaceBetween>
    </Container>
  );
};

export default Settings;
