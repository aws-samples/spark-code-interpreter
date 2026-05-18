import React, { useState, useEffect } from 'react';
import { Container, Header, SpaceBetween, Select, Multiselect, Button, Box, Badge, Table, Tabs } from '@cloudscape-design/components';

const GlueTableSelector = ({ sessionId, onTablesSelected }) => {
  const [databases, setDatabases] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(null);
  const [tables, setTables] = useState([]);
  const [selectedTables, setSelectedTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tablePreviews, setTablePreviews] = useState([]);  // [{table, columns, sample_rows}]
  const [activePreviewTab, setActivePreviewTab] = useState(null);

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
      if (data.databases && data.databases.length > 0) {
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
      if (data.tables && data.tables.length > 0) {
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
    if (selectedTables.length === 0) return;

    try {
      setLoading(true);
      setTablePreviews([]);
      const db = selectedDatabase.value;
      const tableRefs = selectedTables.map(t => ({ database: db, table: t.value }));

      // Register selection with backend
      const response = await fetch(`http://localhost:8000/sessions/${sessionId}/select-tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables: tableRefs, session_id: sessionId })
      });
      const data = await response.json();

      if (data.success) {
        // Fetch schema + sample rows for each selected table in parallel
        const previews = await Promise.all(
          tableRefs.map(t =>
            fetch(`http://localhost:8000/glue/tables/${t.database}/${t.table}/sample?rows=5`)
              .then(r => r.json())
              .catch(() => ({ table: t.table, columns: [], sample_rows: [] }))
          )
        );
        setTablePreviews(previews);
        setActivePreviewTab(previews[0]?.table || null);
        onTablesSelected && onTablesSelected(tableRefs, previews);
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

        {tablePreviews.length > 0 && (
          <Box>
            <Tabs
              activeTabId={activePreviewTab}
              onChange={({ detail }) => setActivePreviewTab(detail.activeTabId)}
              tabs={tablePreviews.map(p => ({
                id: p.table,
                label: p.table,
                content: (
                  <SpaceBetween size="s">
                    {/* Schema */}
                    <Box>
                      <Box variant="awsui-key-label">Schema ({p.columns.length} columns)</Box>
                      <Table
                        columnDefinitions={[
                          { id: 'name', header: 'Column', cell: c => c.name },
                          { id: 'type', header: 'Type',   cell: c => <Badge color="grey">{c.type}</Badge> },
                        ]}
                        items={p.columns}
                        variant="embedded"
                        stripedRows
                      />
                    </Box>
                    {/* Sample rows */}
                    {p.sample_rows.length > 0 ? (
                      <Box>
                        <Box variant="awsui-key-label">Sample rows (first {p.sample_rows.length})</Box>
                        <div style={{ overflowX: 'auto' }}>
                          <Table
                            columnDefinitions={Object.keys(p.sample_rows[0]).map(k => ({
                              id: k, header: k, cell: item => String(item[k] ?? ''),
                            }))}
                            items={p.sample_rows}
                            variant="embedded"
                            stripedRows
                          />
                        </div>
                      </Box>
                    ) : (
                      <Box color="text-body-secondary" variant="small">
                        Sample rows unavailable — table may use a non-CSV format or S3 access is restricted.
                      </Box>
                    )}
                    <Box variant="small" color="text-body-secondary">
                      Location: {p.location}
                    </Box>
                  </SpaceBetween>
                )
              }))}
            />
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
