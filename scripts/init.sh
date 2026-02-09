#!/bin/bash

# Operations Platform Initialization Script

set -e

echo "==================================="
echo "运维平台初始化脚本"
echo "==================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装,请先安装 Docker"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装,请先安装 Docker Compose"
    exit 1
fi

echo "✓ Docker 环境检查通过"

# Create .env file if not exists
if [ ! -f backend/.env ]; then
    echo "创建后端环境配置文件..."
    cat > backend/.env << EOF
DATABASE_URL=postgresql://opsuser:opspass@postgres:5432/opsplatform
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-change-in-production-$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
    echo "✓ 后端环境配置文件已创建"
fi

# Create frontend .env file
if [ ! -f frontend/.env ]; then
    echo "创建前端环境配置文件..."
    cat > frontend/.env << EOF
VITE_API_BASE_URL=http://localhost:8000/api/v1
EOF
    echo "✓ 前端环境配置文件已创建"
fi

# Start services
echo "启动服务..."
docker-compose up -d

echo "等待服务启动..."
sleep 10

# Check service status
echo "检查服务状态..."
docker-compose ps

echo ""
echo "==================================="
echo "初始化完成!"
echo "==================================="
echo ""
echo "服务访问地址:"
echo "  前端:        http://localhost:5173"
echo "  后端 API:    http://localhost:8000"
echo "  API 文档:    http://localhost:8000/api/docs"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3000 (admin/admin)"
echo ""
echo "创建管理员账号:"
echo "  curl -X POST http://localhost:8000/api/v1/auth/register \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\":\"admin\",\"email\":\"admin@example.com\",\"password\":\"admin123\",\"role\":\"admin\"}'"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo "==================================="
