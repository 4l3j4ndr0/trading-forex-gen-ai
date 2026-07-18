#!/bin/bash
# Deploy MCP Forex Server
# Usage: ./deploy.sh

set -e

echo "🛑 Stopping mcp-forex..."
docker stop mcp-forex 2>/dev/null && docker rm mcp-forex 2>/dev/null || true

echo "🔨 Building image..."
docker build --no-cache -t mcp-forex-server .

echo "🚀 Starting mcp-forex on port 8000..."
docker run -d \
  --name mcp-forex \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  mcp-forex-server \
  python server.py --sse

echo "✅ mcp-forex deployed!"
docker logs --tail 5 mcp-forex
