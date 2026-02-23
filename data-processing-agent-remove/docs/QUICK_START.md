# Quick Start Guide

## Application is Ready! ✅

Both backend and frontend are running and fully functional.

## Access

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Features Available

### 1. Generate Ray Code
1. Go to "Generate Code" tab
2. Enter a prompt (e.g., "Create a dataset with 1000 rows")
3. Click "Generate Ray Code"
4. Code is automatically generated and executed
5. Results appear in "Execution Results" tab

### 2. Upload CSV
1. Click "Upload CSV" button in Generate Code tab
2. Select a CSV file
3. Preview appears
4. Generate code that uses the CSV
5. CSV path automatically included in generated code

### 3. Select Glue Tables
1. Open "Glue Data Catalog" in left sidebar
2. Select a database from dropdown
3. Select one or more tables
4. Click "Apply Selection"
5. Tables appear in "Selected Tables" section
6. Generate code that uses the tables

### 4. Edit and Execute Code
1. Go to "Code Editor" tab
2. Edit the generated code
3. Click "Execute on Ray Cluster"
4. Results appear in "Execution Results" tab

### 5. View History
1. Go to "Session History" tab
2. Click "Load History"
3. View all code generations and executions
4. Click "Re-execute" to run code again
5. Click "View Details" to see full code and results

### 6. Configure Settings
1. Go to "Settings" tab
2. Update Ray cluster IPs
3. Update S3 bucket name
4. Click "Save Settings"
5. Settings persist across restarts

### 7. Monitor Ray Cluster
1. Go to "Ray Dashboard" tab
2. View cluster status
3. Monitor running jobs
4. View job logs
5. Stop jobs if needed

## Example Workflows

### Workflow 1: Simple Data Processing
```
1. Generate Code tab
2. Enter: "Create a dataset with 1000 rows, add a squared column"
3. Click "Generate Ray Code"
4. View results automatically
```

### Workflow 2: CSV Processing
```
1. Click "Upload CSV"
2. Select your CSV file
3. Enter: "Read the CSV and calculate statistics"
4. Click "Generate Ray Code"
5. View results with CSV data
```

### Workflow 3: Glue Table Processing
```
1. Open Glue Data Catalog
2. Select database: "northwind"
3. Select tables: "customers", "orders"
4. Click "Apply Selection"
5. Enter: "Join customers and orders tables"
6. Click "Generate Ray Code"
7. View results with joined data
```

## API Endpoints

### Code Generation
```bash
POST http://localhost:8000/generate
Body: {"prompt": "your prompt", "session_id": "uuid"}
```

### Code Execution
```bash
POST http://localhost:8000/execute
Body: {"code": "your code", "session_id": "uuid"}
```

### CSV Upload
```bash
POST http://localhost:8000/upload-csv
Body: {"filename": "data.csv", "content": "csv content", "session_id": "uuid"}
```

### Glue Databases
```bash
GET http://localhost:8000/glue/databases
```

### Glue Tables
```bash
GET http://localhost:8000/glue/tables/{database}
```

### Select Tables
```bash
POST http://localhost:8000/sessions/{session_id}/select-tables
Body: {"tables": [{"database": "db", "table": "tbl"}], "session_id": "uuid"}
```

### Settings
```bash
GET http://localhost:8000/settings
POST http://localhost:8000/settings
Body: {"ray_private_ip": "...", "ray_public_ip": "...", "s3_bucket": "..."}
```

### Session History
```bash
GET http://localhost:8000/history/{session_id}
```

### Ray Status
```bash
GET http://localhost:8000/ray/status
```

### Ray Jobs
```bash
GET http://localhost:8000/ray/jobs
POST http://localhost:8000/ray/jobs/{job_id}/stop
```

## Troubleshooting

### Backend Not Running
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Not Running
```bash
cd frontend
npm run dev
```

### Check Logs
```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

### Verify Services
```bash
# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000
```

## Configuration

### Ray Cluster IPs
Edit via Settings tab or directly in `config.yaml`:
```yaml
ray_cluster:
  private_ip: "172.31.4.12"
  public_ip: "100.27.32.218"
```

### S3 Bucket
Edit via Settings tab or directly in `config.yaml`:
```yaml
s3:
  bucket: "strands-ray-data"
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Browser                         │
│                 http://localhost:3000                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                │
│  • /generate  • /execute  • /upload-csv                 │
│  • /glue/*    • /settings • /history                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Supervisor Agent Runtime (AgentCore)           │
│  Orchestrates: Code Gen + Validation + Execution        │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│ Code Gen Agent   │    │   MCP Gateway    │
│   (AgentCore)    │    │   + Lambda       │
└──────────────────┘    └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   Ray Cluster    │
                        │  (ECS Fargate)   │
                        └──────────────────┘
```

## Support

For issues or questions:
1. Check logs: `backend.log` and `frontend.log`
2. Verify services are running
3. Check Ray cluster is accessible
4. Verify AWS credentials for Glue/S3

## Summary

✅ Application is fully functional
✅ All features integrated
✅ Settings tab working
✅ No simulations - all real endpoints
✅ Ready for production use

**Enjoy using the Ray Code Interpreter!** 🚀
