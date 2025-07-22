"""Domain models for chat assistant service."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ConversationTurn(str, Enum):
    """Types of conversation turns."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatTopic(str, Enum):
    """Chat topic categories."""
    MATCH_PREDICTION = "match_prediction"
    TEAM_ANALYSIS = "team_analysis"
    PLAYER_STATS = "player_stats"
    BETTING_ADVICE = "betting_advice"
    GENERAL_NRL = "general_nrl"
    OTHER = "other"


@dataclass
class Message:
    """Individual message in a conversation."""
    
    content: str
    turn_type: ConversationTurn
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Conversation:
    """Complete conversation context."""
    
    conversation_id: str
    user_id: str
    messages: List[Message]
    topic: Optional[ChatTopic] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class ChatRequest:
    """Request for chat completion."""
    
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    max_tokens: int = 150
    temperature: float = 0.7


@dataclass
class ChatResponse:
    """Response from chat assistant."""
    
    response: str
    conversation_id: str
    topic: ChatTopic
    confidence: float
    processing_time_ms: float
    sources: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatModel(ABC):
    """Abstract base class for chat models."""
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass
    
    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the model version."""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        conversation: Conversation,
        request: ChatRequest
    ) -> str:
        """Generate a response based on conversation context."""
        pass
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """Check if the model is ready to generate responses."""
        pass


class TopicClassifier(ABC):
    """Abstract base class for topic classification."""
    
    @abstractmethod
    async def classify_topic(self, message: str) -> ChatTopic:
        """Classify the topic of a message."""
        pass


class ConversationRepository(ABC):
    """Abstract repository for conversation management."""
    
    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> str:
        """Save a conversation and return conversation ID."""
        pass
    
    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        pass
    
    @abstractmethod
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Conversation]:
        """Get recent conversations for a user."""
        pass
    
    @abstractmethod
    async def update_conversation(self, conversation: Conversation) -> None:
        """Update an existing conversation."""
        pass


class KnowledgeBase(ABC):
    """Abstract base class for knowledge retrieval."""
    
    @abstractmethod
    async def search_knowledge(
        self, 
        query: str, 
        topic: ChatTopic,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant information."""
        pass
    
    @abstractmethod
    async def get_team_info(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific team."""
        pass
    
    @abstractmethod
    async def get_recent_predictions(
        self, 
        team_home: str, 
        team_away: str
    ) -> Optional[Dict[str, Any]]:
        """Get recent predictions for a match."""
        pass