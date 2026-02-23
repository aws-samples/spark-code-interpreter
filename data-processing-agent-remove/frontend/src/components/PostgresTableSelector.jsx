import React, { useState, useEffect } from 'react';
import { Container, Header, SpaceBetween, Select, Multiselect, Button, Box, Badge } from '@cloudscape-design/components';

const PostgresTableSelector = ({ sessionId, connection, onTablesSelected, onDisconnect, onConfigure }) => {
  const [databases, setDatabases] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(null);
  const [schemas, setSchemas] = useState([]);
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [tables, setTables] = useState([]);
  const [selectedTables, setSelectedTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (connection) {
      loadDatabases();
    }
  }, [connection]);

  const loadDatabases = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/postgres/${connection.name}/databases`);
      const data = await response.json();
      if (data.success) {
        setDatabases(data.databases.map(db => ({ label: db, value: db })));
      } else {
        setError(data.error || 'Failed to load databases');
      }
    } catch (err) {
      setError('Failed to load databases');
    } finally {
      setLoading(false);
    }
  };

  const loadSchemas = async (database) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/postgres/${connection.name}/schemas/${database}`);
      const data = await response.json();
      if (data.success) {
        setSchemas(data.schemas.map(s => ({ label: s, value: s })));
      } else {
        setError(data.error || 'Failed to load schemas');
      }
    } catch (err) {
      setError('Failed to load schemas');
    } finally {
      setLoading(false);
    }
  };

  const loadTables = async (database, schema) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/postgres/${connection.name}/tables/${database}/${schema}`);
      const data = await response.json();
      if (data.success) {
        setTables(data.tables.map(t => ({
          label: t.name,
          value: t.name,
          description: `${t.columns.length} columns`,
          tags: t.columns.map(c => `${c.name}: ${c.type}`).slice(0, 3)
        })));
      } else {
        setError(data.error || 'Failed to load tables');
      }
    } catch (err) {
      setError('Failed to load tables');
    } finally {
      setLoading(false);
    }
  };

  const handleDatabaseChange = ({ detail }) => {
    setSelectedDatabase(detail.selectedOption);
    setSelectedSchema(null);
    setSelectedTables([]);
    setSchemas([]);
    setTables([]);
    if (detail.selectedOption) {
      loadSchemas(detail.selectedOption.value);
    }
  };

  const handleSchemaChange = ({ detail }) => {
    setSelectedSchema(detail.selectedOption);
    setSelectedTables([]);
    setTables([]);
    if (detail.selectedOption && selectedDatabase) {
      loadTables(selectedDatabase.value, detail.selectedOption.value);
    }
  };

  const handleApply = async () => {
    if (selectedTables.length === 0) return;

    try {
      setLoading(true);
      const tableRefs = selectedTables.map(t => ({
        database: selectedDatabase.value,
        schema: selectedSchema.value,
        table: t.value
      }));

      const response = await fetch(`http://localhost:8000/sessions/${sessionId}/select-postgres-tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_name: connection.name,
          tables: tableRefs
        })
      });

      const data = await response.json();
      if (data.success) {
        onTablesSelected && onTablesSelected(data.selected_tables);
      } else {
        setError(data.error || 'Failed to select tables');
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
        <Header
          variant="h3"
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={onConfigure} iconName="settings">
                Configure
              </Button>
              <Button onClick={onDisconnect} iconName="close">
                Disconnect
              </Button>
            </SpaceBetween>
          }
        >
          PostgreSQL: {connection.name}
        </Header>
      }
    >
      <SpaceBetween size="m">
        <Box variant="small" color="text-body-secondary">
          {connection.description}
        </Box>

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
          <Select
            selectedOption={selectedSchema}
            onChange={handleSchemaChange}
            options={schemas}
            placeholder="Select schema"
            loadingText="Loading schemas..."
            statusType={loading ? "loading" : "finished"}
            empty="No schemas found"
          />
        )}

        {selectedSchema && (
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

export default PostgresTableSelector;
