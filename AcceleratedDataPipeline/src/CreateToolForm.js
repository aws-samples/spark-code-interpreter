import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Header, 
  Table,
  Button,
  SpaceBetween,
  Box,
  TextFilter,
  Pagination
} from '@cloudscape-design/components';
import EditBlueprintForm from './EditBlueprintForm';

const CreateToolForm = ({ onCancel }) => {
  const [blueprints, setBlueprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filteringText, setFilteringText] = useState('');
  const [currentPageIndex, setCurrentPageIndex] = useState(1);
  const [sortingColumn, setSortingColumn] = useState({ sortingField: 'name' });
  const [sortingDescending, setSortingDescending] = useState(false);
  const [selectedBlueprint, setSelectedBlueprint] = useState(null);

  const parseDynamoDBItem = (item) => {
    const parsed = {};
    for (const [key, value] of Object.entries(item)) {
      if (value.S) parsed[key] = value.S;
      else if (value.L) parsed[key] = value.L.map(listItem => listItem.S);
      else if (value.N) parsed[key] = Number(value.N);
      else if (value.BOOL) parsed[key] = value.BOOL;
    }
    return parsed;
  };

  const fetchBlueprints = async () => {
    try {
      setLoading(true);
      const response = await fetch('https://77a9252l49.execute-api.us-east-1.amazonaws.com/dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'list' })
      });

      if (response.ok) {
        const data = await response.json();
        const parsedItems = (data.items || []).map(item => parseDynamoDBItem(item));
        setBlueprints(parsedItems);
        console.log('Blueprints refreshed:', parsedItems.length);
      } else {
        console.error('Failed to fetch blueprints:', response.status);
      }
    } catch (error) {
      console.error('Error fetching blueprints:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBlueprints();
  }, []);

  const handleGenerateCode = (blueprint) => {
    setSelectedBlueprint(blueprint);
  };

  const handleBack = () => {
    setSelectedBlueprint(null);
  };

  const columns = [
    {
      id: 'name',
      header: 'Blueprint Name',
      cell: item => <strong>{item.name}</strong>,
      sortingField: 'name',
      isRowHeader: true
    },
    {
      id: 'description',
      header: 'Description',
      cell: item => item.description,
      sortingField: 'description'
    },
    {
      id: 'category',
      header: 'Category',
      cell: item => item.category,
      sortingField: 'category'
    },
    {
      id: 'service_type',
      header: 'Service Type',
      cell: item => item.service_type,
      sortingField: 'service_type'
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: item => (
        <Button
          iconName="gen-ai"
          variant="inline-icon"
          onClick={() => handleGenerateCode(item)}
          ariaLabel={`Generate code for ${item.name}`}
        >
          Generate Code
        </Button>
      )
    }
  ];

  const filteredItems = blueprints.filter(item =>
    item.name?.toLowerCase().includes(filteringText.toLowerCase()) ||
    item.description?.toLowerCase().includes(filteringText.toLowerCase()) ||
    item.service_type?.toLowerCase().includes(filteringText.toLowerCase())
  );

  const sortedItems = [...filteredItems].sort((a, b) => {
    const field = sortingColumn.sortingField;
    const result = (a[field] || '').localeCompare(b[field] || '');
    return sortingDescending ? -result : result;
  });

  const pageSize = 10;
  const paginatedItems = sortedItems.slice(
    (currentPageIndex - 1) * pageSize,
    currentPageIndex * pageSize
  );

  if (selectedBlueprint) {
    return <EditBlueprintForm onCancel={handleBack} selectedBlueprint={selectedBlueprint} />;
  }

  return (
    <Container 
      header={
        <Header 
          variant="h2" 
          counter={`(${blueprints.length})`} 
          actions={
            <SpaceBetween direction="horizontal" size="xs">
              <Button onClick={fetchBlueprints} iconName="refresh">
                Refresh
              </Button>
              <Button onClick={onCancel}>
                Back
              </Button>
            </SpaceBetween>
          }
        >
          Create Tools
        </Header>
      }
    >
      <Table
        items={paginatedItems}
        columnDefinitions={columns}
        loading={loading}
        loadingText="Loading blueprints..."
        sortingColumn={sortingColumn}
        sortingDescending={sortingDescending}
        onSortingChange={({ detail }) => {
          setSortingColumn(detail.sortingColumn);
          setSortingDescending(detail.isDescending);
        }}
        filter={
          <TextFilter
            filteringText={filteringText}
            onChange={({ detail }) => {
              setFilteringText(detail.filteringText);
              setCurrentPageIndex(1);
            }}
            placeholder="Search blueprints..."
          />
        }
        pagination={
          <Pagination
            currentPageIndex={currentPageIndex}
            pagesCount={Math.ceil(sortedItems.length / pageSize)}
            onChange={({ detail }) => setCurrentPageIndex(detail.currentPageIndex)}
          />
        }
        empty={
          <Box margin={{ vertical: 'xs' }} textAlign="center">
            <SpaceBetween size="m">
              <b>No blueprints</b>
              <p>No blueprints to display.</p>
            </SpaceBetween>
          </Box>
        }
        noMatch={
          <Box margin={{ vertical: 'xs' }} textAlign="center">
            <SpaceBetween size="m">
              <b>No matches</b>
              <p>We can't find a match.</p>
              <Button onClick={() => setFilteringText('')}>Clear filter</Button>
            </SpaceBetween>
          </Box>
        }
      />
    </Container>
  );
};

export default CreateToolForm;