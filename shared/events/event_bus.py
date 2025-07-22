"""Event bus implementation using Kafka."""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

import asyncio
from confluent_kafka import Producer, Consumer, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
import structlog

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Event types in the system."""
    
    # Prediction events
    PREDICTION_REQUESTED = "prediction.requested"
    PREDICTION_COMPLETED = "prediction.completed"
    
    # Chat events
    CHAT_MESSAGE_SENT = "chat.message.sent"
    CHAT_RESPONSE_GENERATED = "chat.response.generated"
    
    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    
    # Subscription events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    
    # Billing events
    BILLING_PAYMENT_PROCESSED = "billing.payment.processed"
    
    # Analytics events
    ANALYTICS_USER_ACTIVITY = "analytics.user.activity"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health.check"


@dataclass
class BaseEvent:
    """Base event class."""
    
    event_id: str
    event_type: EventType
    timestamp: datetime
    correlation_id: str
    source_service: str
    version: str = "1.0"
    
    def __post_init__(self):
        """Ensure event_id and timestamp are set."""
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


@dataclass
class PredictionRequestedEvent(BaseEvent):
    """Event fired when a prediction is requested."""
    
    user_id: str
    team_home: str
    team_away: str
    prediction_types: List[str]
    match_date: str
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = EventType.PREDICTION_REQUESTED


@dataclass
class PredictionCompletedEvent(BaseEvent):
    """Event fired when a prediction is completed."""
    
    prediction_id: str
    user_id: str
    team_home: str
    team_away: str
    predictions: List[Dict[str, Any]]
    processing_time_ms: float
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = EventType.PREDICTION_COMPLETED


@dataclass
class ChatMessageSentEvent(BaseEvent):
    """Event fired when a chat message is sent."""
    
    user_id: str
    conversation_id: str
    message: str
    topic: str
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = EventType.CHAT_MESSAGE_SENT


@dataclass
class UserRegisteredEvent(BaseEvent):
    """Event fired when a user registers."""
    
    user_id: str
    email: str
    tier: str
    registration_source: str
    
    def __post_init__(self):
        super().__post_init__()
        if not self.event_type:
            self.event_type = EventType.USER_REGISTERED


class EventBus(ABC):
    """Abstract event bus interface."""
    
    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event."""
        pass
    
    @abstractmethod
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: Callable[[BaseEvent], None],
        consumer_group: str = None
    ) -> None:
        """Subscribe to an event type."""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus."""
        pass


class KafkaEventBus(EventBus):
    """Kafka implementation of event bus."""
    
    def __init__(
        self, 
        bootstrap_servers: str = "localhost:9092",
        schema_registry_url: str = "http://localhost:8081"
    ):
        """Initialise Kafka event bus."""
        self.bootstrap_servers = bootstrap_servers
        self.schema_registry_url = schema_registry_url
        self.producer = None
        self.consumers: Dict[str, Consumer] = {}
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        
        # Producer configuration
        self.producer_config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'ai-betting-platform-producer',
            'acks': 'all',
            'retries': 3,
            'retry.backoff.ms': 1000,
            'max.in.flight.requests.per.connection': 5,
            'enable.idempotence': True,
            'compression.type': 'snappy'
        }
        
        # Consumer configuration base
        self.consumer_config_base = {
            'bootstrap.servers': bootstrap_servers,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000
        }
    
    async def start(self) -> None:
        """Start the event bus."""
        logger.info("Starting Kafka event bus...")
        
        # Create producer
        self.producer = Producer(self.producer_config)
        
        # Create topics if they don't exist
        await self._create_topics()
        
        self.running = True
        logger.info("Kafka event bus started")
    
    async def stop(self) -> None:
        """Stop the event bus."""
        logger.info("Stopping Kafka event bus...")
        
        self.running = False
        
        # Close producer
        if self.producer:
            self.producer.flush(timeout=10)
            self.producer = None
        
        # Close all consumers
        for consumer in self.consumers.values():
            consumer.close()
        self.consumers.clear()
        
        logger.info("Kafka event bus stopped")
    
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to Kafka."""
        if not self.producer:
            raise RuntimeError("Event bus not started")
        
        try:
            # Serialise event to JSON
            event_data = asdict(event)
            event_data['timestamp'] = event.timestamp.isoformat()
            
            # Produce message
            self.producer.produce(
                topic=event.event_type.value,
                key=event.correlation_id,
                value=json.dumps(event_data),
                callback=self._delivery_callback
            )
            
            # Trigger delivery
            self.producer.poll(0)
            
            logger.info(
                "Event published",
                event_type=event.event_type.value,
                event_id=event.event_id,
                correlation_id=event.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event.event_type.value,
                error=str(e)
            )
            raise
    
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: Callable[[BaseEvent], None],
        consumer_group: str = None
    ) -> None:
        """Subscribe to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        self.handlers[event_type].append(handler)
        
        # Create consumer if not exists
        if consumer_group not in self.consumers:
            consumer_config = {
                **self.consumer_config_base,
                'group.id': consumer_group or f'ai-betting-{event_type.value}'
            }
            
            consumer = Consumer(consumer_config)
            consumer.subscribe([event_type.value])
            self.consumers[consumer_group or event_type.value] = consumer
            
            # Start consumer task
            asyncio.create_task(self._consume_messages(consumer, event_type))
        
        logger.info(
            "Subscribed to event",
            event_type=event_type.value,
            consumer_group=consumer_group
        )
    
    async def _consume_messages(self, consumer: Consumer, event_type: EventType) -> None:
        """Consume messages from Kafka."""
        while self.running:
            try:
                message = consumer.poll(timeout=1.0)
                
                if message is None:
                    continue
                
                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error("Consumer error", error=message.error())
                        continue
                
                # Process message
                await self._process_message(message, event_type)
                
            except Exception as e:
                logger.error("Error consuming messages", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_message(self, message, event_type: EventType) -> None:
        """Process a received message."""
        try:
            # Deserialise event
            event_data = json.loads(message.value().decode('utf-8'))
            
            # Convert timestamp back to datetime
            if 'timestamp' in event_data:
                event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
            
            # Create event object based on type
            event = self._create_event_from_data(event_type, event_data)
            
            # Call all handlers for this event type
            handlers = self.handlers.get(event_type, [])
            for handler in handlers:
                try:
                    await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
                except Exception as e:
                    logger.error(
                        "Event handler error",
                        event_type=event_type.value,
                        handler=handler.__name__,
                        error=str(e)
                    )
            
            logger.debug(
                "Event processed",
                event_type=event_type.value,
                event_id=event.event_id
            )
            
        except Exception as e:
            logger.error("Failed to process message", error=str(e))
    
    def _create_event_from_data(self, event_type: EventType, data: Dict[str, Any]) -> BaseEvent:
        """Create event object from data."""
        # Map event types to classes
        event_classes = {
            EventType.PREDICTION_REQUESTED: PredictionRequestedEvent,
            EventType.PREDICTION_COMPLETED: PredictionCompletedEvent,
            EventType.CHAT_MESSAGE_SENT: ChatMessageSentEvent,
            EventType.USER_REGISTERED: UserRegisteredEvent,
        }
        
        event_class = event_classes.get(event_type, BaseEvent)
        return event_class(**data)
    
    def _delivery_callback(self, error, message):
        """Callback for message delivery."""
        if error:
            logger.error("Message delivery failed", error=str(error))
        else:
            logger.debug("Message delivered", topic=message.topic(), partition=message.partition())
    
    async def _create_topics(self) -> None:
        """Create Kafka topics if they don't exist."""
        admin_client = AdminClient({'bootstrap.servers': self.bootstrap_servers})
        
        # Define topics
        topics = [
            NewTopic(event_type.value, num_partitions=3, replication_factor=1)
            for event_type in EventType
        ]
        
        try:
            # Create topics
            futures = admin_client.create_topics(topics)
            
            # Wait for topics to be created
            for topic, future in futures.items():
                try:
                    future.result()
                    logger.debug("Topic created", topic=topic)
                except Exception as e:
                    if "already exists" in str(e):
                        logger.debug("Topic already exists", topic=topic)
                    else:
                        logger.error("Failed to create topic", topic=topic, error=str(e))
        
        except Exception as e:
            logger.error("Failed to create topics", error=str(e))


class InMemoryEventBus(EventBus):
    """In-memory event bus for testing."""
    
    def __init__(self):
        """Initialise in-memory event bus."""
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.events: List[BaseEvent] = []
    
    async def start(self) -> None:
        """Start the event bus."""
        pass
    
    async def stop(self) -> None:
        """Stop the event bus."""
        pass
    
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event."""
        self.events.append(event)
        
        # Call handlers immediately
        handlers = self.handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event) if asyncio.iscoroutinefunction(handler) else handler(event)
            except Exception as e:
                logger.error("Handler error", error=str(e))
    
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: Callable[[BaseEvent], None],
        consumer_group: str = None
    ) -> None:
        """Subscribe to an event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        self.handlers[event_type].append(handler)
    
    def get_events(self, event_type: EventType = None) -> List[BaseEvent]:
        """Get published events (for testing)."""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events.copy()
    
    def clear_events(self) -> None:
        """Clear all events (for testing)."""
        self.events.clear()