import React from 'react';
import { Container, Header, SpaceBetween, Box, Badge, Table } from '@cloudscape-design/components';

const ExecutionResults = ({ result }) => {
  if (!result) {
    return (
      <Container header={<Header variant="h2">Execution Results</Header>}>
        <Box textAlign="center" color="text-body-secondary" padding="xxl">
          No execution results yet. Run some code to see results here.
        </Box>
      </Container>
    );
  }

  // Try to parse and format the output
  const formatOutput = (output) => {
    // Safety check for undefined/null output
    if (!output) {
      return (
        <Box>
          <Box variant="h3" padding={{ bottom: 's' }}>Output:</Box>
          <Box color="text-body-secondary">No output available</Box>
        </Box>
      );
    }
    
    // If output is already an array of objects, format as table
    if (Array.isArray(output) && output.length > 0 && typeof output[0] === 'object') {
      const columns = Object.keys(output[0]).map(key => ({
        id: key,
        header: key,
        cell: item => String(item[key] ?? '')
      }));
      
      return (
        <Box>
          <Box variant="h3" padding={{ bottom: 's' }}>Data Results:</Box>
          <Table
            columnDefinitions={columns}
            items={output}
            variant="embedded"
          />
          <Box variant="small" padding={{ top: 's' }}>
            Showing {output.length} rows
          </Box>
        </Box>
      );
    }
    
    // Convert to string if not already
    const outputStr = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
    
    // Try to parse string as JSON array
    try {
      const parsed = JSON.parse(outputStr);
      if (Array.isArray(parsed) && parsed.length > 0 && typeof parsed[0] === 'object') {
        const columns = Object.keys(parsed[0]).map(key => ({
          id: key,
          header: key,
          cell: item => String(item[key] ?? '')
        }));
        
        return (
          <Box>
            <Box variant="h3" padding={{ bottom: 's' }}>Data Results:</Box>
            <Table
              columnDefinitions={columns}
              items={parsed}
              variant="embedded"
            />
            <Box variant="small" padding={{ top: 's' }}>
              Showing {parsed.length} rows
            </Box>
          </Box>
        );
      }
    } catch (e) {
      // Not valid JSON, continue to plain text
    }
    
    // Format plain text with better styling
    return (
      <Box>
        <Box variant="h3" padding={{ bottom: 's' }}>Output:</Box>
        <pre style={{
          backgroundColor: '#f5f5f5',
          padding: '16px',
          borderRadius: '4px',
          overflow: 'auto',
          maxHeight: '500px',
          fontFamily: 'Monaco, Menlo, monospace',
          fontSize: '13px',
          lineHeight: '1.6',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {outputStr}
        </pre>
      </Box>
    );
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          info={
            <Badge color={result.success ? 'green' : 'red'}>
              {result.success ? 'Success' : 'Failed'}
            </Badge>
          }
        >
          Execution Results
        </Header>
      }
    >
      <SpaceBetween size="l">
        {result.job_id && (
          <Box variant="small">Job ID: {result.job_id}</Box>
        )}
        
        {result.execution_output && result.execution_output.length > 0 && (
          <Box>
            <Box variant="h3" padding={{ bottom: 's' }}>Execution Output:</Box>
            <pre style={{
              backgroundColor: '#f5f5f5',
              padding: '16px',
              borderRadius: '4px',
              overflow: 'auto',
              maxHeight: '300px',
              fontFamily: 'Monaco, Menlo, monospace',
              fontSize: '13px',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {result.execution_output.join('\n')}
            </pre>
          </Box>
        )}
        
        {formatOutput(result.result)}

        <Box variant="small" color="text-body-secondary">
          Executed at: {new Date(result.timestamp).toLocaleString()}
        </Box>
      </SpaceBetween>
    </Container>
  );
};

export default ExecutionResults;
