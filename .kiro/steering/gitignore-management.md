---
inclusion: auto
---

# .gitignore Management Guidelines

## Purpose
Automatically manage .gitignore to keep the repository clean by excluding temporary files, test artifacts, logs, and documentation generated during development.

## Rules for File Creation

### Always Add to .gitignore

When creating or identifying these types of files, **proactively suggest or add them to .gitignore**:

#### 1. Documentation Files
- `*.md` files in root directory (except README.md, CONTRIBUTING.md, LICENSE.md)
- `docs/` directory and all contents
- `archive/` directory and all contents
- Any `*_SUMMARY.md`, `*_ANALYSIS.md`, `*_RESULTS.md` files

#### 2. Log Files
- `*.log`
- `deployment*.log`
- `*-debug.log`
- Any files ending in `.log`

#### 3. Test/Verification Files
- `test_*.json`, `*test*.json`
- `verify*.py`, `verify*.sh`
- `sample_*.csv`, `test_*.csv`
- `*_test_data.*`
- Test response files

#### 4. Temporary Files
- `*.tmp`, `*.temp`
- `*.bak`, `*.backup`
- Files in `/tmp/` directory
- `*~` (editor backup files)

#### 5. Build/Deployment Artifacts
- `*.zip` (deployment packages)
- `node_modules/`
- `dist/`, `build/`
- `*.egg-info/`

#### 6. Environment/Config
- `.env`, `.env.local`
- `*.pem`, `*.key` (credentials)
- `.aws/` (local AWS config)

## Workflow

### When Creating Files

1. **Before creating** documentation, test, or temporary files:
   - Check if similar patterns exist in .gitignore
   - If not, suggest adding the pattern

2. **After creating** multiple temporary files:
   - Review what was created
   - Suggest a .gitignore update with all new patterns

3. **During cleanup**:
   - When organizing/archiving files, ensure directories are in .gitignore

### Pattern Matching

Use **specific patterns** when possible:
- ✅ `sample_sales_data.csv` (specific file)
- ✅ `verify-fixes.sh` (specific file)
- ✅ `docs/` (entire directory)
- ✅ `*_SUMMARY.md` (pattern for similar files)

Avoid overly broad patterns that might exclude important files:
- ❌ `*.csv` (too broad, might exclude important data schemas)
- ❌ `*.sh` (too broad, might exclude important scripts)

## Examples

### Good .gitignore Structure

```gitignore
# Documentation and Archive
docs/
archive/

# Test/verification files
sample_sales_data.csv
verify-fixes.sh
verify_output_fix.py
test_*.csv

# Log files
*.log
deployment*.log

# Temporary test files
*test*.json
test_*.json

# Python cache
__pycache__/
*.py[cod]
```

### When to Suggest Updates

**Scenario 1: Creating test data**
```
User: "Create a sample CSV file for testing"
Action: After creating sample_data.csv, suggest:
  "I've created sample_data.csv. Should I add it to .gitignore?"
```

**Scenario 2: Creating documentation**
```
User: "Document the deployment process"
Action: After creating DEPLOYMENT_GUIDE.md in root:
  "I've created DEPLOYMENT_GUIDE.md. Since it's in the root directory,
   I recommend adding it to .gitignore or moving it to docs/ directory."
```

**Scenario 3: Multiple temporary files**
```
User: "Run tests and save results"
Action: After creating test_results.json, test_output.log:
  "I've created test files. I'll add these patterns to .gitignore:
   - *test*.json
   - *.log"
```

## Proactive Behavior

### During File Operations

1. **Creating files**: Check if they match temporary/test patterns
2. **Organizing files**: Ensure organized directories are in .gitignore
3. **Cleanup**: Verify .gitignore covers all temporary file patterns
4. **End of task**: Review all files created and suggest .gitignore updates

### Checking .gitignore

Before suggesting updates:
1. Read current .gitignore
2. Check if pattern already exists
3. Only suggest new patterns
4. Group related patterns together

## Special Cases

### Keep in Repository
These should NOT be in .gitignore:
- `README.md` (main documentation)
- `LICENSE.md`, `CONTRIBUTING.md`
- Core configuration files (`package.json`, `requirements.txt`)
- Source code files
- Infrastructure as Code (CloudFormation, Terraform)
- Deployment scripts that are part of the project

### Context-Specific
Ask user before adding:
- CSV files that might be data schemas
- Shell scripts that might be deployment scripts
- JSON files that might be configuration

## Implementation

### Automatic Addition
For clearly temporary files, add directly:
```
"I've added the following to .gitignore:
 - test_results.json (temporary test file)
 - deployment.log (log file)"
```

### Suggest Addition
For ambiguous files, ask first:
```
"I've created sample_data.csv. This appears to be test data.
 Should I add it to .gitignore, or is it part of the project?"
```

## Maintenance

### Regular Checks
- When creating 3+ temporary files, review .gitignore
- After cleanup operations, verify .gitignore is complete
- When organizing documentation, ensure docs/ is ignored

### Pattern Optimization
- Consolidate similar patterns
- Use wildcards for common prefixes/suffixes
- Keep .gitignore organized with comments

---

**Note**: This steering document is always active and guides .gitignore management throughout all interactions.
