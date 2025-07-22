"""Logistic Regression prediction model implementation."""

import time
from typing import List, Dict, Any
import numpy as np
import joblib
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from shared.data_contracts.prediction import PredictionType, ModelType
from ...domain.models import PredictionModel, PredictionFeatures, PredictionOutput


class LogisticRegressionModel(PredictionModel):
    """Logistic Regression implementation for match predictions."""
    
    def __init__(self, model_path: Path):
        """Initialise the logistic regression model."""
        self.model_path = model_path
        self._pipeline = None
        self._feature_names = None
        self._version = "1.0.0"
        self._is_loaded = False
    
    @property
    def model_type(self) -> ModelType:
        """Return the model type."""
        return ModelType.LOGISTIC_REGRESSION
    
    @property
    def supported_prediction_types(self) -> List[PredictionType]:
        """Return supported prediction types."""
        return [PredictionType.MATCH_WINNER]
    
    @property
    def model_version(self) -> str:
        """Return the model version."""
        return self._version
    
    async def is_ready(self) -> bool:
        """Check if the model is ready to make predictions."""
        if not self._is_loaded:
            await self._load_model()
        return self._is_loaded and self._pipeline is not None
    
    async def predict(
        self, 
        features: PredictionFeatures, 
        prediction_type: PredictionType
    ) -> PredictionOutput:
        """Make a prediction using the logistic regression model."""
        if prediction_type not in self.supported_prediction_types:
            raise ValueError(f"Unsupported prediction type: {prediction_type}")
        
        if not await self.is_ready():
            raise RuntimeError("Model is not ready for predictions")
        
        start_time = time.time()
        
        # Extract features for prediction
        feature_vector = self._extract_feature_vector(features)
        
        # Make prediction
        probabilities = self._pipeline.predict_proba([feature_vector])[0]
        predicted_class_idx = np.argmax(probabilities)
        
        # Map to standard outcomes
        class_names = ["away_win", "draw", "home_win"]  # Assuming this order
        predicted_value = class_names[predicted_class_idx]
        
        # Create probability dictionary
        prob_dict = {
            "home": probabilities[2] if len(probabilities) > 2 else probabilities[0],
            "away": probabilities[0] if len(probabilities) > 2 else probabilities[1],
            "draw": probabilities[1] if len(probabilities) > 2 else 0.0
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return PredictionOutput(
            prediction_type=prediction_type,
            model_type=self.model_type,
            predicted_value=predicted_value,
            confidence=float(np.max(probabilities)),
            probabilities=prob_dict,
            model_version=self.model_version,
            features_used=self._feature_names or [],
            processing_time_ms=processing_time,
            metadata={
                "feature_importance": self._get_feature_importance(),
                "model_params": self._get_model_params()
            }
        )
    
    async def _load_model(self) -> None:
        """Load the trained model from disk."""
        try:
            if self.model_path.exists():
                model_data = joblib.load(self.model_path)
                
                if isinstance(model_data, dict):
                    # Structured model file
                    self._pipeline = model_data.get("pipeline")
                    self._feature_names = model_data.get("feature_names", [])
                    self._version = model_data.get("version", "1.0.0")
                else:
                    # Legacy model file (just the pipeline)
                    self._pipeline = model_data
                    self._feature_names = self._infer_feature_names()
                
                self._is_loaded = True
            else:
                # Create a default model for development
                self._create_default_model()
                self._is_loaded = True
                
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def _create_default_model(self) -> None:
        """Create a default model for development/testing."""
        # Create a simple pipeline with standard scaler and logistic regression
        self._pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(
                random_state=42,
                class_weight='balanced',
                max_iter=1000
            ))
        ])
        
        # Define feature names for development
        self._feature_names = [
            'elo_difference',
            'home_advantage',
            'home_form_streak',
            'away_form_streak',
            'home_avg_points',
            'away_avg_points',
            'head_to_head_ratio'
        ]
        
        # Create dummy training data and fit the model
        # In production, this would be replaced with actual training
        X_dummy = np.random.randn(100, len(self._feature_names))
        y_dummy = np.random.choice([0, 1, 2], 100)  # 0=away, 1=draw, 2=home
        
        self._pipeline.fit(X_dummy, y_dummy)
    
    def _extract_feature_vector(self, features: PredictionFeatures) -> List[float]:
        """Extract feature vector from PredictionFeatures object."""
        # Calculate ELO difference
        elo_diff = features.home_team_stats.elo_rating - features.away_team_stats.elo_rating
        
        # Calculate form streaks (simplified)
        home_form = self._calculate_form_score(features.home_team_stats.recent_form)
        away_form = self._calculate_form_score(features.away_team_stats.recent_form)
        
        # Head to head ratio
        h2h_total = sum(features.head_to_head_record.values())
        h2h_ratio = features.head_to_head_record.get("home_wins", 0) / max(h2h_total, 1)
        
        return [
            elo_diff,
            features.home_advantage,
            home_form,
            away_form,
            features.home_team_stats.avg_points_scored,
            features.away_team_stats.avg_points_scored,
            h2h_ratio
        ]
    
    def _calculate_form_score(self, recent_form: List[str]) -> float:
        """Calculate a form score from recent results."""
        if not recent_form:
            return 0.0
        
        score = 0
        for i, result in enumerate(recent_form[-5:]):  # Last 5 games
            weight = (i + 1) / 5  # More recent games have higher weight
            if result == "W":
                score += 1 * weight
            elif result == "D":
                score += 0.5 * weight
            # Loss adds 0
        
        return score / len(recent_form[-5:])
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if self._pipeline and hasattr(self._pipeline.named_steps['classifier'], 'coef_'):
            coef = self._pipeline.named_steps['classifier'].coef_[0]
            if self._feature_names and len(coef) == len(self._feature_names):
                return {
                    name: float(abs(importance)) 
                    for name, importance in zip(self._feature_names, coef)
                }
        return {}
    
    def _get_model_params(self) -> Dict[str, Any]:
        """Get model parameters."""
        if self._pipeline and hasattr(self._pipeline.named_steps['classifier'], 'get_params'):
            return self._pipeline.named_steps['classifier'].get_params()
        return {}
    
    def _infer_feature_names(self) -> List[str]:
        """Infer feature names for legacy models."""
        # Default feature names for backwards compatibility
        return [
            'elo_difference',
            'home_advantage', 
            'home_form_streak',
            'away_form_streak',
            'home_avg_points',
            'away_avg_points',
            'head_to_head_ratio'
        ]