#!/bin/bash
# Deploy MCP Trading Server to EC2
# Usage: ./deploy.sh <user@host> [ssh-key-path]
# Example: ./deploy.sh ubuntu@54.123.45.67 ~/.ssh/my-key.pem

set -e

EC2_HOST=${1:?"Usage: ./deploy.sh <user@host> [ssh-key-path]"}
SSH_KEY=${2:-""}
SSH_CMD="ssh"
SCP_CMD="scp"

if [ -n "$SSH_KEY" ]; then
    SSH_CMD="ssh -i $SSH_KEY"
    SCP_CMD="scp -i $SSH_KEY"
fi

REMOTE_DIR="/opt/mcp-trading"

echo "🚀 Deploying MCP Trading Server to $EC2_HOST..."
echo ""

# 1. Create remote directory structure
echo "📁 Creating directories..."
$SSH_CMD $EC2_HOST "sudo mkdir -p $REMOTE_DIR/src/{core,clients,tools} $REMOTE_DIR/data && sudo chown -R \$(whoami) $REMOTE_DIR"

# 2. Copy root files
echo "📦 Copying root files..."
$SCP_CMD server.py requirements.txt Dockerfile docker-compose.yml $EC2_HOST:$REMOTE_DIR/

# 3. Copy src/
echo "📦 Copying src/..."
$SCP_CMD src/__init__.py $EC2_HOST:$REMOTE_DIR/src/
$SCP_CMD src/core/__init__.py src/core/config.py src/core/database.py src/core/safety.py $EC2_HOST:$REMOTE_DIR/src/core/
$SCP_CMD src/clients/__init__.py src/clients/binance.py $EC2_HOST:$REMOTE_DIR/src/clients/
$SCP_CMD src/tools/__init__.py src/tools/analysis.py src/tools/trading.py src/tools/portfolio.py src/tools/system.py $EC2_HOST:$REMOTE_DIR/src/tools/

# 4. Copy .env
if [ -f .env ]; then
    echo "🔑 Copying .env..."
    $SCP_CMD .env $EC2_HOST:$REMOTE_DIR/.env
else
    echo "⚠️  No .env found locally. You'll need to create it on the server."
    echo "   $SSH_CMD $EC2_HOST 'nano $REMOTE_DIR/.env'"
fi

# 5. Build and run
echo ""
echo "🐳 Building Docker image and starting..."
$SSH_CMD $EC2_HOST "cd $REMOTE_DIR && docker compose down 2>/dev/null || true && docker compose up -d --build"

# 6. Wait and verify
echo ""
echo "⏳ Waiting for server to start..."
sleep 5
$SSH_CMD $EC2_HOST "docker compose -f $REMOTE_DIR/docker-compose.yml logs --tail 15"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ MCP Trading Server deployed!"
echo ""
echo "   Endpoint: http://$EC2_HOST:8000/mcp"
echo ""
echo "   Kiro Web config:"
echo '   {'
echo '     "mcpServers": {'
echo '       "trading": {'
echo "         \"url\": \"http://<PUBLIC_IP>:8000/mcp\","
echo '         "type": "http"'
echo '       }'
echo '     }'
echo '   }'
echo "═══════════════════════════════════════════════════════════"
