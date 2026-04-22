"""Shared progress tracking for MCP tool Lambdas.

Writes progress updates to S3 so the frontend can poll for real-time status.
Progress file: s3://{bucket}/{session_id}/progress.json
"""

import json
import time
import boto3


def update_progress(s3_bucket, session_id, stage, status, message="", region="us-east-1"):
    """Write a progress update to S3.

    Args:
        s3_bucket: S3 bucket name
        session_id: Session ID (used as S3 prefix)
        stage: Tool/stage name (e.g., "generate_spark_code")
        status: "running" | "complete" | "error"
        message: Optional detail message
        region: AWS region
    """
    if not s3_bucket or not session_id:
        return

    try:
        s3 = boto3.client("s3", region_name=region)
        key = f"{session_id}/progress.json"

        # Read existing progress
        try:
            obj = s3.get_object(Bucket=s3_bucket, Key=key)
            progress = json.loads(obj["Body"].read().decode("utf-8"))
        except Exception:
            progress = {"stages": [], "started_at": time.time()}

        # Append or update stage
        existing = next((s for s in progress["stages"] if s["stage"] == stage), None)
        now = time.time()

        if existing:
            existing["status"] = status
            existing["message"] = message
            existing["updated_at"] = now
            if status == "complete":
                existing["duration_s"] = round(now - existing.get("started_at", now), 1)
        else:
            progress["stages"].append({
                "stage": stage,
                "status": status,
                "message": message,
                "started_at": now,
                "updated_at": now,
            })

        progress["current_stage"] = stage
        progress["current_status"] = status
        progress["updated_at"] = now

        s3.put_object(
            Bucket=s3_bucket,
            Key=key,
            Body=json.dumps(progress).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception:
        pass  # Progress tracking is best-effort, never fail the tool
