#!/bin/bash
set -e

# Change to project root directory
cd "$(dirname "$0")"

echo "=================================================="
echo " Starting CDC Customs & Quota Manager in Docker"
echo "=================================================="

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH."
    echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker daemon is not running."
    echo "Please start Docker Desktop and run this script again."
    exit 1
fi

echo "📦 Building and starting container..."
docker compose up -d --build

echo "⏳ Waiting for application to initialize..."
for i in {1..30}; do
    if curl -s -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "✅ Application is ready!"
        break
    fi
    sleep 1
done

URL="http://localhost:8501"
echo ""
echo "=================================================="
echo "🚀 CDC Customs & Quota Manager is running!"
echo "   URL: $URL"
echo "=================================================="
echo "💡 Commands:"
echo "   • View logs:  docker compose logs -f"
echo "   • Stop app:   ./stop_docker.sh (or 'docker compose down')"
echo "=================================================="

# Automatically open in browser on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$URL"
elif command -v xdg-open &> /dev/null; then
    xdg-open "$URL"
fi

