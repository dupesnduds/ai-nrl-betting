"""Use cases for chat assistant service."""

import time
import uuid
from datetime import datetime
from typing import Optional, List

from ..domain.models import (
    ChatRequest, 
    ChatResponse, 
    Conversation, 
    Message, 
    ConversationTurn,
    ChatTopic,
    ChatModel,
    TopicClassifier,
    ConversationRepository,
    KnowledgeBase
)


class ProcessChatUseCase:
    """Use case for processing chat requests."""
    
    def __init__(
        self,
        chat_model: ChatModel,
        topic_classifier: TopicClassifier,
        conversation_repository: ConversationRepository,
        knowledge_base: KnowledgeBase
    ):
        self.chat_model = chat_model
        self.topic_classifier = topic_classifier
        self.conversation_repository = conversation_repository
        self.knowledge_base = knowledge_base
    
    async def execute(self, request: ChatRequest) -> ChatResponse:
        """Execute chat request and generate response."""
        start_time = time.time()
        
        # Get or create conversation
        conversation = await self._get_or_create_conversation(request)
        
        # Add user message to conversation
        user_message = Message(
            content=request.message,
            turn_type=ConversationTurn.USER,
            timestamp=datetime.utcnow()
        )
        conversation.messages.append(user_message)
        
        # Classify topic
        topic = await self.topic_classifier.classify_topic(request.message)
        conversation.topic = topic
        
        # Enhance conversation with knowledge
        await self._enhance_with_knowledge(conversation, topic)
        
        # Generate response
        response_text = await self.chat_model.generate_response(conversation, request)
        
        # Add assistant message to conversation
        assistant_message = Message(
            content=response_text,
            turn_type=ConversationTurn.ASSISTANT,
            timestamp=datetime.utcnow(),
            metadata={"topic": topic.value}
        )
        conversation.messages.append(assistant_message)
        
        # Save updated conversation
        conversation.updated_at = datetime.utcnow()
        await self.conversation_repository.save_conversation(conversation)
        
        # Calculate confidence and suggestions
        confidence = await self._calculate_confidence(response_text, topic)
        suggestions = await self._generate_suggestions(topic, conversation)
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation.conversation_id,
            topic=topic,
            confidence=confidence,
            processing_time_ms=processing_time,
            suggestions=suggestions,
            metadata={
                "model_name": self.chat_model.model_name,
                "model_version": self.chat_model.model_version,
                "message_count": len(conversation.messages)
            }
        )
    
    async def _get_or_create_conversation(self, request: ChatRequest) -> Conversation:
        """Get existing conversation or create new one."""
        if request.conversation_id:
            conversation = await self.conversation_repository.get_conversation(
                request.conversation_id
            )
            if conversation:
                return conversation
        
        # Create new conversation
        conversation_id = str(uuid.uuid4())
        return Conversation(
            conversation_id=conversation_id,
            user_id=request.user_id or "anonymous",
            messages=[],
            context=request.context
        )
    
    async def _enhance_with_knowledge(self, conversation: Conversation, topic: ChatTopic) -> None:
        """Enhance conversation with relevant knowledge."""
        if topic == ChatTopic.MATCH_PREDICTION:
            # Extract team names from the latest message
            latest_message = conversation.messages[-1].content.lower()
            teams = await self._extract_team_names(latest_message)
            
            if len(teams) >= 2:
                predictions = await self.knowledge_base.get_recent_predictions(
                    teams[0], teams[1]
                )
                if predictions:
                    conversation.context = conversation.context or {}
                    conversation.context["recent_predictions"] = predictions
        
        elif topic == ChatTopic.TEAM_ANALYSIS:
            # Extract team name and get team info
            latest_message = conversation.messages[-1].content.lower()
            teams = await self._extract_team_names(latest_message)
            
            if teams:
                team_info = await self.knowledge_base.get_team_info(teams[0])
                if team_info:
                    conversation.context = conversation.context or {}
                    conversation.context["team_info"] = team_info
    
    async def _extract_team_names(self, message: str) -> List[str]:
        """Extract NRL team names from message."""
        nrl_teams = [
            "brisbane broncos", "sydney roosters", "melbourne storm",
            "penrith panthers", "north queensland cowboys", "south sydney rabbitohs",
            "canterbury bulldogs", "parramatta eels", "newcastle knights",
            "cronulla sharks", "st george illawarra dragons", "wests tigers",
            "gold coast titans", "manly sea eagles", "new zealand warriors",
            "canberra raiders"
        ]
        
        found_teams = []
        message_lower = message.lower()
        
        for team in nrl_teams:
            if team in message_lower:
                found_teams.append(team.title())
            else:
                # Check for partial matches (e.g., "broncos" for "Brisbane Broncos")
                team_parts = team.split()
                for part in team_parts:
                    if len(part) > 4 and part in message_lower:
                        found_teams.append(team.title())
                        break
        
        return found_teams
    
    async def _calculate_confidence(self, response: str, topic: ChatTopic) -> float:
        """Calculate confidence score for the response."""
        # Simple confidence calculation based on response length and topic
        base_confidence = 0.7
        
        # Adjust based on response length
        if len(response) < 50:
            base_confidence *= 0.8
        elif len(response) > 200:
            base_confidence *= 1.1
        
        # Adjust based on topic
        if topic in [ChatTopic.MATCH_PREDICTION, ChatTopic.TEAM_ANALYSIS]:
            base_confidence *= 1.1
        elif topic == ChatTopic.OTHER:
            base_confidence *= 0.8
        
        return min(base_confidence, 1.0)
    
    async def _generate_suggestions(
        self, 
        topic: ChatTopic, 
        conversation: Conversation
    ) -> List[str]:
        """Generate follow-up suggestions."""
        suggestions = []
        
        if topic == ChatTopic.MATCH_PREDICTION:
            suggestions = [
                "What are the key factors in this prediction?",
                "How have these teams performed recently?",
                "What are the betting odds for this match?"
            ]
        elif topic == ChatTopic.TEAM_ANALYSIS:
            suggestions = [
                "How is this team's recent form?",
                "Who are the key players to watch?",
                "What are their strengths and weaknesses?"
            ]
        elif topic == ChatTopic.BETTING_ADVICE:
            suggestions = [
                "What's the best strategy for this bet?",
                "What are the risks involved?",
                "How confident are you in this advice?"
            ]
        else:
            suggestions = [
                "Can you tell me about NRL predictions?",
                "Which teams are performing well this season?",
                "Help me understand betting strategies"
            ]
        
        return suggestions[:3]  # Return max 3 suggestions


class GetConversationHistoryUseCase:
    """Use case for retrieving conversation history."""
    
    def __init__(self, conversation_repository: ConversationRepository):
        self.conversation_repository = conversation_repository
    
    async def execute(self, user_id: str, limit: int = 10) -> List[Conversation]:
        """Get conversation history for a user."""
        return await self.conversation_repository.get_user_conversations(user_id, limit)