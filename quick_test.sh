#!/bin/bash
# Quick Local Test Script

set -e

echo "=========================================="
echo "Quick Local Test - LLM Quiz Solver"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Load env vars
export $(grep -v '^#' .env | xargs)

# Check Python
echo "Checking Python..."
python3 --version
echo ""

# Check and install dependencies
echo "Checking dependencies..."
if ! python3 -c "import fastapi, uvicorn, playwright, openai, aiohttp, pandas" 2>/dev/null; then
    echo "⚠️  Missing dependencies. Installing..."
    python3 -m pip install -q -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✓ All dependencies installed"
fi

# Check Playwright browsers
if ! python3 -c "from playwright.sync_api import sync_playwright; p = sync_playwright(); p.start()" 2>/dev/null; then
    echo "⚠️  Installing Playwright browsers..."
    playwright install chromium 2>/dev/null || echo "⚠️  Playwright install may need manual setup"
fi
echo ""

# Start server in background
echo "Starting server..."
python3 main.py > /tmp/quiz_server.log 2>&1 &
SERVER_PID=$!
sleep 3

# Check if server started
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Server failed to start"
    cat /tmp/quiz_server.log
    exit 1
fi

echo "✓ Server started (PID: $SERVER_PID)"
echo ""

# Test endpoints
BASE_URL="http://localhost:${PORT:-8000}"

echo "Testing endpoints..."
echo ""

# Test 1: Health
echo "1. Health check:"
HEALTH=$(curl -s "$BASE_URL/health" || echo "FAILED")
echo "   $HEALTH"
[[ "$HEALTH" == *"healthy"* ]] && echo "   ✓ PASS" || echo "   ❌ FAIL"
echo ""

# Test 2: Root
echo "2. Root endpoint:"
ROOT=$(curl -s "$BASE_URL/" || echo "FAILED")
echo "   $ROOT"
[[ "$ROOT" == *"online"* ]] && echo "   ✓ PASS" || echo "   ❌ FAIL"
echo ""

# Test 3: Invalid JSON (400)
echo "3. Invalid JSON (should be 400):"
HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/quiz" \
    -H "Content-Type: application/json" \
    -d 'invalid' 2>/dev/null || echo "000")
echo "   HTTP $HTTP_CODE"
[ "$HTTP_CODE" == "400" ] && echo "   ✓ PASS" || echo "   ❌ FAIL"
echo ""

# Test 4: Invalid secret (403)
echo "4. Invalid secret (should be 403):"
HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/quiz" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$QUIZ_EMAIL\",\"secret\":\"wrong\",\"url\":\"https://test.com\"}" 2>/dev/null || echo "000")
echo "   HTTP $HTTP_CODE"
[ "$HTTP_CODE" == "403" ] && echo "   ✓ PASS" || echo "   ❌ FAIL"
echo ""

echo "=========================================="
echo "Tests completed!"
echo "Server running on: $BASE_URL"
echo "PID: $SERVER_PID"
echo ""
echo "To stop: kill $SERVER_PID"
echo "=========================================="

# Keep server running - user can stop manually
read -p "Press Enter to stop server..."
kill $SERVER_PID 2>/dev/null || true
rm -f /tmp/quiz_server.log
echo "✓ Server stopped"

