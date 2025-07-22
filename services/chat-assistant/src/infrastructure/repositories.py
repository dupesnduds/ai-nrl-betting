"""Repository implementations for chat assistant."""

from typing import Dict, List, Optional
from datetime import datetime

from ..domain.models import Conversation, ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    """In-memory implementation of conversation repository."""
    
    def __init__(self):
        """Initialise the repository."""
        self._conversations: Dict[str, Conversation] = {}
        self._user_conversations: Dict[str, List[str]] = {}
    
    async def save_conversation(self, conversation: Conversation) -> str:
        """Save a conversation and return conversation ID."""
        # Update timestamp
        conversation.updated_at = datetime.utcnow()
        
        # Store conversation
        self._conversations[conversation.conversation_id] = conversation
        
        # Update user's conversation list
        if conversation.user_id not in self._user_conversations:
            self._user_conversations[conversation.user_id] = []
        
        if conversation.conversation_id not in self._user_conversations[conversation.user_id]:
            self._user_conversations[conversation.user_id].append(conversation.conversation_id)
        
        return conversation.conversation_id
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        return self._conversations.get(conversation_id)
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Conversation]:
        """Get recent conversations for a user."""
        if user_id not in self._user_conversations:
            return []
        
        conversation_ids = self._user_conversations[user_id]
        
        # Get conversations and sort by updated_at
        conversations = []
        for conv_id in conversation_ids:
            if conv_id in self._conversations:
                conversations.append(self._conversations[conv_id])
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        # Return limited results
        return conversations[:limit]
    
    async def update_conversation(self, conversation: Conversation) -> None:
        """Update an existing conversation."""
        conversation.updated_at = datetime.utcnow()
        self._conversations[conversation.conversation_id] = conversation


class DatabaseConversationRepository(ConversationRepository):
    """Database implementation of conversation repository (placeholder)."""
    
    def __init__(self, db_session):
        """Initialise with database session."""
        self.db_session = db_session
    
    async def save_conversation(self, conversation: Conversation) -> str:
        """Save a conversation to database."""
        # TODO: Implement database storage
        # This would involve serialising the conversation and storing in DB
        raise NotImplementedError("Database implementation pending")
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation from database."""
        # TODO: Implement database retrieval
        raise NotImplementedError("Database implementation pending")
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Conversation]:
        """Get user conversations from database."""
        # TODO: Implement database query
        raise NotImplementedError("Database implementation pending")
    
    async def update_conversation(self, conversation: Conversation) -> None:
        """Update conversation in database."""
        # TODO: Implement database update
        raise NotImplementedError("Database implementation pending")