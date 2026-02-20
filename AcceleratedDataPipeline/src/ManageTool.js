import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  Table,
  Button,
  SpaceBetween,
  Box,
  TextFilter,
  Pagination,
  Alert,
  Checkbox,
  ButtonDropdown
} from '@cloudscape-design/components';

const ManageTool = ({ onCancel }) => {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [filteringText, setFilteringText] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [sortingColumn, setSortingColumn] = useState({ sortingField: 'tool_name' });
  const [sortingDescending, setSortingDescending] = useState(false);

  useEffect(() => {
    fetchTools();
  }, []);

  const parseDynamoDBItem = (item) => {
    const parsed = {};
    for (const [key, value] of Object.entries(item)) {
      if (value.S) parsed[key] = value.S;
      else if (value.N) parsed[key] = Number(value.N);
      else if (value.BOOL) parsed[key] = value.BOOL;
      else if (value.L) parsed[key] = value.L.map(listItem => listItem.S || listItem.N || listItem);
    }
    return parsed;
  };

  const fetchTools = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('https://j964h7agk6.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'list' })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.items && Array.isArray(data.items)) {
        const parsedTools = data.items.map(item => parseDynamoDBItem(item));
        setTools(parsedTools);
      } else {
        setTools([]);
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
      setError(`Failed to load tools: ${error.message}`);
      setTools([]);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (tool) => {
    console.log('Edit tool:', tool);
    // TODO: Implement edit functionality
  };

  const handleClone = (tool) => {
    console.log('Clone tool:', tool);
    // TODO: Implement clone functionality
  };

  const handleSelectionChange = ({ detail }) => {
    setSelectedItems(detail.selectedItems);
  };

  const columns = [
    {
      id: 'tool_name',
      header: 'Tool Name',
      cell: item => item.tool_name || 'N/A',
      sortingField: 'tool_name',
      isRowHeader: true
    },
    {
      id: 'system_type',
      header: 'System Type',
      cell: item => item.system_type || 'N/A',
      sortingField: 'system_type'
    },
    {
      id: 'action_name',
      header: 'Action',
      cell: item => item.action_name || 'N/A',
      sortingField: 'action_name'
    },
    {
      id: 'language',
      header: 'Language',
      cell: item => item.language || 'N/A',
      sortingField: 'language'
    },
    {
      id: 'blueprint_id',
      header: 'Blueprint ID',
      cell: item => item.blueprint_id || 'N/A',
      sortingField: 'blueprint_id'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            iconName="edit"
            variant="inline-icon"
            onClick={() => handleEdit(item)}
            ariaLabel={`Edit ${item.tool_name || 'tool'}`}
          >
            Edit
          </Button>
          <Button
            iconName="copy"
            variant="inline-icon"
            onClick={() => handleClone(item)}
            ariaLabel={`Clone ${item.tool_name || 'tool'}`}
          >
            Clone
          </Button>
        </SpaceBetween>
      )
    }
  ];

  const filteredItems = tools.filter(item => {
    const searchText = filteringText.toLowerCase();
    return (
      (item.tool_name || '').toLowerCase().includes(searchText) ||
      (item.system_type || '').toLowerCase().includes(searchText) ||
      (item.action_name || '').toLowerCase().includes(searchText) ||
      (item.language || '').toLowerCase().includes(searchText) ||
      (item.blueprint_id || '').toLowerCase().includes(searchText)
    );
  });

  const sortedItems = [...filteredItems].sort((a, b) => {
    const field = sortingColumn.sortingField;
    const aValue = a[field] || '';
    const bValue = b[field] || '';
    const result = aValue.toString().localeCompare(bValue.toString());
    return sortingDescending ? -result : result;
  });

  const pageSize = Math.max(5, Math.floor(window.innerHeight / 80) || 10);
  const paginatedItems = sortedItems.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  const bulkActions = [
    {
      text: 'Delete Selected',
      id: 'delete',
      disabled: selectedItems.length === 0
    },
    {
      text: 'Export Selected',
      id: 'export',
      disabled: selectedItems.length === 0
    }
  ];

  const handleBulkAction = ({ detail }) => {
    console.log('Bulk action:', detail.id, 'Items:', selectedItems);
    // TODO: Implement bulk actions
  };

  return (
    <Container
      header={
        <Header
          variant="h2"
          counter={`(${tools.length})`}
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={fetchTools} iconName="refresh">
                Refresh
              </Button>
              <Button onClick={onCancel}>
                Back
              </Button>
            </SpaceBetween>
          }
        >
          Manage Tools
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        {error && (
          <Alert
            statusIconAriaLabel="Error"
            type="error"
            dismissible
            onDismiss={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        <Table
          items={paginatedItems}
          columnDefinitions={columns}
          loading={loading}
          loadingText="Loading tools..."
          selectionType="multi"
          selectedItems={selectedItems}
          onSelectionChange={handleSelectionChange}
          sortingColumn={sortingColumn}
          sortingDescending={sortingDescending}
          onSortingChange={({ detail }) => {
            setSortingColumn(detail.sortingColumn);
            setSortingDescending(detail.isDescending);
          }}
          header={
            <Header
              counter={selectedItems.length > 0 ? `(${selectedItems.length}/${tools.length})` : `(${tools.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <ButtonDropdown
                    items={bulkActions}
                    onItemClick={handleBulkAction}
                    disabled={selectedItems.length === 0}
                  >
                    Actions
                  </ButtonDropdown>
                </SpaceBetween>
              }
            >
              Tools
            </Header>
          }
          filter={
            <TextFilter
              filteringText={filteringText}
              onChange={({ detail }) => {
                setFilteringText(detail.filteringText);
                setCurrentPageIndex(1);
              }}
              placeholder="Search tools..."
              filteringAriaLabel="Filter tools"
            />
          }
          pagination={
            <Pagination
              currentPageIndex={currentPageIndex}
              pagesCount={Math.ceil(sortedItems.length / pageSize)}
              onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
              ariaLabels={{
                nextPageLabel: 'Next page',
                previousPageLabel: 'Previous page',
                pageLabel: pageNumber => `Page ${pageNumber} of all pages`
              }}
            />
          }
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center">
              <SpaceBetween size="m">
                <b>No tools found</b>
                <p>No tools match the current filter criteria.</p>
                <Button onClick={fetchTools} iconName="refresh">
                  Refresh
                </Button>
              </SpaceBetween>
            </Box>
          }
        />
      </SpaceBetween>
    </Container>
  );
};

export default ManageTool;