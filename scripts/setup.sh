#!/bin/bash

# ==============================================
# OPS Platform - Setup Script
# ==============================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "  OPS Platform Setup"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo -e "${GREEN}Creating .env from .env.example...${NC}"
    cp .env.example .env
    
    echo -e "${YELLOW}⚠️  IMPORTANT: Please update the following in .env:${NC}"
    echo "  - POSTGRES_PASSWORD"
    echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "  - GF_SECURITY_ADMIN_PASSWORD"
    echo ""
    read -p "Press Enter to continue after updating .env..."
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi

# Check if frontend is built
if [ ! -d "frontend/dist" ]; then
    echo -e "${YELLOW}⚠️  Frontend not built${NC}"
    read -p "Build frontend now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Building frontend...${NC}"
        cd frontend
        npm install
        npm run build
        cd ..
        echo -e "${GREEN}✓ Frontend built${NC}"
    else
        echo -e "${RED}⚠️  Skipping frontend build. You'll need to build it manually.${NC}"
    fi
else
    echo -e "${GREEN}✓ Frontend already built${NC}"
fi

# Ask for environment
echo ""
echo "Select environment:"
echo "1) Development (with hot reload, exposed ports)"
echo "2) Production (optimized, secure)"
read -p "Enter choice [1-2]: " env_choice

case $env_choice in
    1)
        echo -e "${GREEN}Starting in DEVELOPMENT mode...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        echo ""
        echo -e "${GREEN}=========================================="
        echo "  Services Started (Development)"
        echo "==========================================${NC}"
        echo "Frontend Dev Server: http://localhost:5173"
        echo "Backend API: http://localhost:8000"
        echo "API Docs: http://localhost:8000/docs"
        echo "Nginx Proxy: http://localhost"
        echo "Prometheus: http://localhost:9090"
        echo "Grafana: http://localhost:3000"
        echo "PostgreSQL: localhost:5432"
        echo "Redis: localhost:6379"
        ;;
    2)
        echo -e "${GREEN}Starting in PRODUCTION mode...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
        echo ""
        echo -e "${GREEN}=========================================="
        echo "  Services Started (Production)"
        echo "==========================================${NC}"
        echo "Application: http://localhost"
        echo "API Docs: http://localhost/docs"
        echo ""
        echo -e "${YELLOW}Note: Internal services (DB, Redis, monitoring) are not exposed${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Waiting for services to be healthy...${NC}"
sleep 10

echo ""
docker-compose ps

echo ""
echo -e "${GREEN}=========================================="
echo "  Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f          # View logs"
echo "  docker-compose ps               # Check status"
echo "  docker-compose down             # Stop all services"
echo "  docker-compose restart backend  # Restart a service"
echo ""
echo "For more information, see DOCKER_DEPLOYMENT.md"
