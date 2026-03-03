import requests, json, time
r = requests.post("http://localhost:8000/spark/generate", json={
    "prompt": "find top 10 products by order total",
    "session_id": f"pg-clean-{int(time.time())}",
    "framework": "spark",
    "execution_platform": "emr",
    "selected_postgres_tables": [{
        "connection_name": "aurora", "database": "postgres", "schema": "public", "table": "order_details",
        "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
        "auth_method": "user_password",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
        "host": "pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com", "port": 5432,
        "columns": [{"name": "order_id", "type": "smallint"}, {"name": "product_id", "type": "smallint"}, 
                   {"name": "unit_price", "type": "real"}, {"name": "quantity", "type": "smallint"}, {"name": "discount", "type": "real"}]
    }]
}, timeout=900)
print(f"Status: {r.status_code}")
result = r.json()
if result.get("success"):
    code = result.get("result", {}).get("spark_code", "")
    has_jdbc = "jdbc:postgresql" in code
    has_secrets = "get_secret_value" in code
    print(f"JDBC: {'✓' if has_jdbc else '✗'}, Secrets: {'✓' if has_secrets else '✗'}")
    print(f"Result: {result.get('result', {}).get('execution_result')}")
else:
    print(f"Error: {result.get('error')}")
