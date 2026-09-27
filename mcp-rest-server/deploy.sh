#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="mcp-rest-server"
IMAGE_TAG="latest"

echo "=========================================================="
echo "🚀 FastMCP REST API Server - Automated Container Deployment"
echo "=========================================================="

# 1. Check Docker Installation
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH."
    exit 1
fi

# 2. Check Environment Configuration
if [ ! -f ".env" ]; then
    echo "⚠️ Warning: .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "👉 Created .env file. Please edit .env with your actual API credentials."
fi

# 3. Build Docker Image
echo "📦 Building Docker image '${IMAGE_NAME}:${IMAGE_TAG}'..."
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile .

echo "✅ Docker image built successfully."

# 4. Generate Client mcp_config.json snippet
CONFIG_SNIPPET=$(cat <<EOF
{
  "mcpServers": {
    "${IMAGE_NAME}": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file", "${SCRIPT_DIR}/.env",
        "${IMAGE_NAME}:${IMAGE_TAG}"
      ]
    }
  }
}
EOF
)

echo "=========================================================="
echo "🎉 Deployment Setup Complete!"
echo "=========================================================="
echo "To register this Dockerized MCP Server with Antigravity or your MCP client,"
echo "add the following entry to your mcp_config.json:"
echo ""
echo "$CONFIG_SNIPPET"
echo "=========================================================="
