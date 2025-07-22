"""Chat model implementation using transformers."""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from typing import List, Dict, Any
import time
from pathlib import Path
import os

from ..domain.models import ChatModel, Conversation, ChatRequest, ConversationTurn
from ....shared.events.event_bus import EventBus, ChatMessageSentEvent, EventType


class DistilGPT2ChatModel(ChatModel):
    """DistilGPT-2 based chat model for NRL betting conversations."""
    
    def __init__(self, model_path: str = "distilgpt2", event_bus: EventBus = None):
        """Initialise the chat model."""
        self.model_path = model_path
        self._tokenizer = None
        self._model = None
        self._pipeline = None
        self._is_loaded = False
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._event_bus = event_bus
        
        # NRL-specific context
        self.nrl_context = """
You are an expert NRL (National Rugby League) analyst and betting advisor. 
You provide informed insights about NRL teams, players, and matches.
You give responsible betting advice and always remind users to bet responsibly.
"""
    
    @property
    def model_name(self) -> str:
        """Return the model name."""
        return "DistilGPT-2 NRL Chat"
    
    @property
    def model_version(self) -> str:
        """Return the model version."""
        return "1.0.0"
    
    async def is_ready(self) -> bool:
        """Check if the model is ready."""
        if not self._is_loaded:
            await self._load_model()
        return self._is_loaded
    
    async def generate_response(
        self, 
        conversation: Conversation, 
        request: ChatRequest
    ) -> str:
        """Generate a response based on conversation context."""
        if not await self.is_ready():
            raise RuntimeError("Model is not ready")
        
        # Publish chat message event if event bus is available
        if self._event_bus and request.message:
            try:
                event = ChatMessageSentEvent(
                    event_id="",
                    event_type=EventType.CHAT_MESSAGE_SENT,
                    timestamp=None,
                    correlation_id=conversation.conversation_id,
                    source_service="chat-assistant",
                    user_id=conversation.user_id,
                    conversation_id=conversation.conversation_id,
                    message=request.message,
                    topic=conversation.topic.value if conversation.topic else "general_nrl"
                )
                await self._event_bus.publish(event)
            except Exception as e:
                # Log but don't fail on event publishing
                pass
        
        # Build conversation context
        conversation_text = self._build_conversation_context(conversation)
        
        # Generate response
        try:
            # Use the pipeline for text generation
            response = self._pipeline(
                conversation_text,
                max_length=min(len(conversation_text.split()) + request.max_tokens, 1024),
                temperature=request.temperature,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
                num_return_sequences=1,
                truncation=True
            )
            
            generated_text = response[0]['generated_text']
            
            # Extract only the new response (after the conversation context)
            new_response = generated_text[len(conversation_text):].strip()
            
            # Clean up the response
            new_response = self._clean_response(new_response)
            
            # Ensure we have a meaningful response
            if not new_response or len(new_response.strip()) < 10:
                new_response = self._get_fallback_response(conversation.topic)
            
            return new_response
            
        except Exception as e:
            # Fallback response on error
            return f"I apologise, I'm having trouble processing your request right now. Could you please rephrase your question about NRL betting?"
    
    async def _load_model(self) -> None:
        """Load the model and tokenizer."""
        try:
            # Check if we have a custom fine-tuned model
            if Path(self.model_path).exists() and Path(self.model_path).is_dir():
                # Load custom fine-tuned model
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self._model = AutoModelForCausalLM.from_pretrained(self.model_path)
            else:
                # Load base DistilGPT-2 model
                self._tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
                self._model = AutoModelForCausalLM.from_pretrained("distilgpt2")
            
            # Set pad token
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Move model to device
            self._model.to(self._device)
            
            # Create pipeline
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device=0 if self._device == "cuda" else -1
            )
            
            self._is_loaded = True
            
        except Exception as e:
            raise RuntimeError(f"Failed to load chat model: {e}")
    
    def _build_conversation_context(self, conversation: Conversation) -> str:
        """Build conversation context for the model."""
        context_parts = [self.nrl_context]
        
        # Add conversation history (last 5 messages to keep context manageable)
        recent_messages = conversation.messages[-5:] if len(conversation.messages) > 5 else conversation.messages
        
        for message in recent_messages:
            if message.turn_type == ConversationTurn.USER:
                context_parts.append(f"User: {message.content}")
            elif message.turn_type == ConversationTurn.ASSISTANT:
                context_parts.append(f"Assistant: {message.content}")
        
        # Add additional context if available
        if conversation.context:
            if "recent_predictions" in conversation.context:
                predictions = conversation.context["recent_predictions"]
                context_parts.append(f"Recent prediction data: {predictions}")
            
            if "team_info" in conversation.context:
                team_info = conversation.context["team_info"]
                context_parts.append(f"Team information: {team_info}")
        
        context_parts.append("Assistant:")
        
        return "\n".join(context_parts)
    
    def _clean_response(self, response: str) -> str:
        """Clean up the generated response."""
        # Remove common artifacts
        response = response.strip()
        
        # Remove incomplete sentences at the end
        sentences = response.split('.')
        if len(sentences) > 1 and len(sentences[-1].strip()) < 10:
            response = '.'.join(sentences[:-1]) + '.'
        
        # Remove repetitive text
        words = response.split()
        if len(words) > 10:
            # Simple repetition detection
            unique_words = []
            for word in words:
                if word not in unique_words[-3:]:  # Avoid immediate repetition
                    unique_words.append(word)
            response = ' '.join(unique_words)
        
        # Ensure response ends properly
        if response and not response.endswith(('.', '!', '?')):
            response += '.'
        
        return response
    
    def _get_fallback_response(self, topic) -> str:
        """Get a fallback response based on topic."""
        fallback_responses = {
            "match_prediction": "I'd be happy to help with match predictions. Could you tell me which teams you're interested in?",
            "team_analysis": "I can provide team analysis. Which NRL team would you like me to analyse?",
            "betting_advice": "I can offer betting insights, but remember to always bet responsibly and within your means.",
            "general_nrl": "I'm here to help with NRL information and analysis. What specific aspect interests you?",
            "other": "I specialise in NRL analysis and betting insights. How can I help you with rugby league?"
        }
        
        return fallback_responses.get(
            topic.value if topic else "other",
            "I'm here to help with NRL betting analysis. What would you like to know?"
        )