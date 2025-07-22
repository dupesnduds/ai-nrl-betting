"""Unified Prediction API that consolidates all 5 models through MoE routing."""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio

from fastapi import FastAPI, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

from shared.auth.firebase import get_current_user, require_tier, User
from shared.monitoring.telemetry import (
    setup_telemetry, 
    instrument_fastapi, 
    setup_structured_logging,
    MetricsCollector
)

from ..application.prediction_service import PredictionService
from ..application.moe_router import RoutingStrategy
from ..domain.prediction_models import MatchDetails, PredictionType, ModelType
from ....shared.events.event_bus import KafkaEventBus, InMemoryEventBus

tracer, meter = setup_telemetry("prediction-engine")
logger = setup_structured_logging("prediction-engine")

app = FastAPI(
    title="AI Betting Platform - Unified Prediction Engine",
    description="Intelligent NRL match prediction using Mixture of Experts routing across 5 models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_fastapi(app, "prediction-engine")

prediction_service: Optional[PredictionService] = None


class PredictionRequest(BaseModel):
    team_home: str = Field(..., description="Home team name")
    team_away: str = Field(..., description="Away team name")
    match_date: str = Field(..., description="Match date (YYYY-MM-DD)")
    venue: Optional[str] = Field(None, description="Match venue")
    round_num: Optional[int] = Field(None, description="Round number")
    season_year: Optional[int] = Field(None, description="Season year")
    odds_home: Optional[float] = Field(None, description="Home team odds")
    odds_away: Optional[float] = Field(None, description="Away team odds")
    odds_draw: Optional[float] = Field(None, description="Draw odds")
    prediction_type: str = Field("match_winner", description="Type of prediction")
    force_model: Optional[str] = Field(None, description="Force specific model (lr, lightgbm, transformer, stacker, rl)")


class PredictionResponse(BaseModel):
    prediction_id: str
    predicted_winner: str
    confidence: float
    probabilities: Dict[str, float]
    model_used: str
    model_name: str
    processing_time_ms: float
    routing_confidence: float
    routing_strategy: str
    predicted_margin: Optional[float] = None
    features_used: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


class BatchPredictionRequest(BaseModel):
    matches: List[PredictionRequest]
    prediction_type: str = Field("match_winner", description="Type of prediction")
    max_concurrent: int = Field(5, description="Maximum concurrent predictions")


class ModelStatusResponse(BaseModel):
    model_type: str
    name: str
    version: str
    is_ready: bool
    usage_count: int
    accuracy: Optional[float] = None
    supported_types: List[str]


class ServiceMetricsResponse(BaseModel):
    total_predictions: int
    average_processing_time_ms: float
    available_models: int
    model_usage_stats: Dict[str, int]
    routing_statistics: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize the prediction service on startup."""
    global prediction_service
    
    logger.info("Starting Unified Prediction Engine...")
    
    event_bus = None
    try:
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if kafka_servers:
            event_bus = KafkaEventBus(bootstrap_servers=kafka_servers)
            await event_bus.start()
            logger.info("Kafka event bus initialized")
        else:
            event_bus = InMemoryEventBus()
            await event_bus.start()
            logger.info("In-memory event bus initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
    
    routing_strategy = RoutingStrategy(
        os.getenv("ROUTING_STRATEGY", "performance_based")
    )
    
    prediction_service = PredictionService(
        event_bus=event_bus,
        routing_strategy=routing_strategy
    )
    
    logger.info("Warming up prediction models...")
    available_models = await prediction_service.get_available_models()
    logger.info(f"Successfully initialized {len(available_models)} prediction models")
    
    logger.info("Unified Prediction Engine started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    health = await prediction_service.health_check()
    
    if health["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )
    
    return health


@app.post("/predict", response_model=PredictionResponse)
async def predict_match(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Make a prediction for a single match."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    try:
        match_date = datetime.strptime(request.match_date, "%Y-%m-%d")
        prediction_type = PredictionType(request.prediction_type)
        force_model = ModelType(request.force_model) if request.force_model else None
        
        match_details = MatchDetails(
            team_home=request.team_home,
            team_away=request.team_away,
            match_date=match_date,
            venue=request.venue,
            round_num=request.round_num,
            season_year=request.season_year,
            odds_home=request.odds_home,
            odds_away=request.odds_away,
            odds_draw=request.odds_draw
        )
        
        MetricsCollector.record_prediction_request(
            model="unified-engine",
            team_home=request.team_home,
            team_away=request.team_away
        )
        
        result = await prediction_service.predict(
            match_details=match_details,
            prediction_type=prediction_type,
            user_id=user.uid,
            force_model=force_model
        )
        
        MetricsCollector.record_prediction_latency(
            model="unified-engine",
            duration=result.processing_time_ms / 1000
        )
        
        routing_metadata = result.model_metadata.get("moe_routing", {})
        
        logger.info(
            "Prediction completed",
            prediction_id=result.prediction_id,
            model_used=result.model_type.value,
            predicted_winner=result.predicted_winner.value,
            user_id=user.uid,
            processing_time_ms=result.processing_time_ms
        )
        
        return PredictionResponse(
            prediction_id=result.prediction_id,
            predicted_winner=result.predicted_winner.value,
            confidence=result.confidence,
            probabilities=result.probabilities,
            model_used=result.model_type.value,
            model_name=routing_metadata.get("selected_model", "unknown"),
            processing_time_ms=result.processing_time_ms,
            routing_confidence=routing_metadata.get("routing_confidence", 0.0),
            routing_strategy=routing_metadata.get("strategy", "unknown"),
            predicted_margin=result.predicted_margin,
            features_used=result.features_used or [],
            metadata=result.model_metadata
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Prediction failed",
            error=str(e),
            user_id=user.uid,
            team_home=request.team_home,
            team_away=request.team_away
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch", response_model=List[PredictionResponse])
async def predict_batch(
    request: BatchPredictionRequest,
    user: User = Depends(require_tier("premium"))
):
    """Make predictions for multiple matches (premium users only)."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    if len(request.matches) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 matches per batch request"
        )
    
    try:
        matches = []
        for match_req in request.matches:
            match_date = datetime.strptime(match_req.match_date, "%Y-%m-%d")
            match_details = MatchDetails(
                team_home=match_req.team_home,
                team_away=match_req.team_away,
                match_date=match_date,
                venue=match_req.venue,
                round_num=match_req.round_num,
                season_year=match_req.season_year,
                odds_home=match_req.odds_home,
                odds_away=match_req.odds_away,
                odds_draw=match_req.odds_draw
            )
            matches.append(match_details)
        
        prediction_type = PredictionType(request.prediction_type)
        results = await prediction_service.predict_batch(
            matches=matches,
            prediction_type=prediction_type,
            user_id=user.uid,
            max_concurrent=request.max_concurrent
        )
        
        responses = []
        for result in results:
            routing_metadata = result.model_metadata.get("moe_routing", {})
            responses.append(PredictionResponse(
                prediction_id=result.prediction_id,
                predicted_winner=result.predicted_winner.value,
                confidence=result.confidence,
                probabilities=result.probabilities,
                model_used=result.model_type.value,
                model_name=routing_metadata.get("selected_model", "unknown"),
                processing_time_ms=result.processing_time_ms,
                routing_confidence=routing_metadata.get("routing_confidence", 0.0),
                routing_strategy=routing_metadata.get("strategy", "unknown"),
                predicted_margin=result.predicted_margin,
                features_used=result.features_used or [],
                metadata=result.model_metadata
            ))
        
        logger.info(
            "Batch prediction completed",
            user_id=user.uid,
            total_matches=len(request.matches),
            successful_predictions=len(responses)
        )
        
        return responses
        
    except Exception as e:
        logger.error(
            "Batch prediction failed",
            error=str(e),
            user_id=user.uid,
            batch_size=len(request.matches)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.get("/models/status", response_model=List[ModelStatusResponse])
async def get_model_status():
    """Get status of all prediction models."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    model_status = await prediction_service.get_model_status()
    
    responses = []
    for model_type, status in model_status.items():
        responses.append(ModelStatusResponse(
            model_type=model_type,
            name=status.get("name", "Unknown"),
            version=status.get("version", "Unknown"),
            is_ready=status.get("is_ready", False),
            usage_count=status.get("usage_count", 0),
            accuracy=status.get("metrics", {}).get("accuracy") if status.get("metrics") else None,
            supported_types=status.get("supported_prediction_types", [])
        ))
    
    return responses


@app.get("/metrics", response_model=ServiceMetricsResponse)
async def get_service_metrics():
    """Get prediction service metrics."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    metrics = await prediction_service.get_service_metrics()
    service_info = metrics["service_info"]
    
    return ServiceMetricsResponse(
        total_predictions=service_info["total_predictions"],
        average_processing_time_ms=service_info["average_processing_time_ms"],
        available_models=service_info["available_models"],
        model_usage_stats=metrics["model_usage_stats"],
        routing_statistics=metrics["routing_statistics"]
    )


@app.get("/models/feature-importance")
async def get_feature_importance_comparison():
    """Get feature importance comparison across all models."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    return await prediction_service.get_feature_importance_comparison()


@app.get("/routing/statistics")
async def get_routing_statistics():
    """Get MoE routing statistics."""
    
    if not prediction_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not initialized"
        )
    
    return prediction_service.moe_router.get_routing_statistics()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Betting Platform - Unified Prediction Engine",
        "version": "1.0.0",
        "description": "Intelligent NRL match prediction using Mixture of Experts routing",
        "available_endpoints": [
            "/docs",
            "/predict",
            "/predict/batch", 
            "/models/status",
            "/metrics",
            "/health"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.interfaces.unified_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )