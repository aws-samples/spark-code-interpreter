## Ray Code Interpreter

A web-based code interpreter that generates and executes Ray data processing code on an ECS-hosted Ray cluster with automatic error correction.

### Features

- 🤖 **AI-Powered Code Generation**: Uses AWS Bedrock Claude Sonnet 4.5 to generate Ray code
- 🔄 **Iterative Validation**: Automatically tests and fixes code errors (up to 3 attempts)
- ⚡ **Auto-Execution**: Only validated code is executed on full dataset
- 🖥️ **Remote Execution**: Executes code on Ray ECS cluster (Ray 2.42.0)
- 📊 **Embedded Dashboard**: View Ray cluster metrics and job status
- 📁 **CSV Upload**: Upload CSV files to S3 for cluster access
- 🗄️ **Glue Data Catalog**: Browse and select databases/tables from AWS Glue
- 🎨 **Modern UI**: Built with React and AWS Cloudscape Design System
- 🔍 **Clean Output**: Filters Ray logs to show only user output
- 📜 **Session History**: Track all code generations and executions
- 🛡️ **Safety Protections**: Automatic safeguards against infinite loops

### Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   React     │─────▶│   FastAPI    │─────▶│  Ray Cluster    │
│   Frontend  │      │   Backend    │      │  (ECS Fargate)  │
│             │◀─────│  + Validator │◀─────│                 │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │                        │
                            ▼                        ▼
                     ┌──────────────┐        ┌─────────────┐
                     │   Bedrock    │        │  S3 + Glue  │
                     │   (Claude)   │        │  (Data)     │
                     └──────────────┘        └─────────────┘
```

### How It Works

1. **Select Data Sources**: Choose CSV files and/or Glue tables from left panel
2. **User Request**: Describe data processing task in natural language
3. **Code Generation**: Agent generates Ray code using selected data sources
4. **Validation**: Agent tests code on Ray cluster (up to 3 attempts with auto-fix)
5. **Auto-Execution**: Validated code is executed on full dataset
6. **Results Display**: Execution results are automatically shown in UI
7. **Re-execution**: User can re-run from history or edit code and re-execute

### Prerequisites

- Python 3.8+
- Node.js 16+
- AWS credentials configured
- Ray ECS cluster running (see `../ecs-deployment`)

### Ray Cluster Requirements

The following packages must be installed on the Ray cluster:

```bash
# On Ray cluster
pip install awswrangler>=3.0.0 pyarrow>=10.0.0 pyathena>=3.0.0
```

Or use the provided requirements file:
```bash
pip install -r ray-cluster-requirements.txt
```

**Installed packages:**
- `awswrangler` (3.13.0) - AWS Data Wrangler for Athena queries
- `pyarrow` (14.0.2) - Efficient parquet file reading
- `pyathena` (3.18.0) - Athena database connections for ray.data.read_sql()

### Glue Data Catalog with LakeFormation

The application supports reading Glue tables with automatic fallback for LakeFormation permissions:

1. **Direct S3 Read (Default)**: Tries `ray.data.read_parquet()` from table location (faster)
2. **SQL Fallback**: If permission denied, automatically uses `ray.data.read_sql()` with Athena

This ensures tables work even with LakeFormation fine-grained access controls.

### Setup

1. **Install backend dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Install frontend dependencies**:
```bash
cd frontend
npm install
```

3. **Configure environment**:
Edit `backend/.env`:
```
AWS_REGION=us-east-1
AWS_PROFILE=default
RAY_HEAD_IP=13.220.45.214
```

### Running

**Start both frontend and backend**:
```bash
chmod +x start.sh stop.sh
./start.sh
```

**Or start separately**:

Backend:
```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

### Usage

1. **Generate Code**: Describe your data processing task in natural language
2. **Edit Code**: Review and modify the generated Ray code
3. **Execute**: Run the code on the Ray cluster
4. **View Results**: See execution output and logs
5. **Monitor**: Check Ray dashboard for cluster metrics

### Example Prompts

- "Create a dataset with 10000 rows and calculate squared values"
- "Read data, filter rows where value > 100, and group by category"
- "Process 50000 records with map and reduce operations"
- "Create a data pipeline with transformations and aggregations"

### API Endpoints

- `POST /generate` - Generate Ray code from prompt
- `POST /execute` - Execute Ray code on cluster
- `GET /ray/status` - Get Ray cluster status
- `GET /history/{session_id}` - Get session history

### Components

**Frontend**:
- `App.jsx` - Main application
- `CodeEditor.jsx` - Code editing interface
- `ExecutionResults.jsx` - Display execution output
- `RayDashboard.jsx` - Embedded Ray dashboard

**Backend**:
- `main.py` - FastAPI server with Ray integration

### Ray Cluster

The code executes on a Ray 2.42.0 cluster running on AWS ECS Fargate:
- Head node: 13.220.45.214
- Dashboard: http://13.220.45.214:8265
- Auto-scaling: 0-5 workers

### Stopping

```bash
./stop.sh
```

### Troubleshooting

**Backend won't start**:
- Check AWS credentials: `aws sts get-caller-identity`
- Verify Ray cluster is running: `curl http://13.220.45.214:8265/api/version`

**Code execution fails**:
- Check Ray cluster status in dashboard
- Verify network connectivity to Ray head node
- Check backend logs for errors

**Frontend won't connect**:
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings

### Development

**Backend**:
```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend
npm run dev
```

### Production Build

```bash
cd frontend
npm run build
```

Serve the `dist` folder with any static file server.
