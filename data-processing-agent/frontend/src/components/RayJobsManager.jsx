import React, { useState, useEffect } from 'react';
import { Container, Header, SpaceBetween, Select, Button, Box } from '@cloudscape-design/components';

const RayJobsManager = ({ onViewDetails }) => {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const abortControllerRef = React.useRef(null);

  const loadJobs = async () => {
    try {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      abortControllerRef.current = new AbortController();
      setRefreshing(true);
      
      const response = await fetch('http://localhost:8000/ray/jobs', {
        signal: abortControllerRef.current.signal
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success || !Array.isArray(data.jobs)) {
        console.error('Invalid response:', data);
        return;
      }
      
      const allJobs = data.jobs
        .filter(j => j.submission_id && j.status && j.start_time && j.status.toUpperCase() === 'RUNNING')
        .sort((a, b) => b.start_time - a.start_time)
        .map(j => ({
          label: `${j.submission_id.substring(10)}... - ${j.status}`,
          value: j.submission_id,
          description: `Started: ${new Date(j.start_time).toLocaleTimeString()}`
        }));
      
      setJobs(allJobs);
      console.log(`Loaded ${allJobs.length} jobs`);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Failed to load jobs:', err);
      }
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadJobs();
    
    const interval = setInterval(loadJobs, 2000);
    
    const handleVisibilityChange = () => {
      if (document.hidden) {
        clearInterval(interval);
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    console.log('RayJobsManager: jobs state updated', { count: jobs.length, jobs });
  }, [jobs]);

  const handleStopJob = async () => {
    if (!selectedJob) return;
    
    try {
      setLoading(true);
      await fetch(`http://localhost:8000/ray/jobs/${selectedJob.value}/stop`, {
        method: 'POST'
      });
      setSelectedJob(null);
      await loadJobs();
    } catch (err) {
      console.error('Failed to stop job:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = () => {
    if (selectedJob && onViewDetails) {
      onViewDetails(selectedJob.value);
    }
  };

  return (
    <Container
      header={
        <Header variant="h3">
          Running Jobs
        </Header>
      }
    >
      <SpaceBetween size="m">
        <Box>
          <Box variant="awsui-key-label" margin={{ bottom: 'xxxs' }}>
            {jobs.length} running
          </Box>
          <Select
            selectedOption={selectedJob}
            onChange={({ detail }) => setSelectedJob(detail.selectedOption)}
            options={jobs}
            placeholder={jobs.length > 0 ? "Select a job" : "No jobs available"}
            loadingText="Loading jobs..."
            statusType={refreshing ? "loading" : "finished"}
            empty="No jobs found"
            filteringType="auto"
          />
        </Box>

        {selectedJob && (
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              onClick={handleStopJob}
              loading={loading}
            >
              Stop Job
            </Button>
            <Button
              variant="primary"
              onClick={handleViewDetails}
            >
              View Details
            </Button>
          </SpaceBetween>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default RayJobsManager;
