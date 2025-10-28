#!/bin/bash
# Auto-fix code formatting issues
# Runs black and isort to automatically format code

set -e

echo "🔧 Auto-fixing code formatting..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Install formatting tools if needed
echo "1️⃣  Checking formatting tools..."
pip install -q black isort 2>/dev/null || true
echo -e "${GREEN}✓${NC} Tools ready"
echo ""

# 2. Format with black
echo "2️⃣  Running black formatter..."
FILES_FORMATTED=$(black crews/ tests/ 2>&1 | grep "reformatted\|formatted" | wc -l)
if [ "$FILES_FORMATTED" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Formatted $FILES_FORMATTED file(s)"
else
    echo -e "${GREEN}✓${NC} All files already formatted"
fi
echo ""

# 3. Sort imports with isort
echo "3️⃣  Running isort..."
IMPORTS_FIXED=$(isort crews/ tests/ 2>&1 | grep "Fixing\|Skipped" | grep "Fixing" | wc -l)
if [ "$IMPORTS_FIXED" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Fixed imports in $IMPORTS_FIXED file(s)"
else
    echo -e "${GREEN}✓${NC} All imports already sorted"
fi
echo ""

# 4. Show git status
echo "4️⃣  Checking changes..."
MODIFIED=$(git status --short | wc -l)
if [ "$MODIFIED" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  Modified files:"
    git status --short | head -20
    echo ""
    echo "Review changes with: git diff"
    echo "Commit with: git add -A && git commit -m 'style: Auto-format with black and isort'"
else
    echo -e "${GREEN}✓${NC} No changes needed"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Auto-fix complete!${NC}"

if [ "$MODIFIED" -gt 0 ]; then
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: git diff"
    echo "  2. Run tests: pytest tests/ -m unit"
    echo "  3. Commit: git add -A && git commit -m 'style: Auto-format code'"
    echo "  4. Push: git push"
fi
