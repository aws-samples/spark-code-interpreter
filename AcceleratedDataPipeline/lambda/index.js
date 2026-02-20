const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, ScanCommand, QueryCommand, GetCommand, PutCommand, UpdateCommand, DeleteCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

exports.handler = async (event) => {
    const { action, tableName, item, key, filters, updateExpression, expressionAttributeValues } = event;
    
    try {
        switch (action) {
            case 'list':
                return await listRecords(tableName, filters);
            case 'search':
                return await searchRecords(tableName, filters);
            case 'get':
                return await getRecord(tableName, key);
            case 'add':
                return await addRecord(tableName, item);
            case 'update':
                return await updateRecord(tableName, key, updateExpression, expressionAttributeValues);
            case 'delete':
                return await deleteRecord(tableName, key);
            default:
                throw new Error(`Unsupported action: ${action}`);
        }
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};

async function listRecords(tableName, filters = {}) {
    const params = { TableName: tableName };
    if (filters.limit) params.Limit = filters.limit;
    
    const result = await docClient.send(new ScanCommand(params));
    return {
        statusCode: 200,
        body: JSON.stringify({ items: result.Items, count: result.Count })
    };
}

async function searchRecords(tableName, filters) {
    const params = {
        TableName: tableName,
        FilterExpression: filters.expression,
        ExpressionAttributeValues: filters.values
    };
    
    const result = await docClient.send(new ScanCommand(params));
    return {
        statusCode: 200,
        body: JSON.stringify({ items: result.Items, count: result.Count })
    };
}

async function getRecord(tableName, key) {
    const params = {
        TableName: tableName,
        Key: key
    };
    
    const result = await docClient.send(new GetCommand(params));
    return {
        statusCode: result.Item ? 200 : 404,
        body: JSON.stringify({ item: result.Item })
    };
}

async function addRecord(tableName, item) {
    const params = {
        TableName: tableName,
        Item: item
    };
    
    await docClient.send(new PutCommand(params));
    return {
        statusCode: 201,
        body: JSON.stringify({ message: 'Record added successfully', item })
    };
}

async function updateRecord(tableName, key, updateExpression, expressionAttributeValues) {
    const params = {
        TableName: tableName,
        Key: key,
        UpdateExpression: updateExpression,
        ExpressionAttributeValues: expressionAttributeValues,
        ReturnValues: 'ALL_NEW'
    };
    
    const result = await docClient.send(new UpdateCommand(params));
    return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Record updated successfully', item: result.Attributes })
    };
}

async function deleteRecord(tableName, key) {
    const params = {
        TableName: tableName,
        Key: key,
        ReturnValues: 'ALL_OLD'
    };
    
    const result = await docClient.send(new DeleteCommand(params));
    return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Record deleted successfully', deletedItem: result.Attributes })
    };
}