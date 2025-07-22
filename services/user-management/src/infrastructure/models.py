# user_service/models.py
from pydantic import BaseModel, EmailStr, Field # Added Field import
from datetime import datetime
from typing import Optional
from enum import Enum

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    firebase_uid: str

class SubscriptionTier(str, Enum):
    BASIC = "basic"
    DEEP_DIVE = "deep_dive"
    STACKED = "stacked"
    EDGE_FINDER = "edge_finder"
    CUSTOM = "custom"

class User(UserBase):
    id: int
    firebase_uid: str
    created_at: datetime
    subscription_tier: Optional[SubscriptionTier] = None
    subscription_status: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None

    class Config:
        from_attributes = True # Compatibility with SQLAlchemy-style ORM objects

# Model for the decoded Firebase token payload (subset of fields)
class FirebaseUser(BaseModel):
    uid: str
    email: Optional[EmailStr] = None
    # Add other fields you might need from the token, e.g., name, picture

# Model for the response of the internal /users/lookup endpoint
class UserIdLookup(BaseModel):
    user_id: int

# Model for representing a single prediction retrieved for a user
class UserPrediction(BaseModel):
    model: str # e.g., "LR", "LGBM", "Transformer", "RL"
    prediction_id: int # The original prediction ID from its source DB
    match_id: Optional[str] = None
    match_date: Optional[str] = None
    home_team_name: str
    away_team_name: str
    predicted_winner: Optional[str] = None
    prob_home_win: Optional[float] = None
    prob_draw: Optional[float] = None
    prob_away_win: Optional[float] = None
    # Add other common/important fields if needed, e.g., RL specific outputs
    rl_predicted_winner: Optional[str] = None
    rl_winner_confidence: Optional[float] = None
    prediction_timestamp: datetime

    class Config:
        from_attributes = True # Allow creation from ORM objects (like sqlite3.Row)


# --- Feedback Models ---

class FeedbackRatingPayload(BaseModel):
    prediction_id: str
    rating: int = Field(..., ge=1, le=5) # Rating must be between 1 and 5

class FeedbackResultPayload(BaseModel):
    prediction_id: str
    actual_winner: str
    actual_margin: int = Field(..., ge=0) # Margin must be non-negative
