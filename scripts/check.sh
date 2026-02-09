#!/bin/bash

# Pre-deployment Check Script

echo "========================================"
echo "  OPS Platform Pre-Deployment Check"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check 1: .env file exists
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    
    # Check critical variables
    if grep -q "POSTGRES_PASSWORD=CHANGE_ME" .env; then
        echo -e "${RED}✗${NC} POSTGRES_PASSWORD not updated"
        ERRORS=$((ERRORS+1))
    else
        echo -e "${GREEN}✓${NC} POSTGRES_PASSWORD is set"
    fi
    
    if grep -q "SECRET_KEY=CHANGE_ME" .env; then
        echo -e "${RED}✗${NC} SECRET_KEY not updated"
        ERRORS=$((ERRORS+1))
    else
        echo -e "${GREEN}✓${NC} SECRET_KEY is set"
    fi
    
    if grep -q "GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME" .env; then
        echo -e "${RED}✗${NC} GF_SECURITY_ADMIN_PASSWORD not updated"
        ERRORS=$((ERRORS+1))
    else
        echo -e "${GREEN}✓${NC} GF_SECURITY_ADMIN_PASSWORD is set"
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
    ERRORS=$((ERRORS+1))
fi

echo ""

# Check 2: Frontend build
if [ -d frontend/dist ]; then
    echo -e "${GREEN}✓${NC} Frontend is built (frontend/dist exists)"
else
    echo -e "${YELLOW}⚠${NC} Frontend not built (frontend/dist missing)"
    echo "  Run: cd frontend && npm install && npm run build"
    WARNINGS=$((WARNINGS+1))
fi

echo ""

# Check 3: Docker running
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is running"
else
    echo -e "${RED}✗${NC} Docker is not running"
    ERRORS=$((ERRORS+1))
fi

echo ""

# Check 4: Required files
FILES=(
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "docker-compose.prod.yml"
    "docker/nginx.conf"
    "docker/nginx.dev.conf"
    "docker/backend.Dockerfile"
    "scripts/entrypoint.sh"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file missing"
        ERRORS=$((ERRORS+1))
    fi
done

echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo -e "Errors: ${RED}${ERRORS}${NC}"
echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Ready to deploy!${NC}"
    echo ""
    echo "Start services with:"
    echo "  Development: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
    echo "  Production:  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
    exit 0
else
    echo -e "${RED}✗ Please fix errors before deploying${NC}"
    exit 1
fi
