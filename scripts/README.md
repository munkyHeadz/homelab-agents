# Scripts Directory

Automation scripts for development and CI/CD workflows.

## Available Scripts

### pre-push-check.sh

**Purpose:** Validates code quality before pushing to remote repository to catch CI failures early.

**What it checks:**
1. ✅ Python syntax (all `.py` files compile)
2. ✅ Unit tests pass (critical approval workflow tests)
3. ✅ Imports work correctly
4. ✅ `.gitignore` includes coverage artifacts
5. ✅ No untracked files (warns only)
6. ✅ Coverage thresholds match between `pytest.ini` and GitHub Actions

**Usage:**

```bash
# Run manually before pushing
./scripts/pre-push-check.sh

# Set up as git pre-push hook (recommended)
ln -s ../../scripts/pre-push-check.sh .git/hooks/pre-push
```

**Example output:**

```
🔍 Running pre-push CI validation...

1️⃣  Checking Python syntax...
✓ Python syntax check

2️⃣  Running unit tests...
✓ Unit tests (critical services)

3️⃣  Checking imports...
✓ Imports OK

4️⃣  Checking .gitignore...
✓ coverage.xml in .gitignore

5️⃣  Checking for untracked files...
✓ No untracked files

6️⃣  Checking coverage threshold consistency...
✓ Coverage thresholds match (20%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ All pre-push checks passed!
Safe to push to remote.
```

**Exit codes:**
- `0` - All checks passed, safe to push
- `1` - One or more checks failed, do not push

**Performance:** ~2-5 seconds

**Benefits:**
- Catches CI failures before pushing
- Saves CI/CD pipeline minutes
- Faster feedback loop
- Prevents embarrassing failures in GitHub Actions

---

## Setting Up Git Hooks

### Automated Pre-Push Hook

To automatically run checks before every push:

```bash
cd /path/to/homelab-agents
ln -s ../../scripts/pre-push-check.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Now every `git push` will automatically run validation. If checks fail, the push will be blocked.

### Manual Usage

You can also run the script manually anytime:

```bash
# From project root
./scripts/pre-push-check.sh

# From any directory
cd /path/to/anywhere
/path/to/homelab-agents/scripts/pre-push-check.sh
```

---

## Troubleshooting

### Script fails with "command not found"

Make sure the script is executable:
```bash
chmod +x scripts/pre-push-check.sh
```

### Tests fail locally but pass in script

The script runs a subset of fast unit tests. Run the full suite:
```bash
pytest tests/ -m unit
```

### Want to skip checks for emergency push

Override the pre-push hook:
```bash
git push --no-verify
```

⚠️ **Warning:** Only use `--no-verify` in emergencies. CI will still fail if tests don't pass.

---

## Future Enhancements

Potential additions to pre-push checks:

- [ ] Code formatting (black, isort)
- [ ] Linting (flake8)
- [ ] Security scanning (bandit)
- [ ] Type checking (mypy)
- [ ] Documentation checks
- [ ] Dependency vulnerability scanning

These are currently in the CI/CD pipeline but could be added to pre-push for even faster feedback.
