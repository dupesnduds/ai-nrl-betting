"""Unified prediction service that orchestrates all models through MoE routing."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import uuid

from ..domain.prediction_models import (
    PredictionModel, ModelType, PredictionType, MatchDetails, 
    PredictionResult, ModelRepository
)
from ..infrastructure.models.lr_predictor import LogisticRegressionPredictor
from ..infrastructure.models.lightgbm_predictor import LightGBMPredictor
from ..infrastructure.models.transformer_predictor import TransformerPredictor
from ..infrastructure.models.stacker_predictor import StackerPredictor
from ..infrastructure.models.rl_predictor import ReinforcementLearningPredictor
from .moe_router import MixtureOfExpertsRouter, RoutingStrategy
from ....shared.events.event_bus import (
    EventBus, PredictionRequestedEvent, PredictionCompletedEvent, EventType
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Unified prediction service with MoE routing."""
    
    def __init__(
        self,
        model_repository: Optional[ModelRepository] = None,
        event_bus: Optional[EventBus] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.PERFORMANCE_BASED
    ):
        """Initialize prediction service."""
        self.model_repository = model_repository
        self.event_bus = event_bus
        self.moe_router = MixtureOfExpertsRouter(routing_strategy)
        
        self.models: Dict[ModelType, PredictionModel] = {}
        self._initialize_models()
        
        self.prediction_count = 0
        self.total_processing_time = 0.0
        self.model_usage_stats = {model_type: 0 for model_type in ModelType}
        
    def _initialize_models(self):
        """Initialize all prediction models."""
        try:
            self.models[ModelType.LOGISTIC_REGRESSION] = LogisticRegressionPredictor()
            logger.info("Initialized Logistic Regression predictor")
        except Exception as e:
            logger.error(f"Failed to initialize LR predictor: {e}")
        
        try:
            self.models[ModelType.LIGHTGBM] = LightGBMPredictor()
            logger.info("Initialized LightGBM predictor")
        except Exception as e:
            logger.error(f"Failed to initialize LightGBM predictor: {e}")
        
        try:
            self.models[ModelType.TRANSFORMER] = TransformerPredictor()
            logger.info("Initialized Transformer predictor")
        except Exception as e:
            logger.error(f"Failed to initialize Transformer predictor: {e}")
        
        try:
            self.models[ModelType.STACKER] = StackerPredictor()
            logger.info("Initialized Stacker predictor")
        except Exception as e:
            logger.error(f"Failed to initialize Stacker predictor: {e}")
        
        try:
            self.models[ModelType.REINFORCEMENT_LEARNING] = ReinforcementLearningPredictor()
            logger.info("Initialized RL predictor")
        except Exception as e:
            logger.error(f"Failed to initialize RL predictor: {e}")
        
        logger.info(f"Initialized {len(self.models)} prediction models")
    
    async def get_available_models(self) -> List[PredictionModel]:
        """Get list of available and ready models."""
        available_models = []
        
        for model in self.models.values():
            try:
                if await model.is_ready():
                    available_models.append(model)
            except Exception as e:
                logger.warning(f"Model {model.model_type.value} not ready: {e}")
        
        return available_models
    
    async def predict(
        self,
        match_details: MatchDetails,
        prediction_type: PredictionType = PredictionType.MATCH_WINNER,
        user_id: Optional[str] = None,
        force_model: Optional[ModelType] = None
    ) -> PredictionResult:
        """Make a prediction using MoE routing or forced model."""
        
        start_time = time.time()
        prediction_id = str(uuid.uuid4())
        
        if self.event_bus:
            try:
                event = PredictionRequestedEvent(
                    event_id="",
                    event_type=EventType.PREDICTION_REQUESTED,
                    timestamp=None,
                    correlation_id=prediction_id,
                    source_service="prediction-engine",
                    user_id=user_id or "anonymous",
                    team_home=match_details.team_home,
                    team_away=match_details.team_away,
                    prediction_types=[prediction_type.value],
                    match_date=match_details.match_date.strftime('%Y-%m-%d')
                )
                await self.event_bus.publish(event)
            except Exception as e:
                logger.warning(f"Failed to publish prediction requested event: {e}")
        
        try:
            available_models = await self.get_available_models()
            
            if not available_models:
                raise RuntimeError("No prediction models are available")
            
            if force_model:
                selected_model = None
                for model in available_models:
                    if model.model_type == force_model:
                        selected_model = model
                        break
                
                if not selected_model:
                    raise ValueError(f"Forced model {force_model.value} not available")
                
                routing_confidence = 1.0
                routing_metadata = {
                    "strategy": "forced",
                    "selected_model": force_model.value,
                    "routing_confidence": 1.0,
                    "forced": True
                }
            else:
                selected_model, routing_confidence, routing_metadata = await self.moe_router.route_prediction(
                    match_details, available_models, prediction_type
                )
            
            prediction_result = await selected_model.predict(match_details, prediction_type)
            
            if prediction_result.model_metadata is None:
                prediction_result.model_metadata = {}
            
            prediction_result.model_metadata.update({
                "moe_routing": routing_metadata,
                "prediction_service_id": prediction_id,
                "total_available_models": len(available_models),
                "service_prediction_count": self.prediction_count + 1
            })
            
            self.prediction_count += 1
            processing_time = (time.time() - start_time) * 1000
            self.total_processing_time += processing_time
            self.model_usage_stats[selected_model.model_type] += 1
            
            if self.model_repository:
                try:
                    saved_id = await self.model_repository.save_prediction(prediction_result)
                    prediction_result.model_metadata["repository_id"] = saved_id
                except Exception as e:
                    logger.warning(f"Failed to save prediction to repository: {e}")
            
            if self.event_bus:
                try:
                    predictions_data = [{
                        "type": prediction_type.value,
                        "predicted_winner": prediction_result.predicted_winner.value,
                        "confidence": prediction_result.confidence,
                        "model": selected_model.model_type.value
                    }]
                    
                    event = PredictionCompletedEvent(
                        event_id="",
                        event_type=EventType.PREDICTION_COMPLETED,
                        timestamp=None,
                        correlation_id=prediction_id,
                        source_service="prediction-engine",
                        prediction_id=prediction_result.prediction_id,
                        user_id=user_id or "anonymous",
                        team_home=match_details.team_home,
                        team_away=match_details.team_away,
                        predictions=predictions_data,
                        processing_time_ms=processing_time
                    )
                    await self.event_bus.publish(event)
                except Exception as e:
                    logger.warning(f"Failed to publish prediction completed event: {e}")
            
            logger.info(
                f"Prediction completed successfully",
                extra={
                    "prediction_id": prediction_result.prediction_id,
                    "model_used": selected_model.model_type.value,
                    "routing_confidence": routing_confidence,
                    "processing_time_ms": processing_time,
                    "predicted_winner": prediction_result.predicted_winner.value
                }
            )
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise
    
    async def predict_batch(
        self,
        matches: List[MatchDetails],
        prediction_type: PredictionType = PredictionType.MATCH_WINNER,
        user_id: Optional[str] = None,
        max_concurrent: int = 5
    ) -> List[PredictionResult]:
        """Make predictions for multiple matches concurrently."""
        
        logger.info(f"Starting batch prediction for {len(matches)} matches")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def predict_single(match_details: MatchDetails) -> Optional[PredictionResult]:
            async with semaphore:
                try:
                    return await self.predict(match_details, prediction_type, user_id)
                except Exception as e:
                    logger.error(f"Batch prediction failed for match {match_details.match_id}: {e}")
                    return None
        
        tasks = [predict_single(match) for match in matches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = [
            result for result in results 
            if isinstance(result, PredictionResult)
        ]
        
        logger.info(
            f"Batch prediction completed: {len(successful_results)}/{len(matches)} successful",
            extra={
                "total_matches": len(matches),
                "successful_predictions": len(successful_results),
                "failed_predictions": len(matches) - len(successful_results)
            }
        )
        
        return successful_results
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of all prediction models."""
        model_status = {}
        
        for model_type, model in self.models.items():
            try:
                is_ready = await model.is_ready()
                metrics = await model.get_model_metrics() if is_ready else None
                
                model_status[model_type.value] = {
                    "name": model.model_name,
                    "version": model.model_version,
                    "is_ready": is_ready,
                    "supported_prediction_types": [pt.value for pt in model.supported_prediction_types],
                    "usage_count": self.model_usage_stats.get(model_type, 0),
                    "metrics": {
                        "accuracy": metrics.accuracy if metrics else None,
                        "last_updated": metrics.last_updated.isoformat() if metrics and metrics.last_updated else None
                    } if metrics else None
                }
            except Exception as e:
                model_status[model_type.value] = {
                    "name": getattr(model, 'model_name', 'Unknown'),
                    "is_ready": False,
                    "error": str(e)
                }
        
        return model_status
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get prediction service metrics."""
        available_models = await self.get_available_models()
        routing_stats = self.moe_router.get_routing_statistics()
        
        avg_processing_time = (
            self.total_processing_time / self.prediction_count 
            if self.prediction_count > 0 else 0
        )
        
        return {
            "service_info": {
                "total_predictions": self.prediction_count,
                "average_processing_time_ms": avg_processing_time,
                "available_models": len(available_models),
                "total_models": len(self.models)
            },
            "model_usage_stats": {
                model_type.value: count 
                for model_type, count in self.model_usage_stats.items()
            },
            "routing_statistics": routing_stats,
            "model_availability": {
                model.model_type.value: await model.is_ready()
                for model in self.models.values()
            }
        }
    
    async def get_feature_importance_comparison(self) -> Dict[str, Dict[str, float]]:
        """Get feature importance from all available models."""
        feature_importance_comparison = {}
        
        available_models = await self.get_available_models()
        
        for model in available_models:
            try:
                importance = await model.get_feature_importance()
                feature_importance_comparison[model.model_type.value] = importance
            except Exception as e:
                logger.warning(f"Failed to get feature importance from {model.model_type.value}: {e}")
        
        return feature_importance_comparison
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of the prediction service."""
        available_models = await self.get_available_models()
        
        health_status = {
            "status": "healthy" if available_models else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "available_models": len(available_models),
            "total_models": len(self.models),
            "total_predictions": self.prediction_count,
            "moe_router_ready": self.moe_router is not None,
            "event_bus_connected": self.event_bus is not None,
            "model_repository_connected": self.model_repository is not None
        }
        
        health_status["model_health"] = {}
        for model_type, model in self.models.items():
            try:
                is_ready = await model.is_ready()
                health_status["model_health"][model_type.value] = {
                    "ready": is_ready,
                    "name": model.model_name
                }
            except Exception as e:
                health_status["model_health"][model_type.value] = {
                    "ready": False,
                    "error": str(e)
                }
        
        return health_status