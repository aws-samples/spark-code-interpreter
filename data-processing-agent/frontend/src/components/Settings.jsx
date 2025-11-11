import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  Form,
  FormField,
  Input,
  Button,
  SpaceBetween,
  Alert,
  ExpandableSection,
  Select
} from '@cloudscape-design/components';

const Settings = () => {
  const [settings, setSettings] = useState({
    ray_private_ip: '',
    ray_public_ip: '',
    s3_bucket: '',
    ray_gateway_url: '',
    ray_supervisor_arn: '',
    global_bedrock_model: '',
    global_code_gen_agent_arn: '',
    global_bedrock_region: '',
    spark_s3_bucket: '',
    spark_lambda_function: '',
    spark_emr_application_id: '',
    spark_bedrock_region: '',
    spark_max_retries: 3,
    spark_file_size_threshold_mb: 100,
    spark_result_preview_rows: 100,
    spark_presigned_url_expiry_hours: 24,
    spark_lambda_timeout_seconds: 300,
    spark_emr_timeout_minutes: 10,
    spark_supervisor_arn: ''
  });
  const [claudeModels, setClaudeModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [restoreLoading, setRestoreLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
    loadClaudeModels();
  }, []);

  const loadClaudeModels = async () => {
    try {
      const response = await fetch('http://localhost:8000/claude-models');
      const data = await response.json();
      setClaudeModels(data.models.map(model => ({ label: model.name, value: model.id })));
    } catch (error) {
      console.error('Failed to load Claude models:', error);
    }
  };

  const loadSettings = async () => {
    try {
      const response = await fetch('http://localhost:8000/settings');
      const data = await response.json();
      setSettings({
        ray_private_ip: data.ray_cluster?.private_ip || '',
        ray_public_ip: data.ray_cluster?.public_ip || '',
        s3_bucket: data.s3?.bucket || '',
        ray_gateway_url: data.ray?.gateway_url || '',
        ray_supervisor_arn: data.ray?.supervisor_arn || '',
        global_bedrock_model: data.global?.bedrock_model || '',
        global_code_gen_agent_arn: data.global?.code_gen_agent_arn || '',
        global_bedrock_region: data.global?.bedrock_region || '',
        spark_s3_bucket: data.spark?.s3_bucket || '',
        spark_lambda_function: data.spark?.lambda_function || '',
        spark_emr_application_id: data.spark?.emr_application_id || '',
        spark_max_retries: data.spark?.max_retries || 3,
        spark_file_size_threshold_mb: data.spark?.file_size_threshold_mb || 100,
        spark_result_preview_rows: data.spark?.result_preview_rows || 100,
        spark_presigned_url_expiry_hours: data.spark?.presigned_url_expiry_hours || 24,
        spark_lambda_timeout_seconds: data.spark?.lambda_timeout_seconds || 300,
        spark_emr_timeout_minutes: data.spark?.emr_timeout_minutes || 10,
        spark_supervisor_arn: data.spark?.supervisor_arn || ''
      });
    } catch (error) {
      setMessage({ type: 'error', content: 'Failed to load settings' });
    }
  };

  const saveSettings = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      const result = await response.json();
      
      if (result.success) {
        setMessage({ type: 'success', content: 'Settings saved successfully' });
      } else {
        setMessage({ type: 'error', content: result.error || 'Failed to save settings' });
      }
    } catch (error) {
      setMessage({ type: 'error', content: 'Failed to save settings' });
    }
    setLoading(false);
  };

  const restoreDefaults = async () => {
    setRestoreLoading(true);
    try {
      const response = await fetch('http://localhost:8000/settings/restore-defaults', {
        method: 'POST'
      });
      const result = await response.json();
      
      if (result.success) {
        setMessage({ type: 'success', content: 'Settings restored to defaults' });
        await loadSettings(); // Reload settings from server
      } else {
        setMessage({ type: 'error', content: result.error || 'Failed to restore defaults' });
      }
    } catch (error) {
      setMessage({ type: 'error', content: 'Failed to restore defaults' });
    }
    setRestoreLoading(false);
  };

  return (
    <Container header={<Header variant="h2">Settings</Header>}>
      <SpaceBetween size="l">
        {message && (
          <Alert type={message.type} dismissible onDismiss={() => setMessage(null)}>
            {message.content}
          </Alert>
        )}
        
        <Form>
          <SpaceBetween size="l">
            <ExpandableSection headerText="Global Settings" defaultExpanded>
              <SpaceBetween size="m">
                <FormField label="Bedrock Model" description="Claude or Nova model for code generation">
                  <Select
                    selectedOption={claudeModels.find(model => model.value === settings.global_bedrock_model) || null}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, global_bedrock_model: detail.selectedOption.value }))}
                    options={claudeModels}
                    placeholder="Select model"
                  />
                </FormField>
                
                <FormField label="Code Generation Agent ARN" description="ARN of the code generation agent">
                  <Input
                    value={settings.global_code_gen_agent_arn}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, global_code_gen_agent_arn: detail.value }))}
                    placeholder="arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9"
                  />
                </FormField>
                
                <FormField label="Bedrock Region" description="AWS region for Bedrock services">
                  <Input
                    value={settings.global_bedrock_region}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, global_bedrock_region: detail.value }))}
                    placeholder="us-east-1"
                  />
                </FormField>
              </SpaceBetween>
            </ExpandableSection>

            <ExpandableSection headerText="Ray Settings" defaultExpanded>
              <SpaceBetween size="m">
                <FormField label="Ray Cluster Private IP" description="Internal IP for Ray cluster communication">
                  <Input
                    value={settings.ray_private_ip}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, ray_private_ip: detail.value }))}
                    placeholder="172.31.4.12"
                  />
                </FormField>
                
                <FormField label="Ray Cluster Public IP" description="External IP for Ray dashboard access">
                  <Input
                    value={settings.ray_public_ip}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, ray_public_ip: detail.value }))}
                    placeholder="100.27.32.218"
                  />
                </FormField>
                
                <FormField label="S3 Bucket" description="S3 bucket for CSV file uploads">
                  <Input
                    value={settings.s3_bucket}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, s3_bucket: detail.value }))}
                    placeholder="strands-ray-data"
                  />
                </FormField>
                
                <FormField label="Gateway URL" description="MCP Gateway URL for Ray execution">
                  <Input
                    value={settings.ray_gateway_url}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, ray_gateway_url: detail.value }))}
                    placeholder="https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
                  />
                </FormField>
                
                <FormField label="Supervisor Agent ARN" description="ARN of the Ray supervisor agent">
                  <Input
                    value={settings.ray_supervisor_arn}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, ray_supervisor_arn: detail.value }))}
                    placeholder="arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky"
                  />
                </FormField>
              </SpaceBetween>
            </ExpandableSection>

            <ExpandableSection headerText="Spark Settings" defaultExpanded>
              <SpaceBetween size="m">
                <FormField label="Spark S3 Bucket" description="S3 bucket for Spark data processing">
                  <Input
                    value={settings.spark_s3_bucket}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_s3_bucket: detail.value }))}
                    placeholder="spark-data-260005718447-us-east-1"
                  />
                </FormField>
                
                <FormField label="Lambda Function" description="Lambda function name for Spark execution">
                  <Input
                    value={settings.spark_lambda_function}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_lambda_function: detail.value }))}
                    placeholder="sparkOnLambda-spark-code-interpreter"
                  />
                </FormField>
                
                <FormField label="EMR Application ID" description="EMR Serverless application ID">
                  <Input
                    value={settings.spark_emr_application_id}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_emr_application_id: detail.value }))}
                    placeholder="00fv6g7rptsov009"
                  />
                </FormField>
                
                <FormField label="Max Retries" description="Maximum retry attempts for failed executions">
                  <Input
                    type="number"
                    value={settings.spark_max_retries.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_max_retries: parseInt(detail.value) || 3 }))}
                    placeholder="3"
                  />
                </FormField>
                
                <FormField label="File Size Threshold (MB)" description="File size threshold for Lambda vs EMR selection">
                  <Input
                    type="number"
                    value={settings.spark_file_size_threshold_mb.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_file_size_threshold_mb: parseInt(detail.value) || 100 }))}
                    placeholder="100"
                  />
                </FormField>
                
                <FormField label="Result Preview Rows" description="Number of rows to preview in results">
                  <Input
                    type="number"
                    value={settings.spark_result_preview_rows.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_result_preview_rows: parseInt(detail.value) || 100 }))}
                    placeholder="100"
                  />
                </FormField>
                
                <FormField label="Presigned URL Expiry (Hours)" description="Hours until presigned URLs expire">
                  <Input
                    type="number"
                    value={settings.spark_presigned_url_expiry_hours.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_presigned_url_expiry_hours: parseInt(detail.value) || 24 }))}
                    placeholder="24"
                  />
                </FormField>
                
                <FormField label="Lambda Timeout (Seconds)" description="Lambda function timeout in seconds">
                  <Input
                    type="number"
                    value={settings.spark_lambda_timeout_seconds.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_lambda_timeout_seconds: parseInt(detail.value) || 300 }))}
                    placeholder="300"
                  />
                </FormField>
                
                <FormField label="EMR Timeout (Minutes)" description="EMR job timeout in minutes">
                  <Input
                    type="number"
                    value={settings.spark_emr_timeout_minutes.toString()}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_emr_timeout_minutes: parseInt(detail.value) || 10 }))}
                    placeholder="10"
                  />
                </FormField>
                
                <FormField label="Supervisor Agent ARN" description="ARN of the Spark supervisor agent">
                  <Input
                    value={settings.spark_supervisor_arn}
                    onChange={({ detail }) => setSettings(prev => ({ ...prev, spark_supervisor_arn: detail.value }))}
                    placeholder="arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
                  />
                </FormField>
              </SpaceBetween>
            </ExpandableSection>
            
            <SpaceBetween size="m" direction="horizontal">
              <Button variant="primary" loading={loading} onClick={saveSettings}>
                Save Settings
              </Button>
              <Button loading={restoreLoading} onClick={restoreDefaults}>
                Restore Defaults
              </Button>
            </SpaceBetween>
          </SpaceBetween>
        </Form>
      </SpaceBetween>
    </Container>
  );
};

export default Settings;
