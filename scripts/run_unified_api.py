#!/usr/bin/env python3
"""
Script to run the unified prediction API with proper environment setup.
"""

import os
import sys
import subprocess
import uvicorn
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
services_root = project_root / "services" / "prediction-engine"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(services_root))

def setup_environment():
    """Set up environment variables for the unified API."""
    
    # Core service configuration
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("SERVICE_VERSION", "1.0.0")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    
    # API configuration
    os.environ.setdefault("API_HOST", "0.0.0.0")
    os.environ.setdefault("API_PORT", "8001")
    
    # Database configuration (if needed)
    os.environ.setdefault("DATABASE_URL", "sqlite:///./prediction_engine.db")
    
    # Redis configuration (if available)
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    
    # Event bus configuration
    os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "")  # Empty means use in-memory
    
    # Routing strategy for MoE
    os.environ.setdefault("ROUTING_STRATEGY", "performance_based")
    
    # Monitoring configuration
    os.environ.setdefault("PROMETHEUS_PORT", "8000")
    
    # Model paths (using existing trained models)
    models_root = project_root.parent
    os.environ.setdefault("LR_MODEL_PATH", str(models_root / "logistic-regression-predictor"))
    os.environ.setdefault("LIGHTGBM_MODEL_PATH", str(models_root / "lightgbm-predictor"))
    os.environ.setdefault("TRANSFORMER_MODEL_PATH", str(models_root / "transformer-predictor"))
    os.environ.setdefault("STACKER_MODEL_PATH", str(models_root / "stacker-predictor"))
    os.environ.setdefault("RL_MODEL_PATH", str(models_root / "reinforcement-learning-predictor"))
    
    print("Environment setup complete:")
    print(f"  - API Host: {os.getenv('API_HOST')}")
    print(f"  - API Port: {os.getenv('API_PORT')}")
    print(f"  - Environment: {os.getenv('ENVIRONMENT')}")
    print(f"  - Routing Strategy: {os.getenv('ROUTING_STRATEGY')}")
    print(f"  - Models Root: {models_root}")

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import fastapi
        import uvicorn
        import pydantic
        import structlog
        print("Core dependencies available")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run: pip install fastapi uvicorn pydantic structlog")
        return False

def run_unified_api():
    """Run the unified prediction API."""
    
    print("Starting AI Betting Platform - Unified Prediction Engine...")
    print("=" * 60)
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Change to services directory
    os.chdir(services_root)
    
    try:
        # Import and run the unified API
        print("\nStarting unified prediction API...")
        print(f"Access the API at: http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}")
        print(f"API Documentation: http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}/docs")
        print(f"Metrics endpoint: http://{os.getenv('API_HOST')}:{os.getenv('PROMETHEUS_PORT')}/metrics")
        print("\nPress Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the unified API
        uvicorn.run(
            "src.interfaces.unified_api:app",
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8001")),
            reload=True,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        return True
    except Exception as e:
        print(f"\nError starting API: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're in the correct directory")
        print("2. Check that all dependencies are installed")
        print("3. Verify model paths exist")
        print("4. Check for port conflicts")
        return False

if __name__ == "__main__":
    success = run_unified_api()
    sys.exit(0 if success else 1)