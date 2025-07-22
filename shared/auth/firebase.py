"""Firebase authentication utilities."""

import os
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


class User(BaseModel):
    """Authenticated user model."""
    
    uid: str
    email: Optional[str] = None
    email_verified: bool = False
    tier: str = "anonymous"  # anonymous, registered, premium


class FirebaseAuth:
    """Firebase authentication handler."""
    
    def __init__(self, service_account_path: Optional[str] = None):
        """Initialise Firebase authentication."""
        if not firebase_admin._apps:
            if service_account_path:
                cred = credentials.Certificate(service_account_path)
            else:
                # Use default credentials for production
                cred = credentials.ApplicationDefault()
            
            firebase_admin.initialize_app(cred)
    
    async def verify_token(self, token: str) -> User:
        """Verify Firebase ID token and return user."""
        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token["uid"]
            email = decoded_token.get("email")
            email_verified = decoded_token.get("email_verified", False)
            
            # Determine user tier based on custom claims or subscription status
            tier = self._determine_user_tier(decoded_token)
            
            return User(
                uid=uid,
                email=email,
                email_verified=email_verified,
                tier=tier
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}"
            ) from e
    
    def _determine_user_tier(self, decoded_token: dict) -> str:
        """Determine user tier from token claims."""
        custom_claims = decoded_token.get("custom_claims", {})
        subscription_status = custom_claims.get("subscription_status")
        
        if subscription_status == "premium":
            return "premium"
        elif decoded_token.get("email_verified"):
            return "registered"
        else:
            return "anonymous"


# Global Firebase auth instance
firebase_auth = FirebaseAuth(
    service_account_path=os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
)

# FastAPI security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = security
) -> User:
    """FastAPI dependency to get current authenticated user."""
    return await firebase_auth.verify_token(credentials.credentials)


async def require_tier(required_tier: str):
    """Create a dependency that requires a specific user tier."""
    async def check_tier(user: User = get_current_user) -> User:
        tier_hierarchy = {"anonymous": 0, "registered": 1, "premium": 2}
        
        user_level = tier_hierarchy.get(user.tier, 0)
        required_level = tier_hierarchy.get(required_tier, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access requires {required_tier} tier or higher"
            )
        
        return user
    
    return check_tier