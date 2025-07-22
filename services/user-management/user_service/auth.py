# user_service/auth.py
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import os

from .config import FIREBASE_SERVICE_ACCOUNT_KEY_PATH
from .models import FirebaseUser

logger = logging.getLogger(__name__)

# --- Firebase Admin Initialization ---
try:
    # Check if the key file exists before attempting to initialize
    if not os.path.exists(FIREBASE_SERVICE_ACCOUNT_KEY_PATH):
        logger.error(f"Firebase service account key not found at: {FIREBASE_SERVICE_ACCOUNT_KEY_PATH}")
        # Depending on deployment strategy, you might want to raise an error or exit
        # For now, we'll log the error and let subsequent operations fail if Firebase is needed.
        firebase_app = None
    else:
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")

except ValueError as e:
    logger.error(f"Error initializing Firebase Admin SDK: {e}")
    logger.error("Ensure the service account key file is valid JSON.")
    firebase_app = None
except Exception as e:
    logger.error(f"An unexpected error occurred during Firebase Admin SDK initialization: {e}")
    firebase_app = None


# --- Authentication Dependency ---
security = HTTPBearer()

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security)
) -> FirebaseUser:
    """
    Dependency function to verify Firebase ID token and return user info.
    To be used in protected endpoints.
    """
    if firebase_app is None:
        logger.error("Firebase Admin SDK not initialized. Cannot verify token.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication service is not available.",
        )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    try:
        # Verify the ID token while checking if the token is revoked.
        decoded_token = auth.verify_id_token(token.credentials, check_revoked=True)
        # Extract necessary user information
        user = FirebaseUser(
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email")
            # Add other fields as needed from decoded_token
        )
        return user
    except auth.RevokedIdTokenError:
        logger.warning(f"Authentication failed: Revoked ID token for UID {decoded_token.get('uid', 'N/A')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        logger.warning(f"Authentication failed: Expired ID token for UID {decoded_token.get('uid', 'N/A')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError as e:
        logger.error(f"Authentication failed: Invalid ID token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e: # Catch other potential errors during verification
        logger.error(f"An unexpected error occurred during token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
