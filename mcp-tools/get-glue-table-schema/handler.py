"""MCP Tool: get_glue_table_schema
Fetch detailed schema for an AWS Glue table and extract a 200-row sample as CSV.
The sample enables validation on Lambda without needing Glue catalog support.
"""

import json
import boto3
from io import StringIO, BytesIO


def _extract_sample(s3_client, location, s3_bucket, session_id, table_name, sample_size_mb=100):
    """Extract a size-based sample from the table's S3 location and save as CSV.

    Returns (sample_path, data_file_size_bytes, error).
    data_file_size_bytes is the full size of the first data file (before sampling),
    used by the caller to determine whether is_small applies.
    """
    try:
        import pandas as pd
    except ImportError:
        return None, 0, "pandas not available"

    # Parse S3 location
    if not location or not location.startswith("s3://"):
        return None, 0, "No valid S3 location"

    bucket = location.replace("s3://", "").split("/")[0]
    prefix = "/".join(location.replace("s3://", "").split("/")[1:])
    if not prefix.endswith("/"):
        prefix += "/"

    # List files at the location
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=10)
    except Exception as e:
        return None, None, (
            f"AccessDenied: s3://{bucket} is not accessible to the MCP Lambda role. "
            f"Add arn:aws:s3:::{bucket} and arn:aws:s3:::{bucket}/* to the S3 policy in deploy-mcp-tools.sh"
        )
    contents = response.get("Contents", [])

    # Find first data file (CSV or Parquet)
    data_files = [
        obj for obj in contents
        if not obj["Key"].endswith("/")
        and not obj["Key"].endswith("_SUCCESS")
        and not obj["Key"].endswith(".crc")
        and obj["Size"] > 0
    ]

    if not data_files:
        return None, 0, "No data files found at table location"

    first_file_obj = data_files[0]
    first_file = first_file_obj["Key"]
    data_file_size_bytes = first_file_obj["Size"]

    sample_size_bytes = sample_size_mb * 1024 * 1024

    # Read up to sample_size_bytes from the first data file
    if first_file.endswith(".parquet"):
        # For Parquet, read the whole file up to the byte limit then trim rows
        byte_range = f"bytes=0-{sample_size_bytes - 1}" if data_file_size_bytes > sample_size_bytes else None
        get_kwargs = {"Bucket": bucket, "Key": first_file}
        if byte_range:
            get_kwargs["Range"] = byte_range
        raw = s3_client.get_object(**get_kwargs)["Body"].read()
        df = pd.read_parquet(BytesIO(raw))
    else:
        # For CSV, stream up to sample_size_bytes
        get_kwargs = {"Bucket": bucket, "Key": first_file}
        if data_file_size_bytes > sample_size_bytes:
            get_kwargs["Range"] = f"bytes=0-{sample_size_bytes - 1}"
        raw_bytes = s3_client.get_object(**get_kwargs)["Body"].read()
        # Trim to last complete line
        if data_file_size_bytes > sample_size_bytes:
            last_newline = raw_bytes.rfind(b"\n")
            if last_newline > 0:
                raw_bytes = raw_bytes[: last_newline + 1]
        content = raw_bytes.decode("utf-8", errors="ignore")
        lines = content.strip().split("\n")
        if len(lines) > 1:
            first_row = lines[0].split(",")
            has_header = any(
                not val.strip().replace(".", "").replace("-", "").isdigit()
                for val in first_row if val.strip()
            )
        else:
            has_header = False
        df = pd.read_csv(StringIO(content), header=0 if has_header else None,
                         quotechar='"', on_bad_lines='skip')

    # Save as CSV to session-specific path
    sample_key = f"{session_id}/samples/{table_name}_sample.csv"
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    s3_client.put_object(
        Bucket=s3_bucket,
        Key=sample_key,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )

    sample_path = f"s3://{s3_bucket}/{sample_key}"
    return sample_path, data_file_size_bytes, None


def lambda_handler(event, context):
    try:
        database_name = event["database_name"]
        table_name = event["table_name"]
        region = event.get("region", "us-east-1")
        s3_bucket = event.get("s3_bucket", "")
        session_id = event.get("session_id", "")
        sample_size_mb = int(event.get("sample_size_mb", 100))

        from progress import update_progress
        update_progress(s3_bucket, session_id, "get_glue_table_schema", "running",
                        f"Fetching schema for {database_name}.{table_name}...", region)

        glue_client = boto3.client("glue", region_name=region)
        s3_client = boto3.client("s3", region_name=region)

        response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        table = response["Table"]

        storage_desc = table.get("StorageDescriptor", {})
        columns = [
            {"name": col["Name"], "type": col["Type"], "comment": col.get("Comment", "")}
            for col in storage_desc.get("Columns", [])
        ]
        partition_keys = [
            {"name": pk["Name"], "type": pk["Type"]}
            for pk in table.get("PartitionKeys", [])
        ]

        location = storage_desc.get("Location", "")

        result = {
            "status": "success",
            "database": database_name,
            "table": table_name,
            "location": location,
            "input_format": storage_desc.get("InputFormat", ""),
            "output_format": storage_desc.get("OutputFormat", ""),
            "columns": columns,
            "partition_keys": partition_keys,
            "table_type": table.get("TableType", ""),
            "parameters": table.get("Parameters", {}),
        }

        # Extract sample data if s3_bucket and session_id provided
        if s3_bucket and session_id and location:
            sample_path, data_file_size_bytes, error = _extract_sample(
                s3_client, location, s3_bucket, session_id, table_name, sample_size_mb
            )
            if sample_path:
                result["sample_s3_path"] = sample_path
                result["data_file_size_bytes"] = data_file_size_bytes
            elif error:
                result["sample_error"] = error

        update_progress(s3_bucket, session_id, "get_glue_table_schema", "complete",
                        f"Schema fetched: {len(columns)} columns" +
                        (f", sample at {result.get('sample_s3_path', 'N/A')}" if result.get("sample_s3_path") else ""),
                        region)

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error": str(e),
                "database": event.get("database_name", ""),
                "table": event.get("table_name", ""),
            }),
        }
