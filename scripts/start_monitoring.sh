#!/bin/bash

# Start the monitoring stack
echo "Starting AI Betting Platform Monitoring Stack..."
echo "================================================"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

cd "$(dirname "$0")/../monitoring" || exit 1

echo "Starting monitoring services..."

if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

echo "Waiting for services to start..."
sleep 10

echo ""
echo "Checking service status..."
if command -v docker-compose &> /dev/null; then
    docker-compose ps
else
    docker compose ps
fi

echo ""
echo "Monitoring stack started successfully!"
echo ""
echo "Access the monitoring dashboards:"
echo "  - Grafana:      http://localhost:3000 (admin/admin123)"
echo "  - Prometheus:   http://localhost:9090"
echo "  - Alertmanager: http://localhost:9093"
echo "  - Jaeger:       http://localhost:16686"
echo ""
echo "Key dashboards available in Grafana:"
echo "  - AI Betting Platform - Prediction Engine"
echo "  - Infrastructure Overview"
echo "  - Model Performance Comparison"
echo ""
echo "To stop the monitoring stack:"
echo "  cd monitoring && docker-compose down"