"""Use cases for prediction engine."""

import time
import uuid
from typing import List, Optional

from shared.data_contracts.prediction import (
    PredictionRequest, 
    PredictionResponse, 
    PredictionResult,
    PredictionType,
    ModelType
)
from ..domain.models import (
    Match, 
    PredictionModel, 
    ModelRepository, 
    DataRepository,
    FeatureEngineer
)


class PredictMatchUseCase:
    """Use case for making match predictions."""
    
    def __init__(
        self,
        model_repository: ModelRepository,
        data_repository: DataRepository,
        feature_engineer: FeatureEngineer
    ):
        self.model_repository = model_repository
        self.data_repository = data_repository
        self.feature_engineer = feature_engineer
    
    async def execute(self, request: PredictionRequest) -> PredictionResponse:
        """Execute prediction request."""
        start_time = time.time()
        
        # Create match object from request
        match = Match(
            match_id=str(uuid.uuid4()),
            team_home=request.team_home,
            team_away=request.team_away,
            match_date=request.match_date,
            venue=request.venue
        )
        
        # Get historical data for feature engineering
        historical_matches = await self.data_repository.get_historical_matches(
            request.team_home, 
            request.team_away
        )
        
        # Extract features
        features = await self.feature_engineer.extract_features(
            match, 
            historical_matches
        )
        
        # Make predictions
        predictions = []
        model_versions = {}
        
        for prediction_type in request.prediction_types:
            # Determine which models to use
            models_to_use = request.models or [ModelType.ENSEMBLE]
            
            for model_type in models_to_use:
                try:
                    model = await self.model_repository.load_model(model_type)
                    
                    if prediction_type in model.supported_prediction_types:
                        prediction_output = await model.predict(features, prediction_type)
                        
                        prediction_result = PredictionResult(
                            prediction_type=prediction_output.prediction_type,
                            model_used=prediction_output.model_type,
                            predicted_value=prediction_output.predicted_value,
                            confidence=prediction_output.confidence if request.include_confidence else None,
                            probability_home=prediction_output.probabilities.get("home"),
                            probability_away=prediction_output.probabilities.get("away"),
                            probability_draw=prediction_output.probabilities.get("draw"),
                            explanation=prediction_output.metadata if request.include_explanation else None,
                            metadata=prediction_output.metadata
                        )
                        
                        predictions.append(prediction_result)
                        model_versions[model_type.value] = prediction_output.model_version
                        
                        # Save prediction for tracking
                        await self.model_repository.save_prediction(
                            match, 
                            prediction_output
                        )
                
                except Exception as e:
                    # Log error but continue with other models
                    # In production, use proper logging
                    print(f"Error with model {model_type}: {e}")
                    continue
        
        # Calculate ensemble prediction if multiple models used
        ensemble_prediction = None
        if len(predictions) > 1:
            ensemble_prediction = await self._create_ensemble_prediction(predictions)
        
        processing_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            prediction_id=str(uuid.uuid4()),
            request=request,
            predictions=predictions,
            ensemble_prediction=ensemble_prediction,
            processing_time_ms=processing_time,
            model_versions=model_versions
        )
    
    async def _create_ensemble_prediction(
        self, 
        predictions: List[PredictionResult]
    ) -> PredictionResult:
        """Create ensemble prediction from multiple model outputs."""
        # Simple averaging ensemble - can be made more sophisticated
        if not predictions:
            raise ValueError("No predictions to ensemble")
        
        # Group predictions by type
        by_type = {}
        for pred in predictions:
            if pred.prediction_type not in by_type:
                by_type[pred.prediction_type] = []
            by_type[pred.prediction_type].append(pred)
        
        # For now, just return the first prediction type with ensemble averaging
        first_type = list(by_type.keys())[0]
        type_predictions = by_type[first_type]
        
        # Average probabilities
        avg_prob_home = sum(p.probability_home or 0 for p in type_predictions) / len(type_predictions)
        avg_prob_away = sum(p.probability_away or 0 for p in type_predictions) / len(type_predictions)
        avg_prob_draw = sum(p.probability_draw or 0 for p in type_predictions) / len(type_predictions)
        
        # Average confidence
        avg_confidence = sum(p.confidence or 0 for p in type_predictions) / len(type_predictions)
        
        # Determine predicted value based on highest probability
        if avg_prob_home > avg_prob_away and avg_prob_home > avg_prob_draw:
            predicted_value = "home"
        elif avg_prob_away > avg_prob_draw:
            predicted_value = "away"
        else:
            predicted_value = "draw"
        
        return PredictionResult(
            prediction_type=first_type,
            model_used=ModelType.ENSEMBLE,
            predicted_value=predicted_value,
            confidence=avg_confidence,
            probability_home=avg_prob_home,
            probability_away=avg_prob_away,
            probability_draw=avg_prob_draw,
            metadata={"ensemble_size": len(type_predictions)}
        )


class GetModelPerformanceUseCase:
    """Use case for retrieving model performance metrics."""
    
    def __init__(self, model_repository: ModelRepository):
        self.model_repository = model_repository
    
    async def execute(
        self, 
        model_type: ModelType, 
        prediction_type: PredictionType,
        days: int = 30
    ) -> dict:
        """Get model performance metrics."""
        return await self.model_repository.get_model_performance(
            model_type, 
            prediction_type, 
            days
        )