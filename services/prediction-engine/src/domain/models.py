"""Domain models for prediction engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from shared.data_contracts.prediction import PredictionType, ModelType


@dataclass
class Match:
    """Match domain model."""
    
    match_id: str
    team_home: str
    team_away: str
    match_date: datetime
    venue: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    season: Optional[int] = None
    round_number: Optional[int] = None


@dataclass
class TeamStats:
    """Team statistics domain model."""
    
    team_name: str
    elo_rating: float
    recent_form: List[str]  # W, L, D for recent matches
    avg_points_scored: float
    avg_points_conceded: float
    home_win_rate: Optional[float] = None
    away_win_rate: Optional[float] = None
    injury_count: Optional[int] = None


@dataclass
class PredictionFeatures:
    """Features used for making predictions."""
    
    home_team_stats: TeamStats
    away_team_stats: TeamStats
    elo_difference: float
    home_advantage: float
    head_to_head_record: Dict[str, int]
    recent_encounters: List[Match]
    bookmaker_odds: Optional[Dict[str, float]] = None
    additional_features: Optional[Dict[str, Any]] = None


@dataclass
class PredictionOutput:
    """Output from a prediction model."""
    
    prediction_type: PredictionType
    model_type: ModelType
    predicted_value: Any
    confidence: float
    probabilities: Dict[str, float]
    model_version: str
    features_used: List[str]
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]] = None


class PredictionModel(ABC):
    """Abstract base class for prediction models."""
    
    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """Return the model type."""
        pass
    
    @property
    @abstractmethod
    def supported_prediction_types(self) -> List[PredictionType]:
        """Return the prediction types this model supports."""
        pass
    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version."""
        pass
    
    @abstractmethod
    async def predict(
        self, 
        features: PredictionFeatures, 
        prediction_type: PredictionType
    ) -> PredictionOutput:
        """Make a prediction based on features."""
        pass
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if the model is ready to make predictions."""
        pass


class FeatureEngineer(ABC):
    """Abstract base class for feature engineering."""
    
    @abstractmethod
    async def extract_features(
        self, 
        match: Match, 
        historical_data: List[Match]
    ) -> PredictionFeatures:
        """Extract features for prediction."""
        pass


class ModelRepository(ABC):
    """Abstract repository for model management."""
    
    @abstractmethod
    async def load_model(self, model_type: ModelType) -> PredictionModel:
        """Load a trained model."""
        pass
    
    @abstractmethod
    async def save_prediction(
        self, 
        match: Match, 
        prediction: PredictionOutput,
        user_id: Optional[str] = None
    ) -> str:
        """Save a prediction and return prediction ID."""
        pass
    
    @abstractmethod
    async def get_model_performance(
        self, 
        model_type: ModelType,
        prediction_type: PredictionType,
        days: int = 30
    ) -> Dict[str, float]:
        """Get model performance metrics."""
        pass


class DataRepository(ABC):
    """Abstract repository for data access."""
    
    @abstractmethod
    async def get_historical_matches(
        self, 
        team_home: str, 
        team_away: str,
        limit: Optional[int] = None
    ) -> List[Match]:
        """Get historical matches between teams."""
        pass
    
    @abstractmethod
    async def get_team_stats(self, team_name: str) -> TeamStats:
        """Get current team statistics."""
        pass
    
    @abstractmethod
    async def get_recent_matches(
        self, 
        team_name: str, 
        count: int = 10
    ) -> List[Match]:
        """Get recent matches for a team."""
        pass