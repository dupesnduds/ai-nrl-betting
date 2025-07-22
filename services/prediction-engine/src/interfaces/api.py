"""FastAPI interface for prediction engine service."""

import os
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.firebase import get_current_user, require_tier, User
from shared.monitoring.telemetry import (
    setup_telemetry, 
    instrument_fastapi, 
    setup_structured_logging,
    MetricsCollector
)
from shared.data_contracts.prediction import (
    PredictionRequest, 
    PredictionResponse,
    ModelType,
    PredictionType
)

from ..application.use_cases import PredictMatchUseCase, GetModelPerformanceUseCase
from ..infrastructure.repositories import (
    DatabaseModelRepository, 
    DatabaseDataRepository,
    CachedDataRepository
)
from ..infrastructure.feature_engineering import StandardFeatureEngineer


# Configure telemetry and logging
tracer, meter = setup_telemetry("prediction-engine")
logger = setup_structured_logging("prediction-engine")

# Create FastAPI app
app = FastAPI(
    title="AI Betting Platform - Prediction Engine",
    description="Enterprise-grade prediction engine for NRL match outcomes",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, "prediction-engine")

# Global dependencies (in production, these would be properly configured)
redis_client = None
db_session = None
model_repository = None
data_repository = None
feature_engineer = None
predict_use_case = None
performance_use_case = None


@app.on_event("startup")
async def startup_event():
    """Initialise dependencies on startup."""
    global redis_client, db_session, model_repository, data_repository
    global feature_engineer, predict_use_case, performance_use_case
    
    logger.info("Starting Prediction Engine service...")
    
    # Configure Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    
    # Configure models path
    models_path = Path(os.getenv("MODELS_PATH", "../../models/trained"))
    
    # Initialise repositories
    # Note: In production, db_session would be properly configured with SQLAlchemy
    model_repository = DatabaseModelRepository(db_session, models_path)
    db_data_repository = DatabaseDataRepository(db_session)
    data_repository = CachedDataRepository(db_data_repository, redis_client)
    
    # Initialise feature engineering
    feature_engineer = StandardFeatureEngineer(data_repository)
    
    # Initialise use cases
    predict_use_case = PredictMatchUseCase(
        model_repository, 
        data_repository, 
        feature_engineer
    )
    performance_use_case = GetModelPerformanceUseCase(model_repository)
    
    logger.info("Prediction Engine service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global redis_client
    
    logger.info("Shutting down Prediction Engine service...")
    
    if redis_client:
        await redis_client.close()
    
    logger.info("Prediction Engine service shut down successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "prediction-engine",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check if models are loaded
        lr_model = await model_repository.load_model(ModelType.LOGISTIC_REGRESSION)
        is_ready = await lr_model.is_ready()
        
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Models not ready"
            )
        
        return {
            "status": "ready",
            "models_loaded": True
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@app.post("/predict", response_model=PredictionResponse)
async def predict_match(
    request: PredictionRequest,
    user: User = Depends(get_current_user)
):
    """Make predictions for a match."""
    
    # Check tier access for premium features
    if request.include_explanation and user.tier != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Explanations require premium tier"
        )
    
    try:
        # Record metrics
        MetricsCollector.record_prediction_request(
            model="ensemble",
            team_home=request.team_home,
            team_away=request.team_away
        )
        
        # Execute prediction
        response = await predict_use_case.execute(request)
        
        # Record latency
        MetricsCollector.record_prediction_latency(
            model="ensemble", 
            duration=response.processing_time_ms / 1000
        )
        
        logger.info(
            "Prediction completed",
            prediction_id=response.prediction_id,
            team_home=request.team_home,
            team_away=request.team_away,
            user_id=user.uid,
            processing_time_ms=response.processing_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Prediction failed",
            error=str(e),
            team_home=request.team_home,
            team_away=request.team_away,
            user_id=user.uid
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.get("/models")
async def list_available_models():
    """List available prediction models."""
    return {
        "models": [
            {
                "type": ModelType.LOGISTIC_REGRESSION,
                "name": "Logistic Regression",
                "supported_predictions": [PredictionType.MATCH_WINNER],
                "description": "Fast and reliable baseline model"
            },
            # TODO: Add other models as they're implemented
        ]
    }


@app.get("/models/{model_type}/performance")
async def get_model_performance(
    model_type: ModelType,
    prediction_type: PredictionType = PredictionType.MATCH_WINNER,
    days: int = 30,
    user: User = Depends(require_tier("registered"))
):
    """Get model performance metrics."""
    
    try:
        performance = await performance_use_case.execute(
            model_type, 
            prediction_type, 
            days
        )
        
        return {
            "model_type": model_type,
            "prediction_type": prediction_type,
            "evaluation_period_days": days,
            "metrics": performance
        }
        
    except Exception as e:
        logger.error(
            "Failed to get model performance",
            error=str(e),
            model_type=model_type,
            prediction_type=prediction_type
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@app.get("/teams/{team_name}/stats")
async def get_team_statistics(
    team_name: str,
    user: User = Depends(get_current_user)
):
    """Get team statistics."""
    
    try:
        stats = await data_repository.get_team_stats(team_name)
        
        return {
            "team_name": stats.team_name,
            "elo_rating": stats.elo_rating,
            "recent_form": stats.recent_form,
            "avg_points_scored": stats.avg_points_scored,
            "avg_points_conceded": stats.avg_points_conceded,
            "home_win_rate": stats.home_win_rate,
            "away_win_rate": stats.away_win_rate,
            "injury_count": stats.injury_count
        }
        
    except Exception as e:
        logger.error(
            "Failed to get team statistics",
            error=str(e),
            team_name=team_name
        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team statistics not found: {team_name}"
        )


@app.get("/metrics")
async def get_service_metrics():
    """Get service metrics (for monitoring)."""
    # This would typically be handled by Prometheus scraping
    # but provided here for debugging/monitoring
    
    return {
        "service": "prediction-engine",
        "status": "operational",
        "models_loaded": 1,
        "cache_status": "active" if redis_client else "disabled"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.interfaces.api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )