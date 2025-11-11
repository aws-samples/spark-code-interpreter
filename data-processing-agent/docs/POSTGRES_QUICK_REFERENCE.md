# PostgreSQL Integration - Quick Reference Card

**Last Updated:** 2025-10-30

---

## 🔑 KEY RESOURCES

| Resource | Value |
|----------|-------|
| **Secret ARN** | `arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod-ltLn9I` |
| **JDBC Driver** | `s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar` |
| **Aurora Endpoint** | `pg-database.cluster-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432` |
| **EMR Standard** | `00fv6g7rptsov009` (S3/Glue) |
| **EMR PostgreSQL** | `00g0oddl52n83r09` (VPC-enabled) |
| **Agent ARN** | `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR` |

---

## 🚀 QUICK COMMANDS

### Test Backend:
```bash
cd backend
conda run -n bedrock-sdk uvicorn main:app --reload
curl http://localhost:8000/postgres/connections
```

### Deploy Agent:
```bash
cd backend/spark-supervisor-agent
conda run -n bedrock-sdk python agent_deployment.py
```

### Test Metadata:
```python
from backend.postgres_metadata import get_postgres_metadata_fetcher
fetcher = get_postgres_metadata_fetcher()
databases = fetcher.list_databases("arn:aws:secretsmanager:...")
```

### View Logs:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --log-stream-name-prefix "2025/10/30/[runtime-logs]" --follow
```

---

## 📋 API ENDPOINTS

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/postgres/connections` | List connections |
| GET | `/postgres/{conn}/databases` | List databases |
| GET | `/postgres/{conn}/schemas/{db}` | List schemas |
| GET | `/postgres/{conn}/tables/{db}/{schema}` | List tables |
| POST | `/sessions/{id}/select-postgres-tables` | Store selections |

---

## 📁 FILES MODIFIED

### Created:
- `backend/postgres_metadata.py` ✅
- `POSTGRES_IMPLEMENTATION_LOG.md` ✅
- `INFRASTRUCTURE_DEPLOYMENT_GUIDE.md` ✅
- `POSTGRES_INTEGRATION_SUMMARY.md` ✅

### Updated:
- `backend/config.py` ✅
- `backend/requirements.txt` ✅
- `backend/main.py` ✅
- `backend/spark-supervisor-agent/spark_supervisor_agent.py` ✅

### Not Modified (as required):
- `backend/code-generation-agent/` ✅
- `backend/supervisor-agent/` ✅

---

## 🔧 CONFIGURATION

### config.py:
```python
"postgres": {
    "connections": [{
        "name": "aurora-prod",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod-ltLn9I",
        "enabled": True
    }],
    "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar"
}
```

### Credentials:
- **Username:** `pg-spark`
- **Password:** `Pg@spark`
- **Database:** `postgres`

---

## ✅ STATUS CHECKLIST

### Infrastructure:
- [x] JDBC driver in S3
- [x] Secrets Manager secret created
- [x] EMR PostgreSQL app created
- [x] VPC configuration complete
- [ ] NAT Gateway verified
- [ ] IAM permissions verified

### Backend:
- [x] postgres_metadata.py created
- [x] API endpoints added
- [x] config.py updated
- [x] requirements.txt updated

### Agent:
- [x] Spark Supervisor updated
- [x] Agent deployed
- [x] PostgreSQL support added
- [x] Dual EMR logic implemented

### Frontend:
- [ ] PostgresTableSelector.jsx
- [ ] App.jsx updates
- [ ] Settings.jsx updates

### Testing:
- [ ] Backend endpoints tested
- [ ] Metadata fetching tested
- [ ] Code generation tested
- [ ] EMR execution tested
- [ ] End-to-end tested

---

## 🐛 TROUBLESHOOTING

| Issue | Quick Fix |
|-------|-----------|
| Connection timeout | Check NAT Gateway and security groups |
| Access denied | Verify IAM role permissions |
| JDBC driver not found | Check S3 path and permissions |
| Auth failed | Verify credentials in Secrets Manager |

---

## 📚 DOCUMENTATION

| Document | Purpose |
|----------|---------|
| `POSTGRES_INTEGRATION_SPEC.md` | Full specification |
| `POSTGRES_IMPLEMENTATION_LOG.md` | Implementation details |
| `INFRASTRUCTURE_DEPLOYMENT_GUIDE.md` | Deployment steps |
| `POSTGRES_INTEGRATION_SUMMARY.md` | Executive summary |
| `POSTGRES_QUICK_REFERENCE.md` | This file |

---

## 🎯 NEXT STEPS

1. **Frontend:** Create PostgresTableSelector.jsx (4-6 hours)
2. **Testing:** End-to-end query execution (2-3 hours)
3. **IAM:** Verify permissions (30 minutes)

---

## 💰 COST

**Monthly:** ~$35-50
- NAT Gateway: $32
- Secrets Manager: $0.40
- Other: ~$2-18

---

## 🔒 SECURITY

- ✅ Credentials in Secrets Manager
- ✅ VPC isolation
- ✅ Security groups configured
- ✅ Encryption at-rest
- ⏳ IAM database auth (recommended)
- ⏳ VPC endpoints (recommended)

---

**For detailed information, see full documentation files.**
