"""Prediction data contracts and schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class PredictionType(str, Enum):
    """Types of predictions available."""
    MATCH_WINNER = "match_winner"
    MARGIN = "margin"
    FIRST_TRY_SCORER = "first_try_scorer"
    POINT_SCORER = "point_scorer"
    UPSET_DETECTION = "upset_detection"


class ModelType(str, Enum):
    """Available prediction models."""
    LOGISTIC_REGRESSION = "logistic_regression"
    LIGHTGBM = "lightgbm"
    TRANSFORMER = "transformer"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    STACKER = "stacker"
    ENSEMBLE = "ensemble"


class PredictionRequest(BaseModel):
    """Request for predictions."""
    
    team_home: str = Field(..., description="Home team name")
    team_away: str = Field(..., description="Away team name")
    match_date: datetime = Field(..., description="Match date and time")
    venue: Optional[str] = Field(None, description="Match venue")
    prediction_types: List[PredictionType] = Field(
        default=[PredictionType.MATCH_WINNER],
        description="Types of predictions requested"
    )
    models: Optional[List[ModelType]] = Field(
        None,
        description="Specific models to use (if not provided, ensemble will decide)"
    )
    include_confidence: bool = Field(
        True,
        description="Include confidence scores in response"
    )
    include_explanation: bool = Field(
        False,
        description="Include model explanations (premium feature)"
    )
    
    @validator('team_home', 'team_away')
    def validate_team_names(cls, v):
        """Validate team names are not empty."""
        if not v or not v.strip():
            raise ValueError("Team names cannot be empty")
        return v.strip()
    
    @validator('prediction_types')
    def validate_prediction_types(cls, v):
        """Ensure at least one prediction type is requested."""
        if not v:
            raise ValueError("At least one prediction type must be requested")
        return v


class PredictionResult(BaseModel):
    """Individual prediction result."""
    
    prediction_type: PredictionType
    model_used: ModelType
    predicted_value: Any = Field(..., description="Predicted value (varies by type)")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    probability_home: Optional[float] = Field(None, ge=0, le=1)
    probability_away: Optional[float] = Field(None, ge=0, le=1)
    probability_draw: Optional[float] = Field(None, ge=0, le=1)
    explanation: Optional[Dict[str, Any]] = Field(None, description="Model explanation")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PredictionResponse(BaseModel):
    """Response containing predictions."""
    
    prediction_id: str = Field(..., description="Unique prediction identifier")
    request: PredictionRequest
    predictions: List[PredictionResult]
    ensemble_prediction: Optional[PredictionResult] = Field(
        None,
        description="Combined ensemble prediction"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Version information for models used"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HistoricalPrediction(BaseModel):
    """Historical prediction for backtesting and analysis."""
    
    prediction_id: str
    match_id: str
    team_home: str
    team_away: str
    match_date: datetime
    prediction_type: PredictionType
    model_used: ModelType
    predicted_value: Any
    confidence: Optional[float]
    actual_value: Optional[Any] = Field(None, description="Actual outcome")
    accuracy: Optional[float] = Field(None, description="Prediction accuracy")
    created_at: datetime
    user_id: Optional[str] = None


class ModelPerformance(BaseModel):
    """Model performance metrics."""
    
    model_type: ModelType
    prediction_type: PredictionType
    accuracy: float = Field(..., ge=0, le=1)
    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    f1_score: Optional[float] = Field(None, ge=0, le=1)
    calibration_score: Optional[float] = Field(None, ge=0, le=1)
    total_predictions: int = Field(..., ge=0)
    evaluation_period: str
    last_updated: datetime


class TeamFeatures(BaseModel):
    """Team features for prediction models."""
    
    team_name: str
    elo_rating: float
    recent_form: List[str] = Field(..., description="Recent match results")
    injury_count: Optional[int] = Field(None, ge=0)
    home_advantage: Optional[float] = None
    head_to_head_record: Optional[Dict[str, int]] = None
    avg_points_scored: Optional[float] = None
    avg_points_conceded: Optional[float] = None
    features_updated: datetime