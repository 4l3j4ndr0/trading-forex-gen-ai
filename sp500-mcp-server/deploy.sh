#!/bin/bash
# Deploy MCP SP500 Server
# Usage: ./deploy.sh

set -e

echo "🛑 Stopping mcp-sp500..."
docker stop mcp-sp500 2>/dev/null && docker rm mcp-sp500 2>/dev/null || true

echo "🔨 Building image..."
docker build --no-cache -t mcp-sp500-server .

echo "🚀 Starting mcp-sp500 on port 8001..."
docker run -d \
  --name mcp-sp500 \
  --restart unless-stopped \
  --env-file .env \
  -p 8001:8001 \
  mcp-sp500-server

echo "✅ mcp-sp500 deployed!"
docker logs --tail 5 mcp-sp500
