"""Domain models for user management."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod


class UserTier(str, Enum):
    """User subscription tiers."""
    ANONYMOUS = "anonymous"
    REGISTERED = "registered"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DEACTIVATED = "deactivated"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    SUSPENDED = "suspended"


@dataclass
class User:
    """User domain model."""
    
    user_id: str
    email: str
    tier: UserTier
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    email_verified: bool = False
    display_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    firebase_uid: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def has_premium_access(self) -> bool:
        """Check if user has premium access."""
        return self.tier in [UserTier.PREMIUM, UserTier.ENTERPRISE]
    
    @property
    def rate_limit_per_hour(self) -> int:
        """Get rate limit based on tier."""
        limits = {
            UserTier.ANONYMOUS: 10,
            UserTier.REGISTERED: 100,
            UserTier.PREMIUM: 1000,
            UserTier.ENTERPRISE: 10000
        }
        return limits.get(self.tier, 10)


@dataclass
class Subscription:
    """Subscription domain model."""
    
    subscription_id: str
    user_id: str
    tier: UserTier
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    stripe_subscription_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        if self.end_date and datetime.utcnow() > self.end_date:
            return False
        
        return True
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Get days remaining in subscription."""
        if not self.end_date:
            return None
        
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)


@dataclass
class UserActivity:
    """User activity tracking."""
    
    activity_id: str
    user_id: str
    activity_type: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateUserRequest:
    """Request to create a new user."""
    
    email: str
    firebase_uid: str
    display_name: Optional[str] = None
    tier: UserTier = UserTier.REGISTERED


@dataclass
class UpdateUserRequest:
    """Request to update user."""
    
    display_name: Optional[str] = None
    tier: Optional[UserTier] = None
    status: Optional[UserStatus] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateSubscriptionRequest:
    """Request to create subscription."""
    
    user_id: str
    tier: UserTier
    end_date: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None


# Repository interfaces
class UserRepository(ABC):
    """User repository interface."""
    
    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass
    
    @abstractmethod
    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID."""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, updates: UpdateUserRequest) -> Optional[User]:
        """Update user."""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        pass
    
    @abstractmethod
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """List users."""
        pass


class SubscriptionRepository(ABC):
    """Subscription repository interface."""
    
    @abstractmethod
    async def create_subscription(self, subscription: Subscription) -> Subscription:
        """Create subscription."""
        pass
    
    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        pass
    
    @abstractmethod
    async def get_user_subscriptions(self, user_id: str) -> List[Subscription]:
        """Get user subscriptions."""
        pass
    
    @abstractmethod
    async def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription."""
        pass
    
    @abstractmethod
    async def update_subscription(self, subscription_id: str, **updates) -> Optional[Subscription]:
        """Update subscription."""
        pass
    
    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel subscription."""
        pass


class ActivityRepository(ABC):
    """Activity repository interface."""
    
    @abstractmethod
    async def log_activity(self, activity: UserActivity) -> UserActivity:
        """Log user activity."""
        pass
    
    @abstractmethod
    async def get_user_activities(
        self, 
        user_id: str, 
        limit: int = 100,
        activity_type: Optional[str] = None
    ) -> List[UserActivity]:
        """Get user activities."""
        pass