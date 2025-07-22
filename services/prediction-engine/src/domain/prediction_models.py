"""Domain models for prediction engine.

This module defines the abstract interfaces that all prediction models must implement,
ensuring consistent behavior across LR, LightGBM, Transformer, Stacker, and RL models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import uuid


class PredictionType(str, Enum):
    """Types of predictions available."""
    MATCH_WINNER = "match_winner"
    MATCH_MARGIN = "match_margin"
    FIRST_TRY_SCORER = "first_try_scorer"
    TOTAL_POINTS = "total_points"


class ModelType(str, Enum):
    """Available prediction models."""
    LOGISTIC_REGRESSION = "logistic_regression"
    LIGHTGBM = "lightgbm"
    TRANSFORMER = "transformer"
    STACKER = "stacker"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    MOE_ENSEMBLE = "moe_ensemble"


class Winner(str, Enum):
    """Match winner outcomes."""
    HOME = "home"
    AWAY = "away"
    DRAW = "draw"


@dataclass
class MatchDetails:
    """Input match details for prediction."""
    
    team_home: str
    team_away: str
    match_date: datetime
    venue: Optional[str] = None
    round_num: Optional[int] = None
    season_year: Optional[int] = None
    odds_home: Optional[float] = None
    odds_away: Optional[float] = None
    odds_draw: Optional[float] = None
    
    @property
    def match_id(self) -> str:
        """Generate a unique match identifier."""
        date_str = self.match_date.strftime('%Y-%m-%d')
        return f"predict_{self.team_home}_{self.team_away}_{date_str}"


@dataclass
class PredictionFeatures:
    """Engineered features for prediction."""
    
    match_details: MatchDetails
    features: Dict[str, Any]
    feature_names: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary."""
        return self.features


@dataclass
class PredictionResult:
    """Result of a prediction."""
    
    prediction_id: str
    model_type: ModelType
    prediction_type: PredictionType
    match_details: MatchDetails
    predicted_winner: Winner
    probabilities: Dict[str, float]  # e.g., {"home": 0.6, "away": 0.35, "draw": 0.05}
    confidence: float
    predicted_margin: Optional[float] = None
    predicted_total_points: Optional[float] = None
    features_used: Optional[List[str]] = None
    model_metadata: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[float] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set defaults after initialization."""
        if not self.prediction_id:
            self.prediction_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    
    model_type: ModelType
    accuracy: float
    precision: Dict[str, float]
    recall: Dict[str, float]
    f1_score: Dict[str, float]
    auc_score: Optional[float] = None
    log_loss: Optional[float] = None
    brier_score: Optional[float] = None
    calibration_score: Optional[float] = None
    last_updated: Optional[datetime] = None


class PredictionModel(ABC):
    """Abstract base class for all prediction models."""
    
    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """Return the model type."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the human-readable model name."""
        pass
    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version."""
        pass
    
    @property
    @abstractmethod
    def supported_prediction_types(self) -> List[PredictionType]:
        """Return list of prediction types this model supports."""
        pass
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if model is loaded and ready for predictions."""
        pass
    
    @abstractmethod
    async def predict(
        self, 
        match_details: MatchDetails,
        prediction_type: PredictionType = PredictionType.MATCH_WINNER
    ) -> PredictionResult:
        """Make a prediction for the given match."""
        pass
    
    @abstractmethod
    async def predict_batch(
        self, 
        matches: List[MatchDetails],
        prediction_type: PredictionType = PredictionType.MATCH_WINNER
    ) -> List[PredictionResult]:
        """Make predictions for multiple matches."""
        pass
    
    @abstractmethod
    async def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        pass
    
    @abstractmethod
    async def get_model_metrics(self) -> ModelMetrics:
        """Get model performance metrics."""
        pass


class FeatureEngineer(ABC):
    """Abstract base class for feature engineering."""
    
    @abstractmethod
    async def engineer_features(
        self, 
        match_details: MatchDetails,
        historical_data: Any
    ) -> PredictionFeatures:
        """Engineer features for the given match."""
        pass


class ModelRepository(ABC):
    """Abstract repository for model persistence."""
    
    @abstractmethod
    async def save_prediction(self, prediction: PredictionResult) -> str:
        """Save prediction and return prediction ID."""
        pass
    
    @abstractmethod
    async def get_prediction(self, prediction_id: str) -> Optional[PredictionResult]:
        """Get prediction by ID."""
        pass
    
    @abstractmethod
    async def get_predictions_for_user(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[PredictionResult]:
        """Get predictions for a user."""
        pass
    
    @abstractmethod
    async def get_model_performance(
        self, 
        model_type: ModelType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ModelMetrics:
        """Get model performance metrics."""
        pass


class DataLoader(ABC):
    """Abstract data loader for historical match data."""
    
    @abstractmethod
    async def load_historical_matches(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        teams: Optional[List[str]] = None
    ) -> Any:
        """Load historical match data."""
        pass
    
    @abstractmethod
    async def load_team_features(self, team_name: str) -> Dict[str, Any]:
        """Load team-specific features."""
        pass
    
    @abstractmethod
    async def load_player_features(self, team_name: str) -> Dict[str, Any]:
        """Load player features for a team."""
        pass