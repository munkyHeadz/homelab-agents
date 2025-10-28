#!/bin/bash
# Pre-push CI validation script
# Run this before pushing to catch CI failures early

set -e

echo "🔍 Running pre-push CI validation..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        FAILED=1
    fi
}

# 1. Check Python syntax
echo "1️⃣  Checking Python syntax..."
python3 -m py_compile crews/approval/*.py
print_status $? "Python syntax check"
echo ""

# 2. Run unit tests only (fast)
echo "2️⃣  Running unit tests..."
python3 -m pytest tests/test_approval_workflow.py::TestApprovalManager::test_is_critical_service_lxc \
    tests/test_approval_workflow.py::TestApprovalManager::test_is_critical_service_database \
    tests/test_approval_workflow.py::TestApprovalManager::test_is_critical_service_docker \
    -v --tb=short --no-cov 2>&1 | tail -20
print_status $? "Unit tests (critical services)"
echo ""

# 3. Check imports
echo "3️⃣  Checking imports..."
python3 -c "from crews.approval import ApprovalManager, get_approval_manager, CRITICAL_SERVICES; print('✓ Imports OK')"
print_status $? "Import check"
echo ""

# 4. Check gitignore for coverage files
echo "4️⃣  Checking .gitignore..."
if grep -q "coverage.xml" .gitignore; then
    print_status 0 "coverage.xml in .gitignore"
else
    print_status 1 "coverage.xml NOT in .gitignore"
fi
echo ""

# 5. Check for untracked files
echo "5️⃣  Checking for untracked files..."
UNTRACKED=$(git ls-files --others --exclude-standard | grep -v "coverage.xml\|htmlcov\|.pytest_cache\|__pycache__" || true)
if [ -z "$UNTRACKED" ]; then
    print_status 0 "No untracked files"
else
    echo -e "${YELLOW}⚠${NC}  Untracked files found:"
    echo "$UNTRACKED"
fi
echo ""

# 6. Check test coverage requirements match
echo "6️⃣  Checking coverage threshold consistency..."
PYTEST_THRESHOLD=$(grep "cov-fail-under" pytest.ini | grep -oP '\d+')
WORKFLOW_THRESHOLD=$(grep "cov-fail-under" .github/workflows/test.yml | grep -oP '\d+' | head -1)

if [ "$PYTEST_THRESHOLD" = "$WORKFLOW_THRESHOLD" ]; then
    print_status 0 "Coverage thresholds match ($PYTEST_THRESHOLD%)"
else
    print_status 1 "Coverage threshold mismatch: pytest.ini=$PYTEST_THRESHOLD%, workflow=$WORKFLOW_THRESHOLD%"
fi
echo ""

# Final summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All pre-push checks passed!${NC}"
    echo "Safe to push to remote."
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo "Please fix issues before pushing."
    exit 1
fi
