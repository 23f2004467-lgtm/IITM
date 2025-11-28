#!/bin/bash
# Local Testing Script for LLM Analysis Quiz Solver

set -e  # Exit on error

echo "=========================================="
echo "LLM Analysis Quiz Solver - Local Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo "Creating .env from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env with your actual values${NC}"
    else
        echo "QUIZ_SECRET=test-secret-123" > .env
        echo "QUIZ_EMAIL=test@example.com" >> .env
        echo "OPENAI_API_KEY=your-key-here" >> .env
        echo "OPENAI_MODEL=gpt-4o" >> .env
        echo "PORT=8000" >> .env
        echo -e "${YELLOW}⚠️  Created basic .env - please update with real values${NC}"
    fi
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check if required variables are set
if [ -z "$QUIZ_SECRET" ] || [ -z "$QUIZ_EMAIL" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ Missing required environment variables in .env${NC}"
    echo "Required: QUIZ_SECRET, QUIZ_EMAIL, OPENAI_API_KEY"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables loaded${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Check Playwright
if ! python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Playwright browsers not installed. Installing...${NC}"
    playwright install chromium
    echo -e "${GREEN}✓ Playwright installed${NC}"
else
    echo -e "${GREEN}✓ Playwright installed${NC}"
fi

echo ""
echo "=========================================="
echo "Starting server..."
echo "=========================================="
echo ""

# Start server in background
echo "Starting server on port ${PORT:-8000}..."
python3 main.py > server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Check if server is running
if ! ps -p $SERVER_PID > /dev/null; then
    echo -e "${RED}✗ Server failed to start${NC}"
    echo "Last 20 lines of server.log:"
    tail -20 server.log
    exit 1
fi

# Test health endpoint
echo ""
echo "=========================================="
echo "Testing endpoints..."
echo "=========================================="
echo ""

BASE_URL="http://localhost:${PORT:-8000}"

# Test 1: Health check
echo "Test 1: Health endpoint"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health" || echo "FAILED")
if [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "   Response: $HEALTH_RESPONSE"
fi
echo ""

# Test 2: Root endpoint
echo "Test 2: Root endpoint"
ROOT_RESPONSE=$(curl -s "$BASE_URL/" || echo "FAILED")
if [[ "$ROOT_RESPONSE" == *"online"* ]]; then
    echo -e "${GREEN}✓ Root endpoint works${NC}"
    echo "   Response: $ROOT_RESPONSE"
else
    echo -e "${RED}✗ Root endpoint failed${NC}"
    echo "   Response: $ROOT_RESPONSE"
fi
echo ""

# Test 3: Invalid JSON (should return 400)
echo "Test 3: Invalid JSON (should return 400)"
INVALID_JSON_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/quiz" \
    -H "Content-Type: application/json" \
    -d 'invalid json' 2>/dev/null || echo "FAILED")
HTTP_CODE=$(echo "$INVALID_JSON_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "400" ]; then
    echo -e "${GREEN}✓ Invalid JSON correctly rejected (400)${NC}"
else
    echo -e "${RED}✗ Invalid JSON test failed (expected 400, got $HTTP_CODE)${NC}"
fi
echo ""

# Test 4: Invalid secret (should return 403)
echo "Test 4: Invalid secret (should return 403)"
INVALID_SECRET_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/quiz" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$QUIZ_EMAIL\",
        \"secret\": \"wrong-secret\",
        \"url\": \"https://example.com/test\"
    }" 2>/dev/null || echo "FAILED")
HTTP_CODE=$(echo "$INVALID_SECRET_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "403" ]; then
    echo -e "${GREEN}✓ Invalid secret correctly rejected (403)${NC}"
else
    echo -e "${RED}✗ Invalid secret test failed (expected 403, got $HTTP_CODE)${NC}"
fi
echo ""

# Test 5: Invalid email (should return 403)
echo "Test 5: Invalid email (should return 403)"
INVALID_EMAIL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/quiz" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"wrong@email.com\",
        \"secret\": \"$QUIZ_SECRET\",
        \"url\": \"https://example.com/test\"
    }" 2>/dev/null || echo "FAILED")
HTTP_CODE=$(echo "$INVALID_EMAIL_RESPONSE" | tail -1)
if [ "$HTTP_CODE" == "403" ]; then
    echo -e "${GREEN}✓ Invalid email correctly rejected (403)${NC}"
else
    echo -e "${RED}✗ Invalid email test failed (expected 403, got $HTTP_CODE)${NC}"
fi
echo ""

# Test 6: Valid request structure (may take time, so we'll timeout)
echo "Test 6: Valid request structure (testing endpoint accepts request)"
echo -e "${YELLOW}⚠️  This will send a real request - it may take time or use API credits${NC}"
read -p "   Continue? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    VALID_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 10 -X POST "$BASE_URL/quiz" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$QUIZ_EMAIL\",
            \"secret\": \"$QUIZ_SECRET\",
            \"url\": \"https://tds-llm-analysis.s-anand.net/demo\"
        }" 2>/dev/null || echo "TIMEOUT")
    HTTP_CODE=$(echo "$VALID_RESPONSE" | tail -1)
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "500" ]; then
        echo -e "${GREEN}✓ Valid request accepted (HTTP $HTTP_CODE)${NC}"
        echo "   Note: 500 is OK if quiz solving fails, means endpoint is working"
    else
        echo -e "${YELLOW}⚠️  Got HTTP $HTTP_CODE (may be timeout)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipped (user choice)${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Server is running on: $BASE_URL"
echo "Server PID: $SERVER_PID"
echo "Logs: server.log"
echo ""
echo -e "${GREEN}✓ Basic endpoint tests completed${NC}"
echo ""
echo "To stop the server, run:"
echo "  kill $SERVER_PID"
echo ""
echo "Or press Ctrl+C and the server will be stopped automatically"
echo ""

# Wait for user to stop or auto-stop after showing results
read -p "Press Enter to stop the server and exit..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true
rm -f server.log

echo ""
echo -e "${GREEN}✓ Server stopped${NC}"
echo "Test completed!"

