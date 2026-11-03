#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Stopping CDC Customs & Quota Manager container..."
docker compose down
echo "✅ Stopped successfully."

