# Quick Start Guide

## Test Your Deployment in 30 Seconds

### Step 1: Test Direct Agent Invocation

```bash
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

**This works right now!** ✅

### Step 2: Check Gateway Status

```bash
./list-gateway-tools.sh
```

Shows Gateway configuration and available tools.

### Step 3: Add Gateway Target (Optional)

```bash
./add-gateway-target.sh
```

Adds tools to the Gateway for MCP access.

---

## That's It!

You now have:
- ✅ Working Spark Supervisor Agent
- ✅ Secure authentication (Cognito JWT)
- ✅ MCP Gateway (needs targets)
- ✅ Complete infrastructure

---

## Common Commands

```bash
# Ask any question
./invoke-agent-directly.sh "create a dataframe with 10 rows"

# Get authentication token
./get-user-token.sh

# Check Gateway
./list-gateway-tools.sh

# Add Gateway Target
./add-gateway-target.sh
```

---

## Need Help?

- **Testing Guide:** `TESTING_GUIDE.md`
- **Complete Summary:** `COMPLETE_SETUP_SUMMARY.md`
- **Gateway Targets:** `NO_TOOLS_FIX.md`
- **Authentication:** `SECRET_HASH_FIX.md`

---

**Start now:**
```bash
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

🚀 Happy coding!
