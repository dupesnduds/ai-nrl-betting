"""Event bus setup for chat assistant service."""

import os
from typing import Optional

from ....shared.events.event_bus import EventBus, KafkaEventBus, InMemoryEventBus


def create_event_bus() -> Optional[EventBus]:
    """Create and configure event bus based on environment."""
    
    # Check if we're in production/development mode with Kafka
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    schema_registry_url = os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
    
    if kafka_servers:
        # Use Kafka event bus
        return KafkaEventBus(
            bootstrap_servers=kafka_servers,
            schema_registry_url=schema_registry_url
        )
    else:
        # Use in-memory event bus for testing
        return InMemoryEventBus()


async def setup_event_subscriptions(event_bus: EventBus) -> None:
    """Set up event subscriptions for the chat assistant service."""
    
    # Subscribe to prediction completed events to provide context in chat
    from ....shared.events.event_bus import EventType
    
    async def handle_prediction_completed(event):
        """Handle prediction completed events."""
        # This could be used to update conversation context
        # or send notifications to users
        pass
    
    await event_bus.subscribe(
        EventType.PREDICTION_COMPLETED,
        handle_prediction_completed,
        consumer_group="chat-assistant-predictions"
    )