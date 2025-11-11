import requests
import time

# Upload CSV
csv_content = "date,price,volume\n2024-01-01,150.5,1000\n2024-01-02,152.3,1200\n2024-01-03,148.9,900"
resp = requests.post(
    "http://localhost:8000/upload-csv",
    json={"filename": "stock.csv", "content": csv_content, "session_id": "s3test"},
    timeout=10
)
print(f"CSV upload: {resp.json()}")
s3_path = resp.json()["s3_path"]

# Generate code to read from S3
resp = requests.post(
    "http://localhost:8000/generate",
    json={"prompt": "Read the CSV and calculate average price", "session_id": "s3test"},
    timeout=30
)
code = resp.json()["code"]
print(f"\nGenerated code:\n{code}\n")

# Execute
resp = requests.post(
    "http://localhost:8000/execute",
    json={"code": code, "session_id": "s3test"},
    timeout=90
)
result = resp.json()
print(f"Execution success: {result['success']}")
print(f"Output:\n{result['result']}")
