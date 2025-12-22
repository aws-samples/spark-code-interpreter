# Gateway Target Configuration for AWS Console

## Step-by-Step Instructions

1. **Open AWS Console:**
   ```
   https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/gateways
   ```

2. **Select Gateway:**
   - Click on: `dev-spark-gateway-0y5eyw5mag`

3. **Add Target:**
   - Click "Targets" tab
   - Click "Add target" button

4. **Fill in the form:**

---

### Basic Information

**Name:**
```
spark-executor
```

**Description:**
```
Execute PySpark code on AWS Lambda for data processing and analysis
```

---

### Target Configuration

**Target Type:**
```
Lambda
```

**Lambda ARN:**
```
arn:aws:lambda:us-east-1:817323390093:function:dev-spark-on-lambda
```

---

### Tool Schema

**IMPORTANT:** Leave the tool schema field **EMPTY** or select "Auto-generate from Lambda".

The Console expects a complex format that's error-prone. Let AWS auto-generate the schema from your Lambda function instead.

If you must provide a schema manually, the Console expects it as a **JSON string** (not a JSON object), and the format varies by Console version.

**Recommended:** Skip the tool schema field entirely - AWS will detect the Lambda's input/output format automatically.

---

### Credentials

**Credential Type:**
```
None
```

(The Gateway role already has permissions to invoke the Lambda)

---

### Summary

After filling in all fields:
1. Click "Add target"
2. Wait 30-60 seconds for status to change from `Creating` to `Available`
3. Test with:
   ```bash
   cd scripts
   ./list-gateway-tools.sh
   ./ask-gateway.sh "create a simple dataframe"
   ```

---

## Lambda Input Format

The Lambda expects this input structure:

```json
{
  "code": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.getOrCreate()\ndf = spark.createDataFrame([(1, 'a'), (2, 'b')], ['id', 'value'])\nresult = {'data': df.toPandas().to_dict()}\nimport json\nwith open('/tmp/output.json', 'w') as f: json.dump(result, f)",
  "bucket": "spark-data-817323390093-us-east-1",
  "file_path": "output/",
  "iterate": 0,
  "config": {}
}
```

**Required:**
- `code` - PySpark code string

**Optional:**
- `dataset_name` - Dataset name(s) to use
- `bucket` - S3 bucket for outputs
- `file_path` - S3 prefix for outputs
- `iterate` - Retry counter
- `config` - Spark configuration dict

**Output:**
The Lambda writes results to `/tmp/output.json` and returns:
```json
{
  "statusCode": 200,
  "body": {
    "result": {...},
    "image_dict": [...],
    "plotly": [...]
  }
}
```

---

## Alternative: Simplified Schema

If the full schema doesn't work, try this minimal version:

```json
{
  "tools": [
    {
      "name": "execute_spark",
      "description": "Execute PySpark code",
      "inputSchema": {
        "type": "object",
        "properties": {
          "code": {
            "type": "string",
            "description": "PySpark code to execute"
          }
        },
        "required": ["code"]
      }
    }
  ]
}
```

This minimal schema only exposes the required `code` parameter.

---

## Troubleshooting

### If target creation fails:
- Try without the tool schema (let AWS auto-generate)
- Verify the Lambda ARN is correct
- Check that the Gateway role has `lambda:InvokeFunction` permission

### If target is created but doesn't work:
- Check target status is `Available`
- Run `./list-gateway-tools.sh` to verify tool is exposed
- Check CloudWatch logs for the Lambda function

---

**That's it!** Once the target is added, your Gateway will expose the `execute_spark` tool via MCP.
