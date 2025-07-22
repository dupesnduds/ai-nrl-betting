"""FastAPI interface for chat assistant service."""

import os
from typing import List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.auth.firebase import get_current_user, require_tier, User
from shared.monitoring.telemetry import (
    setup_telemetry, 
    instrument_fastapi, 
    setup_structured_logging,
    MetricsCollector
)

from ..application.use_cases import ProcessChatUseCase, GetConversationHistoryUseCase
from ..domain.models import ChatRequest, ChatResponse
from ..infrastructure.chat_model import DistilGPT2ChatModel
from ..infrastructure.topic_classifier import SimpleTopicClassifier
from ..infrastructure.repositories import InMemoryConversationRepository
from ..infrastructure.knowledge_base import StaticKnowledgeBase
from ..infrastructure.event_setup import create_event_bus, setup_event_subscriptions


# Configure telemetry and logging
tracer, meter = setup_telemetry("chat-assistant")
logger = setup_structured_logging("chat-assistant")

# Create FastAPI app
app = FastAPI(
    title="AI Betting Platform - Chat Assistant",
    description="Conversational AI assistant for NRL betting insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app, "chat-assistant")

# Global dependencies
chat_model = None
topic_classifier = None
conversation_repository = None
knowledge_base = None
event_bus = None
process_chat_use_case = None
get_history_use_case = None


# Request/Response models
class ChatRequestModel(BaseModel):
    message: str
    conversation_id: str = None
    max_tokens: int = 150
    temperature: float = 0.7


class ChatResponseModel(BaseModel):
    response: str
    conversation_id: str
    topic: str
    confidence: float
    processing_time_ms: float
    suggestions: List[str] = []


class ConversationSummary(BaseModel):
    conversation_id: str
    topic: str = None
    message_count: int
    last_message_time: str
    preview: str


@app.on_event("startup")
async def startup_event():
    """Initialise dependencies on startup."""
    global chat_model, topic_classifier, conversation_repository, knowledge_base, event_bus
    global process_chat_use_case, get_history_use_case
    
    logger.info("Starting Chat Assistant service...")
    
    # Configure model path
    model_path = os.getenv("CHAT_MODEL_PATH", "distilgpt2")
    
    # Initialise event bus
    try:
        event_bus = create_event_bus()
        if event_bus:
            await event_bus.start()
            await setup_event_subscriptions(event_bus)
            logger.info("Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None
    
    # Initialise components
    chat_model = DistilGPT2ChatModel(model_path, event_bus)
    topic_classifier = SimpleTopicClassifier()
    conversation_repository = InMemoryConversationRepository()
    knowledge_base = StaticKnowledgeBase()
    
    # Initialise use cases
    process_chat_use_case = ProcessChatUseCase(
        chat_model, 
        topic_classifier, 
        conversation_repository, 
        knowledge_base
    )
    get_history_use_case = GetConversationHistoryUseCase(conversation_repository)
    
    # Warm up the model
    logger.info("Warming up chat model...")
    if await chat_model.is_ready():
        logger.info("Chat model ready")
    else:
        logger.warning("Chat model not ready")
    
    logger.info("Chat Assistant service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chat-assistant",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        is_ready = await chat_model.is_ready()
        
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chat model not ready"
            )
        
        return {
            "status": "ready",
            "model_loaded": True,
            "model_name": chat_model.model_name
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@app.post("/chat", response_model=ChatResponseModel)
async def chat(
    request: ChatRequestModel,
    user: User = Depends(get_current_user)
):
    """Process a chat message and return response."""
    
    try:
        # Create domain request
        chat_request = ChatRequest(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=user.uid,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Record metrics
        MetricsCollector.record_prediction_request(
            model="chat-assistant",
            team_home="",
            team_away=""
        )
        
        # Process chat request
        response = await process_chat_use_case.execute(chat_request)
        
        # Record latency
        MetricsCollector.record_prediction_latency(
            model="chat-assistant",
            duration=response.processing_time_ms / 1000
        )
        
        logger.info(
            "Chat request processed",
            conversation_id=response.conversation_id,
            topic=response.topic.value,
            user_id=user.uid,
            processing_time_ms=response.processing_time_ms
        )
        
        return ChatResponseModel(
            response=response.response,
            conversation_id=response.conversation_id,
            topic=response.topic.value,
            confidence=response.confidence,
            processing_time_ms=response.processing_time_ms,
            suggestions=response.suggestions or []
        )
        
    except Exception as e:
        logger.error(
            "Chat request failed",
            error=str(e),
            user_id=user.uid,
            message_preview=request.message[:50]
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


@app.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations(
    limit: int = 10,
    user: User = Depends(require_tier("registered"))
):
    """Get conversation history for the user."""
    
    try:
        conversations = await get_history_use_case.execute(user.uid, limit)
        
        summaries = []
        for conv in conversations:
            # Create summary
            last_message = conv.messages[-1] if conv.messages else None
            preview = last_message.content[:100] + "..." if last_message and len(last_message.content) > 100 else (last_message.content if last_message else "")
            
            summaries.append(ConversationSummary(
                conversation_id=conv.conversation_id,
                topic=conv.topic.value if conv.topic else None,
                message_count=len(conv.messages),
                last_message_time=conv.updated_at.isoformat() if conv.updated_at else "",
                preview=preview
            ))
        
        return summaries
        
    except Exception as e:
        logger.error(
            "Failed to get conversations",
            error=str(e),
            user_id=user.uid
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user)
):
    """Get a specific conversation."""
    
    try:
        conversation = await conversation_repository.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Check if user owns the conversation
        if conversation.user_id != user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return {
            "conversation_id": conversation.conversation_id,
            "topic": conversation.topic.value if conversation.topic else None,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "messages": [
                {
                    "content": msg.content,
                    "turn_type": msg.turn_type.value,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in conversation.messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get conversation",
            error=str(e),
            conversation_id=conversation_id,
            user_id=user.uid
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@app.get("/metrics")
async def get_service_metrics():
    """Get service metrics (for monitoring)."""
    model_ready = await chat_model.is_ready() if chat_model else False
    
    return {
        "service": "chat-assistant",
        "status": "operational",
        "model_ready": model_ready,
        "model_name": chat_model.model_name if chat_model else None
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.interfaces.api:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )