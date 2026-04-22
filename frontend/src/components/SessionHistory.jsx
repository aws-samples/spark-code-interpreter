import React from 'react';
import { Container, Header, SpaceBetween, Box, Table, Badge, Link, Button, Modal } from '@cloudscape-design/components';

const SessionHistory = ({ sessionId, history, onRefresh, onExecuteCode }) => {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [selectedItem, setSelectedItem] = React.useState(null);
  const [showModal, setShowModal] = React.useState(false);
  const [copySuccess, setCopySuccess] = React.useState(false);
  const hasLoadedRef = React.useRef(false);

  const handleCopyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const handleRefresh = async () => {
    if (onRefresh && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
  };

  React.useEffect(() => {
    if (sessionId && !history && onRefresh && !hasLoadedRef.current) {
      hasLoadedRef.current = true;
      handleRefresh();
    }
  }, [sessionId]);

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const executionColumns = [
    {
      id: 'timestamp',
      header: 'Executed At',
      cell: item => formatTimestamp(item.timestamp),
      width: 180
    },
    {
      id: 'result',
      header: 'Status',
      cell: item => (
        <Badge color={item.success ? "green" : "red"}>
          {item.success ? "Success" : "Failed"}
        </Badge>
      ),
      width: 100
    },
    {
      id: 'output',
      header: 'Output Preview',
      cell: item => (
        <Box fontSize="body-s">
          {item.result ? (
            item.result.split('\n')[0].substring(0, 60) + (item.result.length > 60 ? '...' : '')
          ) : 'No output'}
        </Box>
      )
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <SpaceBetween direction="horizontal" size="xs">
          <Link onFollow={() => {
            setSelectedItem({ ...item, type: 'execution' });
            setShowModal(true);
          }}>
            View Details
          </Link>
          <Button size="small" onClick={() => onExecuteCode && onExecuteCode(item.code)}>
            Re-execute
          </Button>
        </SpaceBetween>
      ),
      width: 200
    }
  ];

  const conversationColumns = [
    {
      id: 'timestamp',
      header: 'Time',
      cell: item => formatTimestamp(item.timestamp),
      width: 180
    },
    {
      id: 'type',
      header: 'Type',
      cell: item => <Badge color="blue">Code Generated</Badge>,
      width: 140
    },
    {
      id: 'prompt',
      header: 'Prompt',
      cell: item => (
        <Box fontSize="body-s">
          {item.prompt.length > 60 ? `${item.prompt.substring(0, 60)}...` : item.prompt}
        </Box>
      )
    },
    {
      id: 'iterations',
      header: 'Iterations',
      cell: item => <Box fontSize="body-s">{item.iterations || 1}</Box>,
      width: 100
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <SpaceBetween direction="horizontal" size="xs">
          <Link onFollow={() => {
            setSelectedItem({ ...item, type: 'generation' });
            setShowModal(true);
          }}>
            View Code
          </Link>
          <Button size="small" onClick={() => onExecuteCode && onExecuteCode(item.generated_code)}>
            Execute
          </Button>
        </SpaceBetween>
      ),
      width: 200
    }
  ];

  if (!history) {
    return (
      <Container header={<Header variant="h2">Session History</Header>}>
        <Box textAlign="center" color="text-body-secondary" padding="xxl">
          Loading session history...
        </Box>
      </Container>
    );
  }

  return (
    <>
      <Container 
        header={
          <Header 
            variant="h2"
            actions={
              <Button 
                onClick={handleRefresh}
                loading={isRefreshing}
                iconName="refresh"
              >
                Refresh
              </Button>
            }
          >
            Session History
          </Header>
        }
      >
        <SpaceBetween size="l">
          <Container header={<Header variant="h3">Execution History</Header>}>
            {history.execution_results && history.execution_results.length > 0 ? (
              <Table
                columnDefinitions={executionColumns}
                items={history.execution_results.sort((a, b) => b.timestamp - a.timestamp)}
                empty={
                  <Box textAlign="center" color="text-body-secondary">
                    No execution history
                  </Box>
                }
              />
            ) : (
              <Box textAlign="center" color="text-body-secondary" padding="l">
                No code has been executed yet
              </Box>
            )}
          </Container>

          <Container header={<Header variant="h3">Code Generation History</Header>}>
            {history.conversation_history && history.conversation_history.length > 0 ? (
              <Table
                columnDefinitions={conversationColumns}
                items={history.conversation_history.sort((a, b) => b.timestamp - a.timestamp)}
                empty={
                  <Box textAlign="center" color="text-body-secondary">
                    No generation history
                  </Box>
                }
              />
            ) : (
              <Box textAlign="center" color="text-body-secondary" padding="l">
                No code has been generated yet
              </Box>
            )}
          </Container>
        </SpaceBetween>
      </Container>

      <Modal
        visible={showModal}
        onDismiss={() => setShowModal(false)}
        header={selectedItem?.type === 'execution' ? 'Execution Details' : 'Generated Code'}
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={() => setShowModal(false)}>Close</Button>
              <Button 
                variant="primary" 
                onClick={() => {
                  const code = selectedItem?.type === 'execution' ? selectedItem.code : selectedItem.generated_code;
                  onExecuteCode && onExecuteCode(code);
                  setShowModal(false);
                }}
              >
                {selectedItem?.type === 'execution' ? 'Re-execute' : 'Execute'}
              </Button>
            </SpaceBetween>
          </Box>
        }
        size="large"
      >
        {selectedItem && (
          <SpaceBetween size="m">
            {selectedItem.prompt && (
              <Box>
                <Box variant="awsui-key-label">Prompt</Box>
                <Box padding={{ top: 'xs' }}>{selectedItem.prompt}</Box>
              </Box>
            )}
            
            {selectedItem.iterations && (
              <Box>
                <Box variant="awsui-key-label">Iterations</Box>
                <Box padding={{ top: 'xs' }}>{selectedItem.iterations}</Box>
              </Box>
            )}

            <Box>
              <SpaceBetween direction="horizontal" size="s" alignItems="center">
                <Box variant="awsui-key-label">Code</Box>
                <Button
                  size="small"
                  iconName={copySuccess ? "check" : "copy"}
                  onClick={() => {
                    const code = selectedItem.type === 'execution' ? selectedItem.code : selectedItem.generated_code;
                    handleCopyCode(code);
                  }}
                >
                  {copySuccess ? 'Copied!' : 'Copy'}
                </Button>
              </SpaceBetween>
              <pre style={{
                backgroundColor: '#f5f5f5',
                padding: '16px',
                borderRadius: '4px',
                overflow: 'auto',
                maxHeight: '400px',
                fontFamily: 'Monaco, Menlo, monospace',
                fontSize: '13px',
                lineHeight: '1.5'
              }}>
                {selectedItem.type === 'execution' ? selectedItem.code : selectedItem.generated_code}
              </pre>
            </Box>

            {selectedItem.result && (
              <Box>
                <Box variant="awsui-key-label">Execution Result</Box>
                <pre style={{
                  backgroundColor: '#f5f5f5',
                  padding: '16px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '300px',
                  fontFamily: 'Monaco, Menlo, monospace',
                  fontSize: '13px',
                  lineHeight: '1.5',
                  whiteSpace: 'pre-wrap'
                }}>
                  {selectedItem.result}
                </pre>
              </Box>
            )}
          </SpaceBetween>
        )}
      </Modal>
    </>
  );
};

export default SessionHistory;
