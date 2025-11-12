# Aurora PostgreSQL Integration Specification

**Version:** 1.0  
**Date:** 2025-10-30  
**Status:** Design Specification

---

## 1. OVERVIEW

### 1.1 Purpose
Add Aurora PostgreSQL as a third data source for Spark data processing, alongside existing S3 CSV files and AWS Glue Catalog tables.

### 1.2 Goals
- Enable users to connect to Aurora PostgreSQL databases
- Browse and select PostgreSQL tables similar to Glue Catalog
- Generate Spark code with JDBC connectivity for PostgreSQL
- Execute queries on EMR Serverless with VPC access to Aurora
- Maintain all existing functionality (S3, Glue, Lambda, EMR)

### 1.3 Non-Goals
- Direct SQL query execution (Spark-based only)
- Real-time streaming from PostgreSQL
- Database schema modifications
- Multi-region PostgreSQL support (single region initially)

---

## 2. ARCHITECTURE

### 2.1 Current State
- **Data Sources:** S3 CSV files, AWS Glue Catalog tables
- **Execution Platforms:** Lambda (small data), EMR Serverless (large data/Glue)
- **Orchestration:** Spark Supervisor Agent (AgentCore)
- **Code Generation:** Code Generation Agent (untouched in this implementation)
- **Frontend:** GlueTableSelector component for browsing Glue catalog

### 2.2 Target State
- **Data Sources:** S3 CSV + Glue Catalog + Aurora PostgreSQL
- **New Component:** PostgreSQL metadata fetcher (direct Python module)
- **New UI:** PostgresTableSelector component
- **Enhanced:** Spark code generation with JDBC support
- **Enhanced:** EMR job submission with JDBC driver configuration

### 2.3 Architecture Diagram
```
Frontend (React)
├── GlueTableSelector (existing)
├── PostgresTableSelector (new)
└── App.jsx (updated)
        ↓
Backend (FastAPI)
├── /postgres/* endpoints (new)
├── postgres_metadata.py (new)
└── main.py (updated)
        ↓
Spark Supervisor Agent (AgentCore)
├── fetch_postgres_table_schema tool (new)
├── Updated system prompts
└── Enhanced EMR execution
        ↓
EMR Serverless (VPC-enabled)
├── JDBC driver from S3
├── Secrets Manager access
└── Aurora PostgreSQL connection
```

---

## 3. INFRASTRUCTURE REQUIREMENTS

### 3.1 AWS Resources

#### Aurora PostgreSQL
- **Cluster:** Aurora PostgreSQL 15.x or higher
- **VPC:** Private subnets only
- **Security Group:** Allow inbound port 5432 from EMR/Backend
- **Endpoint:** Cluster endpoint (writer) and reader endpoint
- **Backup:** Automated backups enabled
- **Encryption:** At-rest and in-transit encryption enabled

#### EMR Serverless
- **VPC Configuration:**
  - Same VPC as Aurora OR VPC peering configured
  - Private subnets with NAT gateway for internet access
  - Security group allowing outbound to Aurora (port 5432)
  
- **IAM Role Updates:**
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "arn:aws:secretsmanager:*:*:secret:spark/postgres/*"
      },
      {
        "Effect": "Allow",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::spark-data-*/jars/*"
      }
    ]
  }
  ```

#### AWS Secrets Manager
- **Secret Structure:**
  ```json
  {
    "connection_name": "aurora-postgres-prod",
    "host": "cluster-endpoint.region.rds.amazonaws.com",
    "port": 5432,
    "database": "defaultdb",
    "username": "admin",
    "password": "encrypted-password",
    "jdbc_url": "jdbc:postgresql://host:5432/database"
  }
  ```
- **Naming Convention:** `spark/postgres/{connection-name}`
- **Rotation:** Enable automatic rotation (30-90 days)

#### S3 Storage
- **JDBC Driver Location:** `s3://{spark_bucket}/jars/postgresql-42.7.1.jar`
- **Download:** https://jdbc.postgresql.org/download/
- **Upload Command:**
  ```bash
  aws s3 cp postgresql-42.7.1.jar s3://spark-data-{account}/jars/
  ```

### 3.2 Network Configuration

#### VPC Setup
- **Subnets:** Private subnets for Aurora and EMR
- **NAT Gateway:** Required for EMR to access Bedrock API and S3
- **Route Tables:** Configure routes for Aurora RDS subnet access

#### Security Groups
```
EMR Security Group (sg-emr-spark)
  Outbound: 
    - Port 5432 → Aurora Security Group
    - Port 443 → 0.0.0.0/0 (Bedrock, S3)

Aurora Security Group (sg-aurora-postgres)
  Inbound:
    - Port 5432 ← EMR Security Group
    - Port 5432 ← Backend Security Group (if in VPC)
```

#### Backend Network Access
- **Option 1:** Backend in same VPC as Aurora (recommended for production)
- **Option 2:** Aurora with public endpoint + SSL (development only)
- **Option 3:** VPC peering if backend in different VPC

### 3.3 IAM Permissions

#### Backend Role (Lambda/AgentCore)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:ListSecrets",
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:spark/postgres/*"
    }
  ]
}
```

---

## 4. BACKEND IMPLEMENTATION

### 4.1 Configuration Schema

#### File: `backend/config.py`

**Add to DEFAULT_CONFIG:**
```python
"spark": {
    "s3_bucket": "spark-data-260005718447-us-east-1",
    "lambda_function": "sparkOnLambda-spark-code-interpreter",
    "emr_application_id": "00fv6g7rptsov009",  # Existing - for S3/Glue
    "emr_postgres_application_id": "00g0oddl52n83r09",  # NEW - for PostgreSQL
    "max_retries": 3,
    "file_size_threshold_mb": 100,
    "result_preview_rows": 100,
    "presigned_url_expiry_hours": 24,
    "lambda_timeout_seconds": 300,
    "emr_timeout_minutes": 10,
    "supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
},
"postgres": {
    "connections": [],
    "default_connection": None,
    "jdbc_driver_path": "s3://spark-data-{account}/jars/postgresql-42.7.1.jar",
    "secrets_manager_prefix": "spark/postgres/",
    "connection_timeout": 10,
    "query_timeout": 30,
    "use_dedicated_emr": True  # Use separate EMR app for PostgreSQL
}
```

#### File: `backend/settings.json`

**User-Configurable Settings:**
```json
{
  "postgres": {
    "connections": [
      {
        "name": "aurora-prod",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod",
        "description": "Production Aurora PostgreSQL",
        "enabled": true
      },
      {
        "name": "aurora-dev",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-dev",
        "description": "Development Aurora PostgreSQL",
        "enabled": false
      }
    ],
    "default_connection": "aurora-prod",
    "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.1.jar"
  }
}
```

### 4.2 PostgreSQL Metadata Module

#### File: `backend/postgres_metadata.py` (NEW)

**Purpose:** Direct Python module to fetch database metadata from Aurora PostgreSQL

**Dependencies:**
```
psycopg2-binary==2.9.9
boto3>=1.28.0
```

**Add to `backend/requirements.txt`:**
```
psycopg2-binary==2.9.9
```

**Module Structure:**
```python
class PostgresMetadataFetcher:
    """Fetch metadata from PostgreSQL databases"""
    
    def __init__(self, region: str = 'us-east-1')
    
    def _get_credentials(self, secret_arn: str) -> dict
        # Get credentials from Secrets Manager
        # Cache with @lru_cache(maxsize=10)
    
    def _get_connection(self, secret_arn: str)
        # Get or create database connection
        # Connection pooling/caching
    
    def list_databases(self, secret_arn: str) -> List[str]
        # Query: SELECT datname FROM pg_database
    
    def list_schemas(self, secret_arn: str, database: str) -> List[str]
        # Query: SELECT schema_name FROM information_schema.schemata
    
    def list_tables(self, secret_arn: str, database: str, schema: str) -> List[Dict]
        # Query: SELECT table_name, columns FROM information_schema.tables
        # Returns: [{name, schema, columns: [{name, type, nullable}]}]
    
    def get_table_schema(self, secret_arn: str, database: str, 
                        schema: str, table: str) -> Dict
        # Detailed schema for specific table
        # Returns: {database, schema, table, jdbc_url, columns}
    
    def close_all(self)
        # Close all cached connections

# Singleton pattern
def get_postgres_metadata_fetcher() -> PostgresMetadataFetcher
```

**Key Features:**
- Connection pooling and caching
- Credential caching with LRU cache
- Timeout handling (10s connection, 30s query)
- Graceful error handling
- Singleton instance for application lifecycle

**Error Handling:**
- Connection timeout → Return error with retry suggestion
- Authentication failure → Return error with credential check message
- Network unreachable → Return error with VPC configuration message
- Query timeout → Return error with query optimization suggestion


### 4.3 Backend API Endpoints

#### File: `backend/main.py` (UPDATED)

**Import Statement:**
```python
from postgres_metadata import get_postgres_metadata_fetcher
```

**Application Lifecycle:**
```python
@app.on_event("startup")
async def startup_event():
    get_postgres_metadata_fetcher()

@app.on_event("shutdown")
async def shutdown_event():
    get_postgres_metadata_fetcher().close_all()
```

**New Endpoints:**

#### 1. GET `/postgres/connections`
**Purpose:** List all configured PostgreSQL connections

**Response:**
```json
{
  "success": true,
  "connections": [
    {
      "name": "aurora-prod",
      "description": "Production Aurora PostgreSQL",
      "enabled": true
    }
  ]
}
```

**Implementation:**
```python
@app.get("/postgres/connections")
async def list_postgres_connections():
    config = load_config()
    connections = config.get('postgres', {}).get('connections', [])
    return {
        "success": True,
        "connections": [
            {
                "name": c['name'],
                "description": c.get('description', ''),
                "enabled": c.get('enabled', True)
            }
            for c in connections if c.get('enabled', True)
        ]
    }
```

#### 2. GET `/postgres/{connection_name}/databases`
**Purpose:** List all databases in a PostgreSQL connection

**Response:**
```json
{
  "success": true,
  "databases": ["postgres", "myapp", "analytics"]
}
```

**Implementation:**
```python
@app.get("/postgres/{connection_name}/databases")
async def list_postgres_databases(connection_name: str):
    try:
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        databases = fetcher.list_databases(conn['secret_arn'])
        
        return {"success": True, "databases": databases}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 3. GET `/postgres/{connection_name}/schemas/{database}`
**Purpose:** List schemas in a database

**Response:**
```json
{
  "success": true,
  "schemas": ["public", "analytics", "staging"]
}
```

#### 4. GET `/postgres/{connection_name}/tables/{database}/{schema}`
**Purpose:** List tables with column metadata

**Response:**
```json
{
  "success": true,
  "tables": [
    {
      "name": "users",
      "schema": "public",
      "columns": [
        {"name": "id", "type": "integer", "nullable": false},
        {"name": "email", "type": "varchar", "nullable": false}
      ]
    }
  ]
}
```

#### 5. POST `/sessions/{session_id}/select-postgres-tables`
**Purpose:** Store selected PostgreSQL tables in session

**Request:**
```json
{
  "connection_name": "aurora-prod",
  "tables": [
    {
      "database": "myapp",
      "schema": "public",
      "table": "users"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "selected_tables": [
    {
      "connection_name": "aurora-prod",
      "database": "myapp",
      "schema": "public",
      "table": "users",
      "jdbc_url": "jdbc:postgresql://host:5432/myapp"
    }
  ]
}
```

**Implementation:**
```python
class PostgresTableSelectionRequest(BaseModel):
    connection_name: str
    tables: List[Dict[str, str]]

@app.post("/sessions/{session_id}/select-postgres-tables")
async def select_postgres_tables(session_id: str, request: PostgresTableSelectionRequest):
    try:
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == request.connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        selected_tables = []
        
        for table_ref in request.tables:
            schema_info = fetcher.get_table_schema(
                conn['secret_arn'],
                table_ref['database'],
                table_ref['schema'],
                table_ref['table']
            )
            selected_tables.append({
                'connection_name': request.connection_name,
                'secret_arn': conn['secret_arn'],
                **schema_info
            })
        
        # Store in session
        if session_id not in prompt_sessions:
            prompt_sessions[session_id] = {'postgres_tables': []}
        prompt_sessions[session_id]['postgres_tables'] = selected_tables
        
        return {"success": True, "selected_tables": selected_tables}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 5. SPARK SUPERVISOR AGENT UPDATES

### 5.1 New Tool: fetch_postgres_table_schema

#### File: `backend/spark-supervisor-agent/spark_supervisor_agent.py` (UPDATED)

**Tool Definition:**
```python
@tool
def fetch_postgres_table_schema(
    connection_name: str,
    database: str,
    schema: str,
    table: str
) -> dict:
    """
    Fetch detailed schema for a PostgreSQL table including JDBC connection info.
    
    Args:
        connection_name: Name of PostgreSQL connection (e.g., 'aurora-prod')
        database: Database name
        schema: Schema name (e.g., 'public')
        table: Table name
    
    Returns:
        {
            'connection_name': str,
            'database': str,
            'schema': str,
            'table': str,
            'jdbc_url': str,
            'secret_arn': str,
            'columns': [{'name': str, 'type': str, 'nullable': bool}]
        }
    """
    try:
        config = get_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == connection_name), None)
        
        if not conn:
            return {'error': f'Connection {connection_name} not found'}
        
        # Import metadata fetcher
        from postgres_metadata import get_postgres_metadata_fetcher
        
        fetcher = get_postgres_metadata_fetcher()
        schema_info = fetcher.get_table_schema(
            conn['secret_arn'],
            database,
            schema,
            table
        )
        
        return {
            'connection_name': connection_name,
            'secret_arn': conn['secret_arn'],
            **schema_info
        }
    except Exception as e:
        return {'error': str(e)}
```

### 5.2 Update: call_code_generation_agent Function

**Add PostgreSQL Table Handling:**
```python
def call_code_generation_agent(
    prompt: str, 
    session_id: str, 
    s3_input_path: str = None, 
    selected_tables: list = None,
    selected_postgres_tables: list = None,  # NEW
    s3_output_path: str = None
) -> str:
    
    # Existing S3 and Glue handling...
    
    # NEW: PostgreSQL table handling
    if selected_postgres_tables:
        postgres_context = "\n\nPostgreSQL tables:\n"
        for pg_table in selected_postgres_tables:
            postgres_context += f"- Connection: {pg_table['connection_name']}\n"
            postgres_context += f"  {pg_table['database']}.{pg_table['schema']}.{pg_table['table']}\n"
            postgres_context += f"  JDBC URL: {pg_table['jdbc_url']}\n"
            postgres_context += f"  Secret ARN: {pg_table['secret_arn']}\n"
            postgres_context += f"  Columns: {', '.join([f\"{c['name']} ({c['type']})\" for c in pg_table['columns'][:5]])}\n"
        
        data_context += postgres_context
        
        # Add JDBC driver path
        jdbc_driver = config.get('postgres', {}).get('jdbc_driver_path')
        if jdbc_driver:
            data_context += f"\nJDBC Driver: {jdbc_driver}\n"
```

### 5.3 Update: System Prompt

**Add PostgreSQL Instructions:**
```python
POSTGRESQL DATA SOURCES:
When prompt mentions PostgreSQL tables, use JDBC connection with these patterns:

1. SPARK CONFIGURATION:
   spark = SparkSession.builder \\
       .appName("PostgreSQLQuery") \\
       .config("spark.jars", "s3://bucket/jars/postgresql-42.7.1.jar") \\
       .getOrCreate()

2. GET CREDENTIALS FROM SECRETS MANAGER:
   import boto3, json
   secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
   secret = secrets_client.get_secret_value(SecretId='SECRET_ARN_FROM_CONTEXT')
   creds = json.loads(secret['SecretString'])

3. READ FROM POSTGRESQL:
   df = spark.read.format("jdbc") \\
       .option("url", creds['jdbc_url']) \\
       .option("dbtable", "schema.table") \\
       .option("user", creds['username']) \\
       .option("password", creds['password']) \\
       .option("driver", "org.postgresql.Driver") \\
       .load()

4. PERFORMANCE OPTIMIZATION:
   - Use predicates for pushdown: .option("predicates", ["id > 1000"])
   - Partition reads: .option("partitionColumn", "id")
   - Fetch size: .option("fetchsize", "1000")

5. JOINING POSTGRESQL WITH OTHER SOURCES:
   - Read PostgreSQL table → Spark DataFrame
   - Read Glue/S3 → Spark DataFrame
   - Join in Spark: df1.join(df2, condition)

CRITICAL RULES FOR POSTGRESQL:
- ALWAYS use Secret ARN from context (never hardcode credentials)
- ALWAYS include JDBC driver in spark.jars configuration
- Use schema.table format for dbtable option
- Include error handling for connection failures
- Write results to S3 output path (never back to PostgreSQL)
```

### 5.4 Update: execute_spark_code_emr Function

**Add JDBC Driver Configuration:**
```python
def execute_spark_code_emr(spark_code: str, s3_output_path: str) -> dict:
    # ... existing code ...
    
    # Get JDBC driver path from config
    config = get_config()
    jdbc_driver = config.get('postgres', {}).get('jdbc_driver_path', '')
    
    # Build spark-submit parameters
    spark_params = '--conf spark.executor.instances=2'
    if jdbc_driver:
        spark_params += f' --jars {jdbc_driver}'
    
    response = emr_client.start_job_run(
        applicationId=config['emr_application_id'],
        executionRoleArn=execution_role,
        jobDriver={
            'sparkSubmit': {
                'entryPoint': s3_code_path,
                'sparkSubmitParameters': spark_params
            }
        },
        # ... rest of configuration ...
    )
```

### 5.5 Update: Platform Selection Logic

**Force EMR for PostgreSQL Queries:**
```python
@tool
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """
    Select execution platform based on data source and size.
    
    Returns: 'lambda' or 'emr'
    """
    config = get_config()
    threshold = config.get('file_size_threshold_mb', 100)
    
    # Check if PostgreSQL tables are selected (from global context)
    if CURRENT_SESSION_ID:
        session_data = prompt_sessions.get(CURRENT_SESSION_ID, {})
        if session_data.get('postgres_tables'):
            return 'emr'  # Force EMR for PostgreSQL (requires VPC)
    
    # Existing logic for Glue and S3...
    if file_size_mb > threshold:
        return 'emr'
    else:
        return 'lambda'
```

---

## 6. FRONTEND IMPLEMENTATION

### 6.1 New Component: PostgresTableSelector

#### File: `frontend/src/components/PostgresTableSelector.jsx` (NEW)

**Component Structure:**
```jsx
const PostgresTableSelector = ({ sessionId, onTablesSelected }) => {
  // State
  const [connections, setConnections] = useState([])
  const [selectedConnection, setSelectedConnection] = useState(null)
  const [databases, setDatabases] = useState([])
  const [selectedDatabase, setSelectedDatabase] = useState(null)
  const [schemas, setSchemas] = useState([])
  const [selectedSchema, setSelectedSchema] = useState(null)
  const [tables, setTables] = useState([])
  const [selectedTables, setSelectedTables] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // API calls
  useEffect(() => loadConnections(), [])
  
  const loadConnections = async () => {
    // GET /postgres/connections
  }
  
  const loadDatabases = async (connectionName) => {
    // GET /postgres/{connection}/databases
  }
  
  const loadSchemas = async (connectionName, database) => {
    // GET /postgres/{connection}/schemas/{database}
  }
  
  const loadTables = async (connectionName, database, schema) => {
    // GET /postgres/{connection}/tables/{database}/{schema}
  }
  
  const handleApply = async () => {
    // POST /sessions/{sessionId}/select-postgres-tables
  }
  
  // Render
  return (
    <Container header={<Header>PostgreSQL Data Source</Header>}>
      <SpaceBetween size="l">
        <FormField label="Connection">
          <Select
            selectedOption={selectedConnection}
            onChange={handleConnectionChange}
            options={connections}
          />
        </FormField>
        
        <FormField label="Database">
          <Select
            selectedOption={selectedDatabase}
            onChange={handleDatabaseChange}
            options={databases}
            disabled={!selectedConnection}
          />
        </FormField>
        
        <FormField label="Schema">
          <Select
            selectedOption={selectedSchema}
            onChange={handleSchemaChange}
            options={schemas}
            disabled={!selectedDatabase}
          />
        </FormField>
        
        <FormField label="Tables">
          <Multiselect
            selectedOptions={selectedTables}
            onChange={handleTablesChange}
            options={tables}
            disabled={!selectedSchema}
          />
        </FormField>
        
        <Button
          variant="primary"
          onClick={handleApply}
          disabled={selectedTables.length === 0}
        >
          Apply Selection
        </Button>
      </SpaceBetween>
    </Container>
  )
}
```

**Key Features:**
- Cascading dropdowns (Connection → Database → Schema → Tables)
- Multi-select for tables with column preview
- Loading states and error handling
- Similar UX to GlueTableSelector


### 6.2 App.jsx Integration

#### File: `frontend/src/App.jsx` (UPDATED)

**State Additions:**
```jsx
const [selectedPostgresTables, setSelectedPostgresTables] = useState([])
const [postgresConnection, setPostgresConnection] = useState(null)
```

**UI Layout:**
```jsx
{framework === 'spark' && (
  <Tabs
    tabs={[
      {
        label: "Glue Catalog",
        id: "glue",
        content: (
          <GlueTableSelector
            sessionId={sessionId}
            onTablesSelected={setSelectedTables}
          />
        )
      },
      {
        label: "PostgreSQL",
        id: "postgres",
        content: (
          <PostgresTableSelector
            sessionId={sessionId}
            onTablesSelected={setSelectedPostgresTables}
          />
        )
      }
    ]}
  />
)}
```

**Display Selected Tables:**
```jsx
{framework === 'spark' && selectedPostgresTables.length > 0 && (
  <Container>
    <SpaceBetween size="xs">
      <Box variant="awsui-key-label">Selected PostgreSQL Tables</Box>
      {selectedPostgresTables.map((t, i) => (
        <Box key={i} fontSize="body-s">
          <SpaceBetween direction="horizontal" size="xs">
            <Box>
              {t.connection_name}: {t.database}.{t.schema}.{t.table}
            </Box>
            <Button
              variant="icon"
              iconName="close"
              onClick={() => setSelectedPostgresTables(
                selectedPostgresTables.filter((_, idx) => idx !== i)
              )}
              ariaLabel={`Remove ${t.database}.${t.schema}.${t.table}`}
            />
          </SpaceBetween>
        </Box>
      ))}
    </SpaceBetween>
  </Container>
)}
```

**Request Payload Update:**
```jsx
const generateCode = async () => {
  const payload = {
    prompt: prompt,
    session_id: sessionId,
    framework: framework,
    s3_input_path: uploadedCsvPath,
    selected_tables: selectedTables,  // Glue tables
    selected_postgres_tables: selectedPostgresTables,  // NEW
    execution_platform: executionEngine
  }
  
  const response = await fetch('http://localhost:8000/spark/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}
```

### 6.3 Settings Component Update

#### File: `frontend/src/components/Settings.jsx` (UPDATED)

**Add PostgreSQL Configuration Section:**
```jsx
<ExpandableSection header="PostgreSQL Connections">
  <SpaceBetween size="m">
    {postgresConnections.map((conn, idx) => (
      <Container key={idx}>
        <SpaceBetween size="s">
          <FormField label="Connection Name">
            <Input value={conn.name} onChange={...} />
          </FormField>
          <FormField label="Secret ARN">
            <Input value={conn.secret_arn} onChange={...} />
          </FormField>
          <FormField label="Description">
            <Input value={conn.description} onChange={...} />
          </FormField>
          <Button
            variant="normal"
            iconName="remove"
            onClick={() => removeConnection(idx)}
          >
            Remove
          </Button>
        </SpaceBetween>
      </Container>
    ))}
    
    <Button
      variant="primary"
      iconName="add-plus"
      onClick={addConnection}
    >
      Add Connection
    </Button>
  </SpaceBetween>
</ExpandableSection>
```

---

## 7. CODE GENERATION PATTERNS

### 7.1 Prompt Context Example

**User Request:**
```
Join users and orders tables from PostgreSQL and show top customers
```

**Generated Context:**
```
User request: Join users and orders tables from PostgreSQL and show top customers

Data sources:

PostgreSQL tables (connection: aurora-prod):
- myapp.public.users at jdbc:postgresql://cluster.region.rds.amazonaws.com:5432/myapp
  Columns: id (integer), name (varchar), email (varchar), created_at (timestamp)
  
- myapp.public.orders at jdbc:postgresql://cluster.region.rds.amazonaws.com:5432/myapp
  Columns: id (integer), user_id (integer), amount (decimal), order_date (date)

JDBC Driver: s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.1.jar
Secret ARN: arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod

Selected Glue tables: None
Output path: s3://spark-data-260005718447-us-east-1/output/session-xyz
Session ID: session-xyz
```

### 7.2 Generated Code Example

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, desc
import boto3
import json

# Initialize Spark with JDBC driver
spark = SparkSession.builder \
    .appName("PostgreSQLJoinQuery") \
    .config("spark.jars", "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.1.jar") \
    .getOrCreate()

# Get credentials from Secrets Manager
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
secret = secrets_client.get_secret_value(
    SecretId='arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod'
)
creds = json.loads(secret['SecretString'])

# Read users table from PostgreSQL
users_df = spark.read.format("jdbc") \
    .option("url", creds['jdbc_url']) \
    .option("dbtable", "public.users") \
    .option("user", creds['username']) \
    .option("password", creds['password']) \
    .option("driver", "org.postgresql.Driver") \
    .load()

# Read orders table from PostgreSQL
orders_df = spark.read.format("jdbc") \
    .option("url", creds['jdbc_url']) \
    .option("dbtable", "public.orders") \
    .option("user", creds['username']) \
    .option("password", creds['password']) \
    .option("driver", "org.postgresql.Driver") \
    .load()

# Join and aggregate
result = users_df.join(orders_df, users_df.id == orders_df.user_id) \
    .groupBy("name", "email") \
    .agg(
        sum("amount").alias("total_amount"),
        count("*").alias("order_count")
    ) \
    .orderBy(desc("total_amount")) \
    .limit(10)

# Display results
print("Top 10 Customers by Total Order Amount:")
result.show(10, truncate=False)

# Write to S3
result.coalesce(1).write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv("s3://spark-data-260005718447-us-east-1/output/session-xyz/")

print(f"Results written to S3")
spark.stop()
```

### 7.3 Mixed Data Sources Example

**Scenario:** Join PostgreSQL users with Glue orders table

```python
# Read from PostgreSQL
users_df = spark.read.format("jdbc") \
    .option("url", creds['jdbc_url']) \
    .option("dbtable", "public.users") \
    .option("user", creds['username']) \
    .option("password", creds['password']) \
    .option("driver", "org.postgresql.Driver") \
    .load()

# Read from Glue Catalog
spark_glue = SparkSession.builder \
    .config("spark.sql.warehouse.dir", "s3://bucket/warehouse/") \
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \
    .enableHiveSupport() \
    .getOrCreate()

orders_df = spark_glue.table("analytics.orders")

# Join across data sources
result = users_df.join(orders_df, users_df.id == orders_df.user_id)
```

---

## 8. EXECUTION FLOW

### 8.1 End-to-End Flow

```
1. User selects PostgreSQL tables in UI
   ↓
2. Frontend calls POST /sessions/{id}/select-postgres-tables
   ↓
3. Backend fetches table schemas via postgres_metadata.py
   ↓
4. Schemas stored in session with Secret ARN
   ↓
5. User enters prompt and clicks "Generate Code"
   ↓
6. Frontend sends request with selected_postgres_tables
   ↓
7. Backend invokes Spark Supervisor Agent
   ↓
8. Agent builds context with PostgreSQL table info
   ↓
9. Agent calls Code Generation Agent (unchanged)
   ↓
10. Generated code includes JDBC connectivity
    ↓
11. Agent validates code syntax
    ↓
12. Agent selects EMR platform (forced for PostgreSQL)
    ↓
13. Agent calls execute_spark_code_emr with JDBC driver
    ↓
14. EMR job runs in VPC, connects to Aurora
    ↓
15. Results written to S3
    ↓
16. Agent fetches results and returns to user
```

### 8.2 Platform Selection Logic

```python
def determine_execution_platform(request):
    if request.selected_postgres_tables:
        return 'emr'  # Force EMR for PostgreSQL (VPC required)
    elif request.selected_tables:
        return 'emr'  # Force EMR for Glue tables
    elif request.file_size_mb > threshold:
        return 'emr'  # Large files
    else:
        return 'lambda'  # Small CSV files
```

### 8.3 Error Handling

**Connection Errors:**
- Timeout → Suggest VPC/security group check
- Authentication → Suggest credential verification
- Network unreachable → Suggest VPC configuration

**Query Errors:**
- Table not found → Suggest schema refresh
- Column mismatch → Suggest schema validation
- Permission denied → Suggest database user permissions

**EMR Errors:**
- JDBC driver not found → Suggest S3 path verification
- Secrets Manager access denied → Suggest IAM role check
- VPC connectivity → Suggest security group rules

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Credential Management
- **Storage:** AWS Secrets Manager only
- **Access:** IAM role-based (no hardcoded credentials)
- **Rotation:** Automatic rotation enabled (30-90 days)
- **Logging:** Never log credentials or connection strings
- **Caching:** Credential cache with TTL (5 minutes max)

### 9.2 Network Security
- **Aurora:** Private subnets only, no public access
- **EMR:** VPC-enabled with private subnets
- **Security Groups:** Minimal port access (5432 only)
- **Encryption:** TLS in-transit, AES-256 at-rest
- **VPC Flow Logs:** Enabled for audit trail

### 9.3 IAM Best Practices
- **Least Privilege:** Minimal permissions per role
- **Resource-Based:** Restrict to specific Secret ARNs
- **Condition Keys:** Use aws:SourceAccount, aws:SourceArn
- **MFA:** Require MFA for production secret access
- **Audit:** CloudTrail logging for all API calls

### 9.4 Data Protection
- **Query Results:** Encrypted in S3 (SSE-S3 or SSE-KMS)
- **Logs:** Sanitize before writing to CloudWatch
- **Temporary Files:** Auto-delete after execution
- **PII Handling:** Mask sensitive columns in previews

---

## 10. TESTING STRATEGY

### 10.1 Unit Tests

**Backend Tests:**
```python
# test_postgres_metadata.py
def test_list_databases()
def test_list_schemas()
def test_list_tables()
def test_get_table_schema()
def test_connection_caching()
def test_credential_caching()
def test_error_handling()
```

**Frontend Tests:**
```javascript
// PostgresTableSelector.test.jsx
test('loads connections on mount')
test('cascading dropdown behavior')
test('multi-select tables')
test('apply selection')
test('error handling')
```

### 10.2 Integration Tests

**Test Scenarios:**
1. **Single PostgreSQL Table Query**
   - Select one table
   - Generate simple SELECT query
   - Execute on EMR
   - Verify results in S3

2. **PostgreSQL Join Query**
   - Select multiple tables
   - Generate JOIN query
   - Execute on EMR
   - Verify results

3. **Mixed Data Sources**
   - Select PostgreSQL + Glue tables
   - Generate cross-source JOIN
   - Execute on EMR
   - Verify results

4. **PostgreSQL + S3 CSV**
   - Upload CSV file
   - Select PostgreSQL table
   - Generate JOIN query
   - Execute on EMR
   - Verify results

5. **Connection Failure Handling**
   - Invalid credentials
   - Network timeout
   - Database not found
   - Verify error messages

### 10.3 Performance Tests

**Metrics to Measure:**
- Metadata fetch time (< 2s per operation)
- Code generation time (< 5s)
- EMR job startup time (< 60s)
- Query execution time (varies by data size)
- Result fetch time (< 5s for < 1000 rows)

**Load Testing:**
- Concurrent metadata requests (10 users)
- Multiple EMR jobs (5 concurrent)
- Large result sets (> 10,000 rows)
- Connection pool exhaustion

### 10.4 Security Tests

**Penetration Testing:**
- SQL injection attempts
- Credential exposure in logs
- Unauthorized database access
- Secret ARN enumeration
- Network segmentation bypass

**Compliance Checks:**
- Encryption at-rest verification
- Encryption in-transit verification
- IAM policy validation
- Audit log completeness
- Secret rotation verification

---

## 11. DEPLOYMENT PLAN

### 11.1 Phase 1: Infrastructure Setup (Days 1-3)

**Tasks:**
1. Deploy Aurora PostgreSQL cluster
   - Create VPC and subnets
   - Configure security groups
   - Create database and schemas
   - Load sample data

2. Configure Secrets Manager
   - Create secrets for each connection
   - Set up rotation policies
   - Grant IAM access

3. Update EMR Configuration
   - Enable VPC mode
   - Update security groups
   - Update IAM execution role
   - Upload JDBC driver to S3

4. Test Connectivity
   - EMR → Aurora connection test
   - Backend → Aurora connection test
   - Verify security group rules

**Deliverables:**
- Aurora cluster endpoint
- Secret ARNs
- Updated EMR application ID
- JDBC driver S3 path

### 11.2 Phase 2: Backend Implementation (Days 4-7)

**Tasks:**
1. Implement postgres_metadata.py
   - Connection management
   - Metadata fetching functions
   - Error handling
   - Unit tests

2. Add Backend API Endpoints
   - /postgres/connections
   - /postgres/{conn}/databases
   - /postgres/{conn}/schemas/{db}
   - /postgres/{conn}/tables/{db}/{schema}
   - /sessions/{id}/select-postgres-tables

3. Update Spark Supervisor Agent
   - Add fetch_postgres_table_schema tool
   - Update call_code_generation_agent
   - Update system prompts
   - Update execute_spark_code_emr

4. Integration Testing
   - Test metadata fetching
   - Test code generation
   - Test EMR execution

**Deliverables:**
- Working backend endpoints
- Updated Spark Supervisor Agent
- Integration test results

### 11.3 Phase 3: Frontend Implementation (Days 8-10)

**Tasks:**
1. Create PostgresTableSelector Component
   - Cascading dropdowns
   - Multi-select tables
   - Loading states
   - Error handling

2. Update App.jsx
   - Add PostgreSQL tab
   - Display selected tables
   - Update request payload
   - Handle responses

3. Update Settings Component
   - PostgreSQL connection management
   - Add/remove connections
   - Save to backend

4. UI/UX Testing
   - User flow testing
   - Error scenario testing
   - Responsive design testing

**Deliverables:**
- Working UI components
- Updated App.jsx
- UI test results

### 11.4 Phase 4: End-to-End Testing (Days 11-12)

**Tasks:**
1. Functional Testing
   - All test scenarios from Section 10.2
   - Error handling verification
   - Performance benchmarking

2. Security Testing
   - Credential handling verification
   - Network security validation
   - IAM policy testing

3. User Acceptance Testing
   - Internal team testing
   - Documentation review
   - Feedback incorporation

**Deliverables:**
- Test results report
- Bug fixes
- Performance metrics

### 11.5 Phase 5: Documentation & Rollout (Days 13-14)

**Tasks:**
1. Documentation
   - User guide for PostgreSQL setup
   - Admin guide for connection configuration
   - Troubleshooting guide
   - API documentation

2. Deployment
   - Deploy to staging environment
   - Smoke testing
   - Deploy to production
   - Monitor for issues

3. Training
   - Team training session
   - Demo video creation
   - FAQ document

**Deliverables:**
- Complete documentation
- Production deployment
- Training materials

---

## 12. MONITORING & MAINTENANCE

### 12.1 Metrics to Monitor

**Application Metrics:**
- PostgreSQL metadata fetch latency
- Code generation success rate
- EMR job success rate
- Query execution time
- Result fetch time

**Infrastructure Metrics:**
- Aurora CPU/memory utilization
- Aurora connection count
- EMR job queue depth
- S3 request rate
- Secrets Manager API calls

**Error Metrics:**
- Connection timeout rate
- Authentication failure rate
- Query failure rate
- Network error rate

### 12.2 Alerts

**Critical Alerts:**
- Aurora cluster down
- EMR application unavailable
- Secrets Manager access denied
- High error rate (> 10%)

**Warning Alerts:**
- High Aurora connection count (> 80%)
- Slow query performance (> 60s)
- High EMR job queue (> 10 jobs)
- Credential rotation failure

### 12.3 Maintenance Tasks

**Daily:**
- Review error logs
- Check EMR job success rate
- Monitor Aurora performance

**Weekly:**
- Review slow queries
- Check connection pool health
- Validate security group rules

**Monthly:**
- Rotate database credentials
- Review IAM policies
- Update JDBC driver if needed
- Performance optimization review

---

## 13. FUTURE ENHANCEMENTS

### 13.1 Snowflake Integration
- Similar architecture to PostgreSQL
- Use Snowflake JDBC driver
- Snowflake-specific optimizations
- Estimated effort: 5-7 days

### 13.2 Databricks Integration
- Databricks JDBC/ODBC driver
- Unity Catalog integration
- Delta Lake support
- Estimated effort: 7-10 days

### 13.3 Query Optimization
- Predicate pushdown hints in UI
- Partition column selection
- Fetch size configuration
- Query plan visualization

### 13.4 Connection Pooling
- Implement HikariCP for PostgreSQL
- Connection health checks
- Automatic reconnection
- Pool size configuration

### 13.5 Advanced Features
- Query result caching
- Incremental data loading
- Change data capture (CDC)
- Real-time data streaming

---

## 14. ROLLBACK PLAN

### 14.1 Rollback Triggers
- Critical bugs in production
- Security vulnerabilities discovered
- Performance degradation
- Data corruption issues

### 14.2 Rollback Steps

**Backend Rollback:**
1. Revert Spark Supervisor Agent to previous version
2. Remove PostgreSQL endpoints from main.py
3. Remove postgres_metadata.py
4. Restart backend services

**Frontend Rollback:**
1. Remove PostgresTableSelector component
2. Revert App.jsx changes
3. Rebuild and redeploy frontend

**Infrastructure Rollback:**
1. Remove EMR VPC configuration (if needed)
2. Revert IAM role changes
3. Keep Aurora cluster (no impact)

### 14.3 Data Preservation
- No data loss (read-only operations)
- Session data cleared automatically
- S3 results preserved
- Audit logs maintained

---

## 15. SUCCESS CRITERIA

### 15.1 Functional Requirements
✅ Users can browse PostgreSQL databases/schemas/tables  
✅ Users can select multiple PostgreSQL tables  
✅ Code generation includes JDBC connectivity  
✅ Queries execute successfully on EMR  
✅ Results displayed in UI  
✅ All existing features (S3, Glue) remain functional  

### 15.2 Performance Requirements
✅ Metadata fetch < 2s per operation  
✅ Code generation < 5s  
✅ EMR job startup < 60s  
✅ Query execution time acceptable for data size  
✅ UI responsive (< 200ms interactions)  

### 15.3 Security Requirements
✅ No credentials in logs or responses  
✅ Secrets Manager for all credentials  
✅ VPC-based network isolation  
✅ Encryption at-rest and in-transit  
✅ IAM least privilege policies  

### 15.4 Reliability Requirements
✅ 99.9% uptime for metadata operations  
✅ Graceful error handling  
✅ Automatic retry for transient failures  
✅ Connection pool management  
✅ Comprehensive logging  

---

## 16. APPENDIX

### 16.1 PostgreSQL JDBC Driver Versions
- **Recommended:** postgresql-42.7.1.jar
- **Minimum:** postgresql-42.0.0.jar
- **Download:** https://jdbc.postgresql.org/download/

### 16.2 Secrets Manager Secret Template
```json
{
  "connection_name": "aurora-prod",
  "host": "cluster-endpoint.region.rds.amazonaws.com",
  "port": 5432,
  "database": "postgres",
  "username": "admin",
  "password": "SecurePassword123!",
  "jdbc_url": "jdbc:postgresql://cluster-endpoint.region.rds.amazonaws.com:5432/postgres",
  "ssl": true,
  "ssl_mode": "require"
}
```

### 16.3 EMR Spark Configuration
```json
{
  "spark.executor.instances": "2",
  "spark.executor.memory": "4g",
  "spark.executor.cores": "2",
  "spark.driver.memory": "2g",
  "spark.sql.adaptive.enabled": "true",
  "spark.sql.adaptive.coalescePartitions.enabled": "true"
}
```

### 16.4 Useful SQL Queries

**List all tables with row counts:**
```sql
SELECT 
  schemaname,
  tablename,
  n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

**Check table size:**
```sql
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 16.5 Troubleshooting Guide

**Issue:** Connection timeout  
**Solution:** Check security groups, VPC routing, Aurora status

**Issue:** Authentication failed  
**Solution:** Verify Secret ARN, check credentials, test with psql

**Issue:** JDBC driver not found  
**Solution:** Verify S3 path, check EMR IAM role permissions

**Issue:** Slow query performance  
**Solution:** Add predicates, use partitioning, optimize indexes

**Issue:** Out of memory  
**Solution:** Increase executor memory, reduce fetch size, partition data

---

**END OF SPECIFICATION**

---

## 17. INFRASTRUCTURE ANALYSIS & SPECIFIC CONFIGURATION CHANGES

### 17.1 Current Aurora PostgreSQL Configuration

**Cluster Details:**
- **Cluster ID:** `pg-database`
- **Endpoint:** `pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com`
- **Reader Endpoint:** `pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com`
- **Engine:** Aurora PostgreSQL 16.8
- **Port:** 5432
- **VPC:** `vpc-0485dcc1f1d050b55` (default VPC)
- **Security Group:** `sg-098a735e14f9f2953` (default)
- **Subnet Group:** `default-vpc-0485dcc1f1d050b55`
- **IAM Auth:** Enabled
- **HTTP Endpoint:** Enabled (Data API)
- **Encryption:** Enabled (KMS key: `d9dba9d3-49da-4222-94d4-75f4c028cded`)
- **Serverless v2:** Min 2.0 ACU, Max 10.0 ACU

**Current Security Group Rules (sg-098a735e14f9f2953):**
- ✅ Port 5432 open from `108.24.105.184/32` (external IP)
- ✅ All traffic within same security group (self-referencing)
- ❌ No specific rule for EMR Serverless application

### 17.2 Current EMR Serverless Configuration

**Application Details:**
- **Application ID:** `00fv6g7rptsov009`
- **Name:** `spark-code-interpreter-app`
- **Release:** EMR 7.0.0
- **State:** STOPPED (auto-stop enabled, 15 min idle timeout)
- **Architecture:** X86_64
- **VPC Configuration:** ❌ **NOT IN VPC** (public mode)
- **Initial Capacity:**
  - Driver: 1 worker (2 vCPU, 4 GB memory, 20 GB disk)
  - Executor: 2 workers (4 vCPU, 8 GB memory, 20 GB disk each)
- **CloudWatch Logging:** Enabled (`/aws/emr-serverless/00fv6g7rptsov009`)

**CRITICAL ISSUE:** EMR Serverless is NOT configured with VPC, so it CANNOT access Aurora PostgreSQL in private VPC.

### 17.3 Current Lambda Configuration

**Function Details:**
- **Function Name:** `sparkOnLambda-spark-code-interpreter`
- **Runtime:** Container image (ECR)
- **Memory:** 3008 MB
- **Timeout:** 300 seconds (5 minutes)
- **Ephemeral Storage:** 2048 MB
- **VPC Configuration:** ❌ **NOT IN VPC**
- **Architecture:** x86_64

**CRITICAL ISSUE:** Lambda is NOT in VPC, so it CANNOT access Aurora PostgreSQL.

### 17.4 VPC Subnet Analysis

**Available Subnets in vpc-0485dcc1f1d050b55:**

**Public Subnets (MapPublicIpOnLaunch: true):**
- `subnet-0ffcc9c369d011e54` - us-east-1a - 172.31.0.0/20 (4083 IPs available)
- `subnet-04c2c799482ddc064` - us-east-1b - 172.31.80.0/20 (4078 IPs available)
- `subnet-0d463b21f9ea0e54d` - us-east-1c - 172.31.16.0/20 (4058 IPs available)
- `subnet-0eac3aa700b1bd035` - us-east-1d - 172.31.32.0/20 (4078 IPs available)
- `subnet-02bda43701f70370e` - us-east-1e - 172.31.48.0/20 (4087 IPs available)
- `subnet-0a3fbc0b127093e5d` - us-east-1f - 172.31.64.0/20 (4061 IPs available)

**Private Subnets (MapPublicIpOnLaunch: false):**
- `subnet-006b1a09bd82fd9f7` - us-east-1a - 172.31.208.0/20 (4091 IPs) - "default-private-subnet-1a"
- `subnet-016fb407bc2a3e4c0` - us-east-1b - 172.31.224.0/20 (4091 IPs) - "default-private-subnet-1b"
- `subnet-09cc990e2dd228cdc` - us-east-1c - 172.31.240.0/20 (4091 IPs) - "default-private-subnet-1c"
- `subnet-0aa61f52d0c32b401` - us-east-1a - 172.31.100.0/28 (7 IPs) - "private_test"

**Recommendation:** Use the three "default-private-subnet" subnets for EMR/Lambda VPC configuration.

---

### 17.5 REQUIRED INFRASTRUCTURE CHANGES

#### Change 1: NEW EMR Serverless Application for PostgreSQL (COMPLETED)

**Decision:** Create separate EMR application for PostgreSQL instead of modifying existing one

**Rationale:**
- Keeps existing S3/Glue workflows unchanged
- Isolates PostgreSQL functionality
- Allows independent scaling and configuration
- Easy rollback if issues occur

**New Application Created:**
- **Application ID:** `00g0oddl52n83r09`
- **Name:** `spark-postgres-interpreter-app`
- **ARN:** `arn:aws:emr-serverless:us-east-1:260005718447:/applications/00g0oddl52n83r09`
- **Release:** EMR 7.0.0
- **Architecture:** X86_64
- **State:** CREATED

**VPC Configuration:**
- **Subnets:** 
  - `subnet-006b1a09bd82fd9f7` (us-east-1a, private)
  - `subnet-016fb407bc2a3e4c0` (us-east-1b, private)
  - `subnet-09cc990e2dd228cdc` (us-east-1c, private)
- **Security Group:** `sg-098a735e14f9f2953` (same as Aurora)

**Capacity Configuration:**
- **Driver:** 1 worker (2 vCPU, 4 GB memory, 20 GB disk)
- **Executor:** 2 workers (4 vCPU, 8 GB memory, 20 GB disk each)
- **Maximum:** 400 vCPU, 1000 GB memory, 400 TB disk

**Auto-Configuration:**
- **Auto-Start:** Enabled
- **Auto-Stop:** Enabled (15 minutes idle timeout)

**Monitoring:**
- **CloudWatch Logging:** Enabled (stdout, stderr for driver and executor)
- **Managed Persistence:** Enabled

**Status:** ✅ CREATED AND READY

**Existing EMR Application (Unchanged):**
- **Application ID:** `00fv6g7rptsov009`
- **Name:** `spark-code-interpreter-app`
- **VPC:** None (public mode)
- **Usage:** S3 CSV files, Glue Catalog tables
- **Status:** Remains unchanged, continues to work as before



#### Change 2: Add NAT Gateway (if not exists)

**Check if NAT Gateway exists:**
```bash
aws ec2 describe-nat-gateways \
  --filter "Name=vpc-id,Values=vpc-0485dcc1f1d050b55" \
  --region us-east-1
```

**If no NAT Gateway, create one:**
```bash
# 1. Allocate Elastic IP
aws ec2 allocate-address --domain vpc --region us-east-1

# 2. Create NAT Gateway in public subnet
aws ec2 create-nat-gateway \
  --subnet-id subnet-0ffcc9c369d011e54 \
  --allocation-id <eip-allocation-id> \
  --region us-east-1

# 3. Update route table for private subnets
aws ec2 create-route \
  --route-table-id <private-route-table-id> \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id <nat-gateway-id> \
  --region us-east-1
```

**Why Needed:**
- EMR in private subnet needs internet access for:
  - Bedrock API calls (code generation)
  - S3 access (JDBC driver, code, results)
  - CloudWatch Logs
  - Secrets Manager API

#### Change 3: Update Lambda Function for VPC Access (Optional)

**Current State:** Lambda not in VPC  
**Decision:** Keep Lambda out of VPC for now

**Rationale:**
- Lambda is only used for small CSV files (< 100 MB)
- PostgreSQL queries will always use EMR (forced in platform selection)
- Adding Lambda to VPC increases cold start time
- Lambda doesn't need Aurora access for current use cases

**If Future Requirement:** Update Lambda VPC configuration:
```bash
aws lambda update-function-configuration \
  --function-name sparkOnLambda-spark-code-interpreter \
  --vpc-config SubnetIds=subnet-006b1a09bd82fd9f7,subnet-016fb407bc2a3e4c0,subnet-09cc990e2dd228cdc,SecurityGroupIds=sg-098a735e14f9f2953 \
  --region us-east-1
```

#### Change 4: Update Security Group Rules (Optional Enhancement)

**Current Rules:** Self-referencing allows all traffic within security group  
**Enhancement:** Add explicit rule for clarity (optional)

```bash
# Add explicit PostgreSQL rule (optional - already covered by self-referencing)
aws ec2 authorize-security-group-ingress \
  --group-id sg-098a735e14f9f2953 \
  --protocol tcp \
  --port 5432 \
  --source-group sg-098a735e14f9f2953 \
  --region us-east-1 \
  --group-owner-id 260005718447
```

**Note:** This is redundant since self-referencing rule already exists, but makes intent explicit.

#### Change 5: Create Secrets Manager Secret

**Create secret for Aurora connection:**
```bash
aws secretsmanager create-secret \
  --name spark/postgres/aurora-prod \
  --description "Aurora PostgreSQL connection for Spark" \
  --secret-string '{
    "connection_name": "aurora-prod",
    "host": "pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com",
    "port": 5432,
    "database": "postgres",
    "username": "postgres",
    "password": "YOUR_PASSWORD_HERE",
    "jdbc_url": "jdbc:postgresql://pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres"
  }' \
  --region us-east-1
```

**Enable automatic rotation (optional):**
```bash
aws secretsmanager rotate-secret \
  --secret-id spark/postgres/aurora-prod \
  --rotation-lambda-arn <rotation-lambda-arn> \
  --rotation-rules AutomaticallyAfterDays=30 \
  --region us-east-1
```

#### Change 6: Update EMR Execution Role IAM Policy

**Get current execution role:**
```bash
# From EMR job runs or config
EXECUTION_ROLE_ARN="arn:aws:iam::260005718447:role/EMRServerlessExecutionRole"
```

**Add Secrets Manager permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/*"
    },
    {
      "Sid": "JDBCDriverAccess",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::spark-data-260005718447-us-east-1/jars/*"
    }
  ]
}
```

**Apply policy:**
```bash
aws iam put-role-policy \
  --role-name EMRServerlessExecutionRole \
  --policy-name PostgreSQLAccess \
  --policy-document file://postgres-policy.json \
  --region us-east-1
```

#### Change 7: Upload PostgreSQL JDBC Driver to S3

**Download and upload driver:**
```bash
# Download PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.1.jar

# Upload to S3
aws s3 cp postgresql-42.7.1.jar \
  s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.1.jar \
  --region us-east-1
```

**Verify upload:**
```bash
aws s3 ls s3://spark-data-260005718447-us-east-1/jars/ --region us-east-1
```

---

### 17.6 CONFIGURATION UPDATES IN CODE

#### Update 1: backend/config.py

**Add PostgreSQL configuration with actual values:**
```python
"postgres": {
    "connections": [
        {
            "name": "aurora-prod",
            "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod",
            "description": "Production Aurora PostgreSQL 16.8",
            "enabled": True
        }
    ],
    "default_connection": "aurora-prod",
    "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.1.jar",
    "connection_timeout": 10,
    "query_timeout": 30
}
```

#### Update 2: backend/spark-supervisor-agent/spark_supervisor_agent.py

**Update platform selection to force EMR for PostgreSQL:**
```python
@tool
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """
    CRITICAL: PostgreSQL queries MUST use EMR (VPC required)
    """
    config = get_config()
    
    # Check for PostgreSQL tables in session
    if CURRENT_SESSION_ID:
        session_data = prompt_sessions.get(CURRENT_SESSION_ID, {})
        if session_data.get('postgres_tables'):
            return 'emr'  # FORCE EMR - Lambda not in VPC
    
    # Existing logic...
    threshold = config.get('file_size_threshold_mb', 100)
    if file_size_mb > threshold:
        return 'emr'
    else:
        return 'lambda'
```

#### Update 3: EMR Job Submission

**Ensure VPC configuration is used:**
```python
def execute_spark_code_emr(spark_code: str, s3_output_path: str) -> dict:
    # ... existing code ...
    
    # VPC configuration is now part of EMR application
    # No need to specify in job submission
    # Security group sg-098a735e14f9f2953 allows Aurora access
    
    response = emr_client.start_job_run(
        applicationId=config['emr_application_id'],  # 00fv6g7rptsov009
        executionRoleArn=execution_role,
        jobDriver={
            'sparkSubmit': {
                'entryPoint': s3_code_path,
                'sparkSubmitParameters': f'--jars {jdbc_driver} --conf spark.executor.instances=2'
            }
        },
        # ... rest of configuration ...
    )
```

---

### 17.7 TESTING CHECKLIST

**Pre-Implementation Tests:**
- [ ] Verify NAT Gateway exists in VPC
- [ ] Verify private subnet route tables point to NAT Gateway
- [ ] Test Aurora connectivity from EC2 instance in same VPC
- [ ] Verify Secrets Manager secret created and accessible

**Post-EMR VPC Configuration:**
- [ ] Start EMR application and verify it starts successfully
- [ ] Check EMR application can access S3 (download JDBC driver)
- [ ] Check EMR application can access Secrets Manager
- [ ] Check EMR application can reach Bedrock API
- [ ] Test simple Spark job without PostgreSQL

**Post-PostgreSQL Integration:**
- [ ] Test metadata fetching (list databases, schemas, tables)
- [ ] Test code generation with PostgreSQL tables
- [ ] Test EMR job execution with PostgreSQL query
- [ ] Verify results written to S3
- [ ] Check CloudWatch logs for any errors

---

### 17.8 ROLLBACK PLAN FOR INFRASTRUCTURE CHANGES

**If EMR VPC Configuration Causes Issues:**
```bash
# Remove VPC configuration from EMR application
aws emr-serverless update-application \
  --application-id 00fv6g7rptsov009 \
  --region us-east-1 \
  --network-configuration '{}'
```

**Impact of Rollback:**
- EMR returns to public mode
- PostgreSQL integration will not work
- All other features (S3, Glue) continue to work
- No data loss

---

### 17.9 COST IMPLICATIONS

**New Costs:**
- **NAT Gateway:** ~$0.045/hour + $0.045/GB data processed (~$32/month + data transfer)
- **Secrets Manager:** $0.40/secret/month + $0.05/10,000 API calls
- **EMR in VPC:** No additional cost (same as public mode)
- **VPC Endpoints (optional):** $0.01/hour per endpoint (~$7/month per endpoint)

**Cost Optimization:**
- Use VPC endpoints for S3 and Secrets Manager to avoid NAT Gateway data transfer charges
- Enable EMR auto-stop (already configured: 15 min idle timeout)
- Use Aurora Serverless v2 auto-scaling (already configured: 2-10 ACU)

**Estimated Monthly Cost Increase:** $35-50/month (primarily NAT Gateway)

---

### 17.10 SECURITY CONSIDERATIONS FOR ACTUAL SETUP

**Current Security Posture:**
- ✅ Aurora encryption at-rest (KMS)
- ✅ IAM database authentication enabled
- ✅ Security group restricts access
- ✅ Private subnets available
- ❌ Aurora has external IP access (108.24.105.184/32)
- ❌ EMR not in VPC (public mode)

**Recommended Security Enhancements:**
1. Remove external IP access to Aurora (port 5432 from 108.24.105.184/32)
2. Use IAM database authentication instead of password
3. Enable VPC Flow Logs for audit trail
4. Use VPC endpoints for S3 and Secrets Manager
5. Enable CloudTrail for API audit logging
6. Rotate database credentials regularly (Secrets Manager rotation)

**IAM Database Authentication (Recommended):**
```python
# In generated Spark code, use IAM auth instead of password
import boto3

# Generate auth token
rds_client = boto3.client('rds', region_name='us-east-1')
token = rds_client.generate_db_auth_token(
    DBHostname='pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com',
    Port=5432,
    DBUsername='postgres',
    Region='us-east-1'
)

# Use token as password in JDBC connection
df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/database") \
    .option("user", "postgres") \
    .option("password", token) \
    .option("driver", "org.postgresql.Driver") \
    .load()
```

---

**END OF INFRASTRUCTURE ANALYSIS**


### 5.6 Dual EMR Application Logic

**Update execute_spark_code_emr to select correct application:**

```python
def execute_spark_code_emr(spark_code: str, s3_output_path: str, use_postgres: bool = False) -> dict:
    """
    Execute Spark code on appropriate EMR Serverless application
    
    Args:
        use_postgres: If True, use VPC-enabled PostgreSQL EMR app (00g0oddl52n83r09)
                     If False, use standard EMR app (00fv6g7rptsov009)
    """
    config = get_config()
    
    # Select EMR application based on data source
    if use_postgres:
        app_id = config.get('emr_postgres_application_id', '00g0oddl52n83r09')
        jdbc_driver = config.get('postgres', {}).get('jdbc_driver_path', '')
    else:
        app_id = config.get('emr_application_id', '00fv6g7rptsov009')
        jdbc_driver = ''
    
    # Build spark-submit parameters
    spark_params = '--conf spark.executor.instances=2'
    if jdbc_driver:
        spark_params += f' --jars {jdbc_driver}'
    
    # Start job on selected application
    response = emr_client.start_job_run(
        applicationId=app_id,
        executionRoleArn=execution_role,
        jobDriver={'sparkSubmit': {
            'entryPoint': s3_code_path,
            'sparkSubmitParameters': spark_params
        }},
        # ... rest of config ...
    )
```

**Update system prompt to pass use_postgres flag:**

```
5. VALIDATION EXECUTION:
   - If selected_postgres_tables provided:
     Call execute_spark_code_emr(code, path, use_postgres=True)
   - Elif selected_tables provided (Glue):
     Call execute_spark_code_emr(code, path, use_postgres=False)
   - Else (S3 CSV):
     Call execute_spark_code_lambda(code, path)
```

