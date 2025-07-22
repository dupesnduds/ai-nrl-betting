from typing import List, Optional
from .models import User, SubscriptionTier

def get_allowed_modes(user: Optional[User]) -> List[str]:
    """
    Given a User object (or None for anonymous), return the list of allowed modes.
    """
    if user is None:
        # Unregistered user
        return ["Quick Pick"]

    tier = user.subscription_tier

    # Registered but no paid tier
    if tier is None or tier == SubscriptionTier.BASIC:
        return ["Quick Pick", "Form Cruncher"]

    # Paid tiers
    allowed_modes = ["Quick Pick", "Form Cruncher"]

    if tier in (SubscriptionTier.DEEP_DIVE, SubscriptionTier.STACKED, SubscriptionTier.EDGE_FINDER, SubscriptionTier.CUSTOM):
        allowed_modes.append("Deep Dive")
    if tier in (SubscriptionTier.STACKED, SubscriptionTier.EDGE_FINDER, SubscriptionTier.CUSTOM):
        allowed_modes.append("Stacked")
    if tier in (SubscriptionTier.EDGE_FINDER, SubscriptionTier.CUSTOM):
        allowed_modes.append("Edge Finder")
    if tier == SubscriptionTier.CUSTOM:
        allowed_modes.append("Custom Deep Dive Training")

    return allowed_modes
