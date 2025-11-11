import React, { useState, useEffect } from 'react';
import { Container, Header, Box, SpaceBetween, Tabs, Button } from '@cloudscape-design/components';

const RayDashboard = ({ dashboardUrl, jobId, onCloseJobLogs }) => {
  const [logs, setLogs] = useState('');
  const [loadingLogs, setLoadingLogs] = useState(false);

  useEffect(() => {
    if (jobId) {
      loadJobLogs();
    }
  }, [jobId]);

  const loadJobLogs = async () => {
    try {
      setLoadingLogs(true);
      const response = await fetch(`http://localhost:8000/ray/jobs/${jobId}/logs`);
      const data = await response.json();
      setLogs(data.logs || 'No logs available');
    } catch (err) {
      setLogs('Failed to load logs');
    } finally {
      setLoadingLogs(false);
    }
  };

  if (!dashboardUrl) {
    return (
      <Container header={<Header variant="h2">Ray Dashboard</Header>}>
        <Box textAlign="center" color="text-body-secondary" padding="xxl">
          Ray cluster not connected
        </Box>
      </Container>
    );
  }

  const tabs = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      content: (
        <Box>
          <iframe
            src={dashboardUrl}
            style={{
              width: '100%',
              height: '800px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }}
            title="Ray Dashboard"
          />
        </Box>
      )
    }
  ];

  if (jobId) {
    tabs.push({
      id: 'logs',
      label: `Job ${jobId} Logs`,
      content: (
        <SpaceBetween size="m">
          <Box float="right">
            <Button onClick={onCloseJobLogs}>Close Logs</Button>
          </Box>
          <Box>
            <pre style={{
              backgroundColor: '#232f3e',
              color: '#ffffff',
              padding: '16px',
              borderRadius: '4px',
              maxHeight: '800px',
              overflow: 'auto',
              fontSize: '12px',
              fontFamily: 'monospace'
            }}>
              {loadingLogs ? 'Loading logs...' : logs}
            </pre>
          </Box>
        </SpaceBetween>
      )
    });
  }

  return (
    <Container header={<Header variant="h2">Ray Dashboard</Header>}>
      <Tabs tabs={tabs} />
    </Container>
  );
};

export default RayDashboard;
