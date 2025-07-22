#!/bin/bash

# AI Betting Platform - Development Setup Script
# This script sets up the complete development environment

set -e

echo "Setting up AI Betting Platform development environment..."

# Check prerequisites
echo "Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Prerequisites check completed"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p {config,logs,models/trained,infrastructure/{database/init,monitoring/{prometheus,grafana/{dashboards,datasources}}}}

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating environment configuration..."
    cat > .env << EOF
# Database Configuration
DB_USER=developer
DB_PASSWORD=dev_password
MONGO_USER=developer
MONGO_PASSWORD=dev_password

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Monitoring Configuration
GRAFANA_PASSWORD=admin

# Environment
ENVIRONMENT=development
SERVICE_VERSION=1.0.0

# Prometheus Configuration
PROMETHEUS_PORT=9090

# Firebase Configuration (update with your project details)
FIREBASE_SERVICE_ACCOUNT_PATH=./config/firebase-service-account.json
EOF
    echo "Created .env file - please update with your Firebase configuration"
fi

# Install Python dependencies for the workspace
echo "Installing Python dependencies..."
poetry install

# Create placeholder model files
echo "Setting up model files..."
mkdir -p models/trained
if [ ! -f models/trained/logistic_regression_model.joblib ]; then
    echo "Creating placeholder model file..."
    touch models/trained/logistic_regression_model.joblib
fi

# Create Prometheus configuration
echo "Setting up monitoring configuration..."
cat > infrastructure/monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'prediction-engine'
    static_configs:
      - targets: ['prediction-engine:9090']
    metrics_path: '/metrics'
    scrape_interval: 10s
EOF

# Create basic Grafana datasource configuration
cat > infrastructure/monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Create database initialisation script
cat > infrastructure/database/init/01-init.sql << EOF
-- AI Betting Platform Database Initialisation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables for prediction storage
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id VARCHAR(255) NOT NULL,
    team_home VARCHAR(255) NOT NULL,
    team_away VARCHAR(255) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    predicted_value TEXT,
    confidence DECIMAL(5,4),
    probabilities JSONB,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id);

-- Create teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    elo_rating DECIMAL(10,2) DEFAULT 1500.0,
    home_win_rate DECIMAL(5,4),
    away_win_rate DECIMAL(5,4),
    avg_points_scored DECIMAL(6,2),
    avg_points_conceded DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create matches table
CREATE TABLE IF NOT EXISTS matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id VARCHAR(255) UNIQUE NOT NULL,
    team_home VARCHAR(255) NOT NULL,
    team_away VARCHAR(255) NOT NULL,
    match_date TIMESTAMP NOT NULL,
    venue VARCHAR(255),
    home_score INTEGER,
    away_score INTEGER,
    season INTEGER,
    round_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_match_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(team_home, team_away);

-- Insert sample NRL teams
INSERT INTO teams (name) VALUES 
    ('Brisbane Broncos'),
    ('Sydney Roosters'),
    ('Melbourne Storm'),
    ('Penrith Panthers'),
    ('North Queensland Cowboys'),
    ('South Sydney Rabbitohs'),
    ('Canterbury Bulldogs'),
    ('Parramatta Eels'),
    ('Newcastle Knights'),
    ('Cronulla Sharks'),
    ('St George Illawarra Dragons'),
    ('Wests Tigers'),
    ('Gold Coast Titans'),
    ('Manly Sea Eagles'),
    ('New Zealand Warriors'),
    ('Canberra Raiders')
ON CONFLICT (name) DO NOTHING;
EOF

# Create Makefile for common development tasks
cat > Makefile << EOF
.PHONY: help build start stop test clean logs shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", \$1, \$2}' \$(MAKEFILE_LIST)

build: ## Build all services
	docker-compose build

start: ## Start all services
	docker-compose up -d

stop: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

test: ## Run tests
	poetry run pytest testing/

test-unit: ## Run unit tests only
	poetry run pytest testing/unit/

test-integration: ## Run integration tests only
	poetry run pytest testing/integration/

logs: ## Show logs for all services
	docker-compose logs -f

logs-prediction: ## Show logs for prediction engine
	docker-compose logs -f prediction-engine

shell-prediction: ## Open shell in prediction engine container
	docker-compose exec prediction-engine /bin/bash

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

install: ## Install dependencies
	poetry install

format: ## Format code
	poetry run black .
	poetry run ruff --fix .

lint: ## Lint code
	poetry run ruff .
	poetry run mypy .

setup: ## Initial setup
	./tools/scripts/dev-setup.sh

health: ## Check service health
	curl -f http://localhost:8001/health || echo "Prediction Engine not healthy"
	curl -f http://localhost:8000/health || echo "API Gateway not healthy"
EOF

# Create pre-commit configuration
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
EOF

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
poetry run pre-commit install

# Create GitHub Actions workflow
mkdir -p .github/workflows
cat > .github/workflows/ci.yml << EOF
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python \${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: \${{ matrix.python-version }}

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "\$HOME/.local/bin" >> \$GITHUB_PATH

    - name: Install dependencies
      run: |
        poetry install

    - name: Run linting
      run: |
        poetry run ruff .
        poetry run mypy .

    - name: Run formatting check
      run: |
        poetry run black --check .

    - name: Run tests
      run: |
        poetry run pytest testing/ --cov=src --cov-report=xml

    - name: Security scan
      run: |
        poetry run safety check

  build:
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v4

    - name: Build Docker images
      run: |
        docker-compose build

    - name: Test containers
      run: |
        docker-compose up -d
        sleep 30
        curl -f http://localhost:8001/health
        docker-compose down
EOF

echo "Development environment setup completed!"
echo ""
echo "Next steps:"
echo "1. Update the Firebase configuration in config/ directory"
echo "2. Run 'make start' to start all services"
echo "3. Visit http://localhost:8001/docs to see the API documentation"
echo "4. Visit http://localhost:3000 to access Grafana (admin/admin)"
echo "5. Visit http://localhost:9090 to access Prometheus"
echo ""
echo "Available commands:"
echo "  make start    - Start all services"
echo "  make stop     - Stop all services"
echo "  make test     - Run tests"
echo "  make logs     - View logs"
echo "  make help     - Show all available commands"