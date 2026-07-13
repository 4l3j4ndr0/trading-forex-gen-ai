#!/bin/bash
# Deploy MCP Trading Server to EC2
# Usage: ./deploy.sh <ec2-host> [ssh-key]
# Example: ./deploy.sh ubuntu@54.123.45.67 ~/.ssh/my-key.pem

set -e

EC2_HOST=${1:?"Usage: ./deploy.sh <user@host> [ssh-key-path]"}
SSH_KEY=${2:-""}
SSH_OPTS=""

if [ -n "$SSH_KEY" ]; then
    SSH_OPTS="-i $SSH_KEY"
fi

REMOTE_DIR="/opt/mcp-trading"

echo "🚀 Deploying MCP Trading Server to $EC2_HOST..."

# 1. Create remote directory
ssh $SSH_OPTS $EC2_HOST "sudo mkdir -p $REMOTE_DIR && sudo chown \$(whoami) $REMOTE_DIR"

# 2. Copy files
echo "📦 Copying files..."
scp $SSH_OPTS \
    server.py config.py database.py binance_client.py \
    requirements.txt Dockerfile docker-compose.yml \
    $EC2_HOST:$REMOTE_DIR/

# 3. Copy .env if it exists locally
if [ -f .env ]; then
    echo "🔑 Copying .env..."
    scp $SSH_OPTS .env $EC2_HOST:$REMOTE_DIR/.env
else
    echo "⚠️  No .env found. Create one on the server: $REMOTE_DIR/.env"
fi

# 4. Build and run on EC2
echo "🐳 Building and starting container..."
ssh $SSH_OPTS $EC2_HOST "cd $REMOTE_DIR && \
    mkdir -p data && \
    docker compose down 2>/dev/null || true && \
    docker compose up -d --build"

# 5. Verify
echo "✅ Checking health..."
sleep 3
ssh $SSH_OPTS $EC2_HOST "docker compose -f $REMOTE_DIR/docker-compose.yml logs --tail 10"

echo ""
echo "═══════════════════════════════════════════════"
echo "✅ MCP Trading Server deployed!"
echo ""
echo "   URL: http://$EC2_HOST:8000/mcp"
echo ""
echo "   Connect from Kiro/Claude Desktop:"
echo "   {"
echo "     \"mcpServers\": {"
echo "       \"trading\": {"
echo "         \"url\": \"http://<EC2_PUBLIC_IP>:8000/mcp\","
echo "         \"type\": \"http\""
echo "       }"
echo "     }"
echo "   }"
echo "═══════════════════════════════════════════════"
