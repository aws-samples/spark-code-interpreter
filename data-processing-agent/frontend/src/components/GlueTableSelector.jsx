import React, { useState, useEffect } from 'react';
import { Container, Header, SpaceBetween, Select, Multiselect, Button, Box, Badge } from '@cloudscape-design/components';

const GlueTableSelector = ({ sessionId, onTablesSelected }) => {
  const [databases, setDatabases] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(null);
  const [tables, setTables] = useState([]);
  const [selectedTables, setSelectedTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDatabases();
  }, []);

  const loadDatabases = async () => {
    try {
      setLoading(true);
      console.log('Loading databases from:', 'http://localhost:8000/glue/databases');
      const response = await fetch('http://localhost:8000/glue/databases');
      const data = await response.json();
      console.log('Databases response:', data);
      if (data.success) {
        const dbOptions = data.databases.map(db => ({ label: db, value: db }));
        console.log('Database options:', dbOptions);
        setDatabases(dbOptions);
      }
    } catch (err) {
      console.error('Failed to load databases:', err);
      setError('Failed to load databases');
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async (database) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/glue/tables/${database}`);
      const data = await response.json();
      if (data.success) {
        setTables(data.tables.map(t => ({
          label: t.name,
          value: t.name,
          description: t.location,
          tags: t.columns.map(c => `${c.name}: ${c.type}`).slice(0, 3)
        })));
      }
    } catch (err) {
      setError('Failed to load tables');
    } finally {
      setLoading(false);
    }
  };

  const handleDatabaseChange = ({ detail }) => {
    setSelectedDatabase(detail.selectedOption);
    setSelectedTables([]);
    if (detail.selectedOption) {
      loadTables(detail.selectedOption.value);
    } else {
      setTables([]);
    }
  };

  const handleApply = async () => {
    if (selectedTables.length === 0) {
      return;
    }

    try {
      setLoading(true);
      const tableRefs = selectedTables.map(t => ({
        database: selectedDatabase.value,
        table: t.value
      }));

      const response = await fetch(`http://localhost:8000/sessions/${sessionId}/select-tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: tableRefs, session_id: sessionId })
      });

      const data = await response.json();
      if (data.success) {
        onTablesSelected && onTablesSelected(data.selected_tables);
      }
    } catch (err) {
      setError('Failed to select tables');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container
      header={
        <Header variant="h3">
          Glue Data Catalog
        </Header>
      }
    >
      <SpaceBetween size="m">
        <Select
          selectedOption={selectedDatabase}
          onChange={handleDatabaseChange}
          options={databases}
          placeholder="Select database"
          loadingText="Loading databases..."
          statusType={loading ? "loading" : "finished"}
          empty="No databases found"
        />

        {selectedDatabase && (
          <Multiselect
            selectedOptions={selectedTables}
            onChange={({ detail }) => setSelectedTables(detail.selectedOptions)}
            options={tables}
            placeholder="Select tables"
            loadingText="Loading tables..."
            statusType={loading ? "loading" : "finished"}
            empty="No tables found"
          />
        )}

        {selectedTables.length > 0 && (
          <Box>
            <SpaceBetween direction="horizontal" size="xs">
              <Badge color="blue">{selectedTables.length} table(s) selected</Badge>
              <Button onClick={handleApply} loading={loading}>
                Apply Selection
              </Button>
            </SpaceBetween>
          </Box>
        )}

        {error && (
          <Box color="text-status-error">{error}</Box>
        )}
      </SpaceBetween>
    </Container>
  );
};

export default GlueTableSelector;
