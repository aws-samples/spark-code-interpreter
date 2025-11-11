# Frontend UI Changes - Framework Integration

## Changes Made

### 1. Title Updates
- **index.html**: Changed from "Ray Code Interpreter" to "Data Processing Agent"
- **App.jsx Header**: Changed from "Ray Code Interpreter" to "Data Processing Agent"

### 2. Removed "Ray" References (except Ray Dashboard and Settings)
- Generate Code tab: "Generate Ray Code" → "Generate Code"
- Code Editor tab: "Edit Ray Code" → "Edit Code"
- Execute button: "Execute on Ray Cluster" → "Execute Code"
- Generate button: "Generate Ray Code" → "Generate Code"

### 3. New Framework Selector Component
**Location**: `src/components/FrameworkSelector.jsx`

**Features**:
- Radio button selection for framework choice
- Options: Ray or Spark
- Descriptions for each framework
- Positioned at top of left navigation panel (above Glue Data Catalog)

**State Management**:
- Added `framework` state in App.jsx (default: 'ray')
- State can be toggled between 'ray' and 'spark'

### 4. Navigation Layout
**New Order** (top to bottom):
1. Framework Selector (NEW)
2. Glue Data Catalog
3. Selected Tables (if any)
4. Ray Jobs Manager

### 5. Preserved Components
- Ray Dashboard tab (kept as-is)
- Settings tab (kept as-is)
- Ray status badge in header (kept as-is)
- Ray version display (kept as-is)

## Files Modified
1. `/frontend/index.html` - Title update
2. `/frontend/src/App.jsx` - Main application logic
3. `/frontend/src/components/FrameworkSelector.jsx` - NEW component

## Next Steps
- Wire framework selection to backend API calls
- Update code generation to use selected framework
- Update execution logic based on framework choice
- Add Spark-specific UI elements when Spark is selected
