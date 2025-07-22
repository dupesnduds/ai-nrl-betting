# user_service/api.py
import sqlite3
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any

from . import storage, models, auth
from .models import FeedbackRatingPayload, FeedbackResultPayload, User
from .storage import save_prediction_rating, save_actual_result, update_user_subscription
from .auth import get_current_user
from .permissions import get_allowed_modes

app = FastAPI(title="User Service API")

# --- CORS Middleware Configuration ---
origins = [
    "http://localhost:3001", # React frontend origin (adjust port if necessary)
    # Add other origins if needed, e.g., deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allow cookies/auth headers
    allow_methods=["*"],    # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allow all headers (including Authorization)
)
# --- End CORS Configuration ---

@app.get("/")
async def read_root():
    """ Basic endpoint to check if the service is running. """
    return {"message": "User Service is running"}


@app.get("/users/me", response_model=models.User)
async def read_users_me(current_firebase_user: models.FirebaseUser = Depends(auth.get_current_user)):
    """
    Gets the current authenticated user's details from the local database.
    If the user doesn't exist locally, it creates them based on the Firebase token.
    """
    # Check if user exists in our DB
    db_user = storage.get_user_by_firebase_uid(current_firebase_user.uid)

    if db_user:
        return db_user
    else:
        # User exists in Firebase but not in our DB, create them
        if not current_firebase_user.email:
            # This case should be rare with Google Sign-In, but handle it.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email not found in Firebase token. Cannot create local user record.",
            )

        user_in = models.UserCreate(
            firebase_uid=current_firebase_user.uid,
            email=current_firebase_user.email
        )
        try:
            new_db_user = storage.create_user(user_in)
            return new_db_user
        except Exception as e:
            # Log the exception e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not create user record in local database: {e}",
            )


@app.get("/users/lookup", response_model=models.UserIdLookup)
async def lookup_user_id(firebase_uid: str):
    """
    Internal endpoint to look up the internal user ID based on Firebase UID.
    Used by predictor services to associate predictions with users.
    """
    db_user = storage.get_user_by_firebase_uid(firebase_uid)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with Firebase UID {firebase_uid} not found in local database.",
        )
    # Ensure the returned value matches the Pydantic model structure
    return models.UserIdLookup(user_id=db_user.id)


@app.get("/users/lookup_by_token", response_model=models.UserIdLookup)
async def lookup_user_id_by_token(current_firebase_user: models.FirebaseUser = Depends(auth.get_current_user)):
    """
    Internal endpoint to look up the internal user ID based on a verified Firebase token.
    Used by predictor services to associate predictions with users without needing direct DB access.
    Relies on the get_current_user dependency to handle token verification.
    """
    # The dependency auth.get_current_user already verifies the token and gets FirebaseUser
    # Now, find the corresponding user in our local DB
    db_user = storage.get_user_by_firebase_uid(current_firebase_user.uid)
    if not db_user:
        # This case implies a valid Firebase token but no corresponding local user.
        # This might happen if /users/me hasn't been called yet for this user.
        # Option 1: Raise 404 (simplest)
        # Option 2: Create the user here (similar to /users/me) - might be better UX
        # Let's go with Option 1 for now for simplicity, assuming /users/me is called first.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with Firebase UID {current_firebase_user.uid} not found in local database. Ensure /users/me was called first.",
        )
    return models.UserIdLookup(user_id=db_user.id)


@app.get("/users/me/modes", response_model=List[str])
async def get_user_modes(current_firebase_user: models.FirebaseUser = Depends(auth.get_current_user)):
    """
    Returns the list of allowed modes for the current user.
    """
    db_user = storage.get_user_by_firebase_uid(current_firebase_user.uid)
    if not db_user:
        # Treat as anonymous user
        return get_allowed_modes(None)
    return get_allowed_modes(db_user)


# Define paths to the prediction databases relative to the project root
# Assuming the user-service runs from the SPORTS_BETS root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')) # Adjust if needed

MODEL_PREDICTION_DBS: Dict[str, Dict[str, str]] = {
    "LR": {
        "path": os.path.join(PROJECT_ROOT, "logistic-regression-predictor", "data", "lr_predictions.db"),
        "table": "predictions"
    },
    "LGBM": {
        "path": os.path.join(PROJECT_ROOT, "nrl_predictions.db"), # Shared DB
        "table": "predictions"
    },
    "Stacker": {
        "path": os.path.join(PROJECT_ROOT, "nrl_predictions.db"), # Shared DB
        "table": "predictions"
    },
    "Transformer": {
        "path": os.path.join(PROJECT_ROOT, "transformer-predictor", "data", "t_predictions.db"),
        "table": "t_predictions"
    },
    "RL": {
        "path": os.path.join(PROJECT_ROOT, "nrl_predictions.db"), # Shared DB
        "table": "predictions"
    },
}

@app.get("/users/me/predictions", response_model=List[models.UserPrediction])
async def read_user_predictions(firebase_user: models.FirebaseUser = Depends(auth.get_current_user)):
    """
    Retrieves all predictions associated with the currently authenticated user
    from all relevant prediction databases.
    """
    # First, get the internal user object from the database using the Firebase UID
    db_user = storage.get_user_by_firebase_uid(firebase_user.uid)
    if not db_user:
        # This should ideally not happen if the frontend ensures /users/me is called after login,
        # but handle it defensively.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with Firebase UID {firebase_user.uid} not found in local database. Please ensure the user profile exists.",
        )

    print(f"--- [User Predictions] Endpoint called for user_id: {db_user.id} ---") # LOGGING
    user_id = db_user.id # Use the internal ID from the fetched user object
    all_predictions: List[models.UserPrediction] = []
    processed_prediction_ids: Dict[str, set] = {model: set() for model in MODEL_PREDICTION_DBS} # Track IDs per model

    print(f"--- [User Predictions] Starting database loop ---") # LOGGING
    for model_name, db_info in MODEL_PREDICTION_DBS.items():
        db_path = db_info["path"]
        table_name = db_info["table"]
        conn = None
        if not os.path.exists(db_path):
            # Log this? Or just skip? For now, skip silently.
            continue

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row # Important for accessing columns by name
            cursor = conn.cursor()

            # Construct query safely
            # Ensure user_id column exists before querying? For now, assume it does.
            sql = f"SELECT * FROM {table_name} WHERE user_id = ?"
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

            for row in rows:
                row_dict = dict(row)
                prediction_id = row_dict.get('prediction_id')

                # Avoid duplicates if multiple models write to the same DB row (unlikely with current setup but safe)
                if prediction_id is not None and prediction_id in processed_prediction_ids[model_name]:
                    continue

                try:
                    # Map row data to UserPrediction model
                    # Handle potential missing keys gracefully using .get()
                    prediction_data = {
                        "model": model_name,
                        "prediction_id": prediction_id,
                        "match_id": row_dict.get('match_id') or row_dict.get('match_identifier'), # Handle different column names
                        "match_date": row_dict.get('match_date'),
                        "home_team_name": row_dict.get('home_team_name'),
                        "away_team_name": row_dict.get('away_team_name'),
                        "predicted_winner": row_dict.get('predicted_winner') or row_dict.get('rl_predicted_winner'), # Check RL specific field
                        "prob_home_win": row_dict.get('prob_home_win'),
                        "prob_draw": row_dict.get('prob_draw'),
                        "prob_away_win": row_dict.get('prob_away_win'),
                        "rl_predicted_winner": row_dict.get('rl_predicted_winner'), # Include RL specific fields
                        "rl_winner_confidence": row_dict.get('rl_winner_confidence'),
                        "prediction_timestamp": row_dict.get('prediction_timestamp')
                    }
                    # Filter out None values before validation if needed, or handle in model
                    # Validate and create the Pydantic model instance
                    user_pred = models.UserPrediction(**prediction_data)
                    all_predictions.append(user_pred)
                    if prediction_id is not None:
                         processed_prediction_ids[model_name].add(prediction_id)

                except Exception as e: # Catch validation errors or other issues
                    # Log the error and the problematic row data
                    print(f"Error processing prediction row for model {model_name}, ID {prediction_id}: {e}. Row: {row_dict}")
                    continue # Skip this row

        except sqlite3.Error as e:
            # Log the database connection or query error
            print(f"Database error for model {model_name} at {db_path}: {e}")
            continue # Skip this database if error occurs
        finally:
            if conn:
                conn.close()

    print(f"--- [User Predictions] Finished database loop. Found {len(all_predictions)} raw predictions. ---") # LOGGING

    # Sort predictions by timestamp, newest first
    print(f"--- [User Predictions] Sorting {len(all_predictions)} predictions... ---") # LOGGING
    try:
        all_predictions.sort(key=lambda p: p.prediction_timestamp, reverse=True)
        print(f"--- [User Predictions] Sorting complete. ---") # LOGGING
    except TypeError as e:
        print(f"--- [User Predictions] ERROR during sorting: {e} ---") # LOGGING
        # Optionally re-raise or handle differently, but logging is key
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sorting predictions: {e}"
        )

    print(f"--- [User Predictions] Returning {len(all_predictions)} predictions. ---") # LOGGING
    return all_predictions


# --- Subscription Management ---

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SubscriptionUpdateRequest(BaseModel):
    firebase_uid: str
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None

@app.post("/users/update_subscription", response_model=User)
async def update_subscription(payload: SubscriptionUpdateRequest):
    """
    Updates a user's subscription details.
    """
    updated_user = update_user_subscription(
        firebase_uid=payload.firebase_uid,
        subscription_tier=payload.subscription_tier,
        subscription_status=payload.subscription_status,
        subscription_start_date=payload.subscription_start_date,
        subscription_end_date=payload.subscription_end_date
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with Firebase UID {payload.firebase_uid} not found.",
        )
    return updated_user

# --- Feedback Endpoints ---

@app.post("/users/feedback/rating", status_code=status.HTTP_201_CREATED)
async def submit_prediction_rating(
    payload: FeedbackRatingPayload,
    current_user: User = Depends(get_current_user)
):
    """Submits a user's star rating for a specific prediction."""
    try:
        save_prediction_rating(
            user_id=current_user.id,
            prediction_id=payload.prediction_id,
            rating=payload.rating
        )
        return {"message": "Rating submitted successfully"}
    except sqlite3.Error as e:
        # Log the error e
        print(f"Database error submitting rating for user {current_user.id}, prediction {payload.prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save rating due to a database error.",
        )
    except Exception as e:
        # Log the error e
        print(f"Unexpected error submitting rating for user {current_user.id}, prediction {payload.prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the rating.",
        )


@app.post("/users/feedback/result", status_code=status.HTTP_201_CREATED)
async def submit_actual_result(
    payload: FeedbackResultPayload,
    current_user: User = Depends(get_current_user)
):
    """Submits the actual outcome of a match corresponding to a prediction."""
    try:
        save_actual_result(
            user_id=current_user.id,
            prediction_id=payload.prediction_id,
            actual_winner=payload.actual_winner,
            actual_margin=payload.actual_margin
        )
        return {"message": "Actual result submitted successfully"}
    except sqlite3.Error as e:
        # Log the error e
        print(f"Database error submitting result for user {current_user.id}, prediction {payload.prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save actual result due to a database error.",
        )
    except Exception as e:
        # Log the error e
        print(f"Unexpected error submitting result for user {current_user.id}, prediction {payload.prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the actual result.",
        )
