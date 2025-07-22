"""User management application service."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import structlog

from ..domain.models import (
    User, Subscription, UserActivity, UserTier, UserStatus, SubscriptionStatus,
    CreateUserRequest, UpdateUserRequest, CreateSubscriptionRequest,
    UserRepository, SubscriptionRepository, ActivityRepository
)
from ....shared.events.event_bus import (
    EventBus, UserRegisteredEvent, EventType
)

logger = structlog.get_logger(__name__)


class UserService:
    """User management service."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
        activity_repository: ActivityRepository,
        event_bus: Optional[EventBus] = None
    ):
        """Initialise user service."""
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.activity_repository = activity_repository
        self.event_bus = event_bus
    
    async def create_user(self, request: CreateUserRequest) -> User:
        """Create a new user."""
        logger.info("Creating new user", email=request.email)
        
        # Check if user already exists
        existing_user = await self.user_repository.get_user_by_email(request.email)
        if existing_user:
            raise ValueError(f"User with email {request.email} already exists")
        
        existing_firebase_user = await self.user_repository.get_user_by_firebase_uid(request.firebase_uid)
        if existing_firebase_user:
            raise ValueError(f"User with Firebase UID {request.firebase_uid} already exists")
        
        # Create user
        now = datetime.utcnow()
        user = User(
            user_id=str(uuid.uuid4()),
            email=request.email,
            firebase_uid=request.firebase_uid,
            display_name=request.display_name,
            tier=request.tier,
            status=UserStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            email_verified=False,
            metadata={}
        )
        
        # Save user
        created_user = await self.user_repository.create_user(user)
        
        # Log activity
        await self._log_activity(
            user_id=created_user.user_id,
            activity_type="user_registered",
            metadata={"tier": request.tier.value}
        )
        
        # Publish event
        if self.event_bus:
            try:
                event = UserRegisteredEvent(
                    event_id="",
                    event_type=EventType.USER_REGISTERED,
                    timestamp=None,
                    correlation_id=created_user.user_id,
                    source_service="user-management",
                    user_id=created_user.user_id,
                    email=created_user.email,
                    tier=created_user.tier.value,
                    registration_source="api"
                )
                await self.event_bus.publish(event)
            except Exception as e:
                logger.warning("Failed to publish user registered event", error=str(e))
        
        logger.info("User created successfully", user_id=created_user.user_id)
        return created_user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repository.get_user(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repository.get_user_by_email(email)
    
    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Get user by Firebase UID."""
        return await self.user_repository.get_user_by_firebase_uid(firebase_uid)
    
    async def update_user(self, user_id: str, request: UpdateUserRequest) -> Optional[User]:
        """Update user."""
        logger.info("Updating user", user_id=user_id)
        
        # Get existing user
        user = await self.user_repository.get_user(user_id)
        if not user:
            return None
        
        # Update user
        updated_user = await self.user_repository.update_user(user_id, request)
        
        if updated_user:
            # Log activity
            await self._log_activity(
                user_id=user_id,
                activity_type="user_updated",
                metadata={"updates": request.__dict__}
            )
            
            logger.info("User updated successfully", user_id=user_id)
        
        return updated_user
    
    async def upgrade_user_tier(self, user_id: str, new_tier: UserTier) -> Optional[User]:
        """Upgrade user tier."""
        logger.info("Upgrading user tier", user_id=user_id, new_tier=new_tier.value)
        
        request = UpdateUserRequest(tier=new_tier)
        updated_user = await self.update_user(user_id, request)
        
        if updated_user:
            # Log activity
            await self._log_activity(
                user_id=user_id,
                activity_type="tier_upgraded",
                metadata={"new_tier": new_tier.value}
            )
        
        return updated_user
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user."""
        logger.info("Deactivating user", user_id=user_id)
        
        request = UpdateUserRequest(status=UserStatus.DEACTIVATED)
        updated_user = await self.update_user(user_id, request)
        
        if updated_user:
            # Cancel active subscriptions
            active_subscription = await self.subscription_repository.get_active_subscription(user_id)
            if active_subscription:
                await self.subscription_repository.cancel_subscription(active_subscription.subscription_id)
            
            # Log activity
            await self._log_activity(
                user_id=user_id,
                activity_type="user_deactivated"
            )
            
            return True
        
        return False
    
    async def create_subscription(self, request: CreateSubscriptionRequest) -> Subscription:
        """Create subscription."""
        logger.info("Creating subscription", user_id=request.user_id, tier=request.tier.value)
        
        # Check if user exists
        user = await self.user_repository.get_user(request.user_id)
        if not user:
            raise ValueError(f"User {request.user_id} not found")
        
        # Cancel existing active subscription
        existing_subscription = await self.subscription_repository.get_active_subscription(request.user_id)
        if existing_subscription:
            await self.subscription_repository.cancel_subscription(existing_subscription.subscription_id)
        
        # Create subscription
        now = datetime.utcnow()
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            user_id=request.user_id,
            tier=request.tier,
            status=SubscriptionStatus.ACTIVE,
            start_date=now,
            end_date=request.end_date,
            created_at=now,
            updated_at=now,
            stripe_subscription_id=request.stripe_subscription_id,
            metadata={}
        )
        
        # Save subscription
        created_subscription = await self.subscription_repository.create_subscription(subscription)
        
        # Update user tier
        await self.upgrade_user_tier(request.user_id, request.tier)
        
        # Log activity
        await self._log_activity(
            user_id=request.user_id,
            activity_type="subscription_created",
            metadata={
                "subscription_id": created_subscription.subscription_id,
                "tier": request.tier.value
            }
        )
        
        logger.info("Subscription created successfully", subscription_id=created_subscription.subscription_id)
        return created_subscription
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription."""
        return await self.subscription_repository.get_active_subscription(user_id)
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel subscription."""
        logger.info("Cancelling subscription", subscription_id=subscription_id)
        
        subscription = await self.subscription_repository.get_subscription(subscription_id)
        if not subscription:
            return False
        
        # Cancel subscription
        cancelled = await self.subscription_repository.cancel_subscription(subscription_id)
        
        if cancelled:
            # Downgrade user tier to registered
            await self.upgrade_user_tier(subscription.user_id, UserTier.REGISTERED)
            
            # Log activity
            await self._log_activity(
                user_id=subscription.user_id,
                activity_type="subscription_cancelled",
                metadata={"subscription_id": subscription_id}
            )
            
            logger.info("Subscription cancelled successfully", subscription_id=subscription_id)
        
        return cancelled
    
    async def get_user_activities(
        self, 
        user_id: str, 
        limit: int = 100,
        activity_type: Optional[str] = None
    ) -> List[UserActivity]:
        """Get user activities."""
        return await self.activity_repository.get_user_activities(user_id, limit, activity_type)
    
    async def record_login(self, user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """Record user login."""
        # Update last login
        user = await self.user_repository.get_user(user_id)
        if user:
            request = UpdateUserRequest()
            await self.user_repository.update_user(user_id, request)
        
        # Log activity
        await self._log_activity(
            user_id=user_id,
            activity_type="login",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def _log_activity(
        self,
        user_id: str,
        activity_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log user activity."""
        try:
            activity = UserActivity(
                activity_id=str(uuid.uuid4()),
                user_id=user_id,
                activity_type=activity_type,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {}
            )
            
            await self.activity_repository.log_activity(activity)
        except Exception as e:
            logger.warning("Failed to log activity", error=str(e), user_id=user_id, activity_type=activity_type)