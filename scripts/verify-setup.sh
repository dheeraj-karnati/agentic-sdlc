#!/bin/bash
# Verify the complete Agentic SDLC development environment
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

ERRORS=0
echo '=== Agentic SDLC Environment Verification ==='
echo ''

# ─── CLI Tools ───
echo '--- CLI Tools ---'
command -v python3 &>/dev/null && pass "Python3: $(python3 --version 2>&1)" || fail 'Python3 not found'
command -v uv &>/dev/null && pass "uv: $(uv --version 2>&1)" || fail 'uv not found (brew install uv)'
command -v node &>/dev/null && pass "Node.js: $(node --version 2>&1)" || fail 'Node.js not found'
command -v docker &>/dev/null && pass "Docker: $(docker --version 2>&1)" || fail 'Docker not found'
command -v gh &>/dev/null && pass "GitHub CLI: $(gh --version 2>&1 | head -1)" || warn 'gh not found (brew install gh)'
command -v git &>/dev/null && pass "Git: $(git --version 2>&1)" || fail 'Git not found'
command -v claude &>/dev/null && pass "Claude Code: installed" || warn 'Claude Code not found (curl -fsSL https://claude.ai/install.sh | bash)'
echo ''

# ─── Docker Services ───
echo '--- Docker Services ---'
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    docker ps --filter name=sdlc-postgres --format '{{.Status}}' 2>/dev/null | grep -q Up && \
        pass 'PostgreSQL is running' || fail 'PostgreSQL is NOT running'
    docker ps --filter name=sdlc-redis --format '{{.Status}}' 2>/dev/null | grep -q Up && \
        pass 'Redis is running' || fail 'Redis is NOT running'
    docker ps --filter name=sdlc-minio --format '{{.Status}}' 2>/dev/null | grep -q Up && \
        pass 'MinIO is running' || fail 'MinIO is NOT running'
else
    fail 'Docker is not running'
fi
echo ''

# ─── PostgreSQL + pgvector ───
echo '--- Database ---'
if docker ps --filter name=sdlc-postgres --format '{{.Status}}' 2>/dev/null | grep -q Up; then
    docker exec sdlc-postgres psql -U sdlc -d agentic_sdlc -c \
        "SELECT extname FROM pg_extension WHERE extname='vector'" \
        2>/dev/null | grep -q vector && \
        pass 'pgvector extension enabled' || fail 'pgvector NOT enabled'
    docker exec sdlc-postgres psql -U sdlc -d agentic_sdlc -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" \
        2>/dev/null | grep -q '[1-9]' && \
        pass 'Database tables created' || fail 'Database tables NOT found'
else
    warn 'Skipping DB checks (PostgreSQL not running)'
fi
echo ''

# ─── Python Environment ───
echo '--- Python Environment ---'
[ -d '.venv' ] && pass '.venv directory exists' || warn '.venv not found (run: uv sync)'
if [ -d '.venv' ]; then
    uv run python -c 'import langchain; print(f"LangChain: {langchain.__version__}")' 2>/dev/null && \
        pass 'LangChain installed' || fail 'LangChain NOT installed'
    uv run python -c 'import langgraph' 2>/dev/null && \
        pass 'LangGraph installed' || fail 'LangGraph NOT installed'
    uv run python -c 'import fastapi; print(f"FastAPI: {fastapi.__version__}")' 2>/dev/null && \
        pass 'FastAPI installed' || fail 'FastAPI NOT installed'
fi
echo ''

# ─── API Keys ───
echo '--- Configuration ---'
[ -f '.env' ] && pass '.env file exists' || warn '.env file NOT found (cp .env.example .env)'
if [ -f '.env' ]; then
    grep -q 'ANTHROPIC_API_KEY=sk-ant' .env 2>/dev/null && \
        pass 'Anthropic API key configured' || warn 'Anthropic API key not set in .env'
    grep -q 'LANGCHAIN_API_KEY=ls' .env 2>/dev/null && \
        pass 'LangSmith API key configured' || warn 'LangSmith API key not set'
    grep -q 'GITHUB_TOKEN=' .env 2>/dev/null && \
        pass 'GitHub token configured' || warn 'GitHub token not set'
fi

# ─── Check for env var conflict ───
if [ -n "$ANTHROPIC_API_KEY" ]; then
    warn 'ANTHROPIC_API_KEY is set as shell env var! This will conflict with Claude Code Max subscription.'
    warn 'Remove it from ~/.zshrc and use .env file only.'
fi
echo ''

# ─── Summary ───
echo '==============================='
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed! Environment is ready.${NC}"
else
    echo -e "${RED}$ERRORS check(s) failed. Fix the issues above.${NC}"
fi
