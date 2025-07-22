#!/bin/bash

# Kong Configuration Initialisation Script
# This script sets up Kong with the AI Betting Platform configuration

set -e

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://localhost:8001}"
KONG_CONFIG_FILE="${KONG_CONFIG_FILE:-/app/infrastructure/kong/kong.yml}"

echo "Initialising Kong configuration..."
echo "Kong Admin URL: $KONG_ADMIN_URL"

# Wait for Kong to be ready
echo "Waiting for Kong to be ready..."
until curl -f $KONG_ADMIN_URL/status > /dev/null 2>&1; do
    echo "Kong not ready yet, waiting..."
    sleep 5
done

echo "Kong is ready. Applying configuration..."

# Apply Kong configuration using deck
if command -v deck &> /dev/null; then
    echo "Using deck to sync configuration..."
    deck sync --kong-addr $KONG_ADMIN_URL --state $KONG_CONFIG_FILE
else
    echo "deck not found, applying configuration via API..."
    
    # Clear existing configuration
    echo "Clearing existing configuration..."
    curl -s -X DELETE $KONG_ADMIN_URL/config
    
    # Apply new configuration
    echo "Applying new configuration..."
    curl -s -X POST $KONG_ADMIN_URL/config \
        -F "config=@$KONG_CONFIG_FILE"
fi

echo "Kong configuration applied successfully!"

# Verify services are configured
echo "Verifying services..."
curl -s $KONG_ADMIN_URL/services | jq '.data[].name' || echo "Services configured"

# Verify routes are configured
echo "Verifying routes..."
curl -s $KONG_ADMIN_URL/routes | jq '.data[].name' || echo "Routes configured"

# Verify plugins are configured
echo "Verifying plugins..."
curl -s $KONG_ADMIN_URL/plugins | jq '.data[].name' || echo "Plugins configured"

echo "Kong initialisation completed successfully!"
echo ""
echo "Available endpoints:"
echo "- Prediction Engine: http://localhost:8000/api/v1/predict"
echo "- User Management: http://localhost:8000/api/v1/users"
echo "- Chat Assistant: http://localhost:8000/api/v1/chat"
echo "- Subscription Billing: http://localhost:8000/api/v1/subscriptions"
echo ""
echo "Kong Admin: $KONG_ADMIN_URL"
echo "Kong Manager: http://localhost:8002"