# Ray Cluster Disconnection Fix

## Issue
UI shows "Ray Disconnected" after some time, even though Ray cluster is accessible and backend is running.

## Root Cause Analysis

### Frontend Issue (Primary)
**File**: `frontend/src/App.jsx`

The polling logic had a critical bug:
```javascript
const handleVisibilityChange = () => {
  if (document.hidden) {
    clearInterval(interval);  // ✅ Stops polling when tab hidden
  }
  // ❌ MISSING: Never restarts polling when tab becomes visible!
};
```

**What happened:**
1. User switches to another tab → `document.hidden = true`
2. Polling stops (to save resources)
3. User switches back → `document.hidden = false`
4. **Polling never restarts!**
5. UI shows last known status (eventually shows "disconnected")

### Backend Issue (Secondary)
**File**: `backend/main.py`

No retry logic for transient network failures:
```python
try:
    response = make_ray_request("/api/version", timeout=3)
    # Single attempt - fails on any transient network issue
except Exception as e:
    return {"status": "disconnected"}
```

## Solution

### 1. Frontend Fix - Restart Polling on Visibility Change
```javascript
const handleVisibilityChange = () => {
  if (document.hidden) {
    clearInterval(interval);
  } else {
    checkRayStatus(); // ✅ Check immediately when visible
    interval = setInterval(checkRayStatus, 30000); // ✅ Restart polling
  }
};
```

**Benefits:**
- Polling resumes when user returns to tab
- Immediate status check on tab focus
- Reduced polling interval (60s → 30s) for faster updates

### 2. Backend Fix - Add Retry Logic
```python
@app.get("/ray/status")
async def ray_status():
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = make_ray_request("/api/version", timeout=5)
            if response:
                return {"status": "connected", ...}
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait before retry
                continue
    return {"status": "disconnected", ...}
```

**Benefits:**
- Handles transient network failures
- 2 retry attempts with 1-second delay
- More resilient to temporary issues

## Testing

### Before Fix
1. Open UI → Ray shows "Connected"
2. Switch to another tab for 2+ minutes
3. Switch back → Ray shows "Disconnected" (even though cluster is up)
4. Status never recovers

### After Fix
1. Open UI → Ray shows "Connected"
2. Switch to another tab for any duration
3. Switch back → Status checks immediately
4. Ray shows "Connected" within 1-2 seconds

## Files Changed

### Frontend
- **File**: `frontend/src/App.jsx`
- **Lines**: 38-58 (useEffect hook)
- **Change**: Added polling restart logic in visibility change handler
- **Polling interval**: 60s → 30s

### Backend
- **File**: `backend/main.py`
- **Lines**: 1-13 (imports), 406-426 (ray_status endpoint)
- **Changes**:
  - Added `asyncio` import
  - Added retry logic with 2 attempts
  - Increased timeout from 3s to 5s

## Deployment

### Frontend
Restart the frontend to pick up changes:
```bash
cd frontend
npm run dev
```

### Backend
Backend auto-reloads with `--reload` flag (already running).

## Additional Improvements

### Polling Strategy
- **Before**: 60-second interval, stops on tab hide
- **After**: 30-second interval, pauses/resumes on visibility change

### Error Handling
- **Before**: Single attempt, immediate failure
- **After**: 2 retry attempts with 1-second delay

### User Experience
- Faster status updates (30s vs 60s)
- Immediate check when returning to tab
- More resilient to network hiccups

## Monitoring

To verify the fix is working:
1. Open browser console
2. Watch for `/ray/status` requests
3. Switch tabs and return
4. Should see immediate status check on tab focus

## Related Issues
- Tab visibility API: https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API
- React useEffect cleanup: https://react.dev/reference/react/useEffect#cleanup-function

## Summary
✅ Fixed polling restart on tab visibility change
✅ Added retry logic for transient failures
✅ Reduced polling interval for faster updates
✅ Improved user experience and reliability
