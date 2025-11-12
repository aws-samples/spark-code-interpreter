# Framework-Based Conditional UI Changes

## Summary
Updated frontend and backend to show/hide components based on selected framework (Ray or Spark).

## Frontend Changes (App.jsx)

### 1. State Management
- Added `sparkStatus` state to track Lambda and EMR availability
- Updated `useEffect` to check status based on selected framework
- Added `checkSparkStatus()` function to poll Spark infrastructure

### 2. Navigation Panel (Left Sidebar)
**When Ray is selected:**
- Framework Selector (visible)
- Glue Data Catalog (HIDDEN)
- Ray Jobs Manager (visible)

**When Spark is selected:**
- Framework Selector (visible)
- Glue Data Catalog (visible)
- Selected Tables display (visible if tables selected)
- Ray Jobs Manager (HIDDEN)

### 3. Header Status Badges
**When Ray is selected:**
- Shows: Ray status badge (green/red)
- Shows: Ray version info

**When Spark is selected:**
- Shows: Lambda status badge (green/grey)
- Shows: EMR status badge (green/grey)
- Hides: Ray version info

### 4. Tabs
**When Ray is selected:**
- Generate Code
- Code Editor
- Execution Results
- Session History
- Ray Dashboard (visible)
- Settings

**When Spark is selected:**
- Generate Code
- Code Editor
- Execution Results
- Session History
- Ray Dashboard (HIDDEN)
- Settings

## Backend Changes (main.py)

### New Endpoint: `/spark/status`
**Purpose:** Check Spark Lambda and EMR Serverless availability

**Response:**
```json
{
  "lambda_status": "ready|not_ready|error|unknown",
  "emr_status": "ready|not_ready|error|unknown",
  "lambda_function": "sparkOnLambda-spark-code-interpreter",
  "emr_application_id": "00fv6g7rptsov009"
}
```

**Logic:**
- Checks Lambda function state (Active = ready)
- Checks EMR Serverless application state (CREATED/STARTED = ready)
- Returns status for both infrastructure components
- Polls every 30 seconds when Spark is selected

## Status Indicators

### Lambda Status
- **ready** (green): Lambda function is Active and ready to invoke
- **not_ready** (grey): Lambda exists but not in Active state
- **error** (grey): Cannot access Lambda function
- **unknown** (grey): Status check not yet completed

### EMR Status
- **ready** (green): EMR Serverless application is CREATED or STARTED
- **not_ready** (grey): EMR application exists but not ready
- **error** (grey): Cannot access EMR application
- **unknown** (grey): Status check not yet completed

## No Simulations Added
All status checks are real API calls to AWS services:
- Lambda: `lambda.get_function()`
- EMR: `emr-serverless.get_application()`

## Features Preserved
- All Ray functionality works when Ray is selected
- All Spark functionality works when Spark is selected
- Framework switching is instant and updates UI immediately
- No breaking changes to existing features
