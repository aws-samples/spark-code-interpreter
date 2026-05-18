# Spark Code Interpreter — Claude Instructions

## After Every Code or Config Change

Before reporting a task as complete, always verify whether these two files need updating:

**`scripts/deploy-mcp-tools.sh` / `scripts/deploy-all.sh`**
Ask: does this change affect how things are deployed?
- New Python dependency added to a Lambda → update pip install or requirements.txt
- New shared file added to `mcp-tools/` that Lambdas need → copy it in the package step
- New AWS resource accessed by a Lambda → add permissions to the IAM policy in the script
- New Lambda or infrastructure component → add it to the deploy sequence

**`README.md` (Troubleshooting section)**
Ask: could this change produce a new error a user might hit?
- New failure mode introduced or discovered → add an entry
- Error fixed that had a workaround documented → update or remove the workaround
- New deploy-time requirement → document it

This check is mandatory — do not skip it even for small changes. If neither file needs updating, state that explicitly so it's clear the check was done.

**`docs/CHANGELOG.md`**
Ask: does this change represent a completed feature, fix, or enhancement worth tracking?
- Bug fixed → add a bullet under today's date describing what broke and how it was fixed
- Feature or improvement completed → add a bullet with what changed and measurable impact if known
- Group related changes under a named section heading (e.g. "Glue Catalog Fix", "Frontend Improvements")
- Add a new `## YYYY-MM-DD` date section at the top if one doesn't exist for today

Update this file at the end of every task, not just at the end of a session.
