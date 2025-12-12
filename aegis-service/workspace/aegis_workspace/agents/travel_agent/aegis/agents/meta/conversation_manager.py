"""
Conversation Manager for managing conversational context and flow
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from aegis.types import ConversationContext, ConversationState
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class ConversationManager:
    """
    Manages conversational context, state, and flow for agents.
    Supports session persistence and conversation memory.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the conversation manager.
        
        Args:
            storage_path: Path to store conversation sessions. If None, uses in-memory only.
        """
        self.sessions: Dict[str, ConversationContext] = {}
        self.storage_path = storage_path
        self.conversation_history: Dict[str, List[Dict]] = {}
        
        if storage_path:
            os.makedirs(storage_path, exist_ok=True)
            self._load_sessions()
    
    def create_session(self, user_preferences: Dict[str, Any] = None) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_preferences: Initial user preferences for the session
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())[:8]
        context = ConversationContext(
            session_id=session_id,
            state=ConversationState.IDLE,
            user_preferences=user_preferences or {}
        )
        self.sessions[session_id] = context
        self.conversation_history[session_id] = []
        
        if self.storage_path:
            self._save_session(session_id)
        
        logger.info(f"Created new conversation session: {session_id}", title="Conversation")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """
        Get a conversation session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            ConversationContext if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """
        Update a conversation session.
        
        Args:
            session_id: The session ID
            **kwargs: Fields to update
            
        Returns:
            True if updated successfully
        """
        if session_id not in self.sessions:
            return False
        
        context = self.sessions[session_id]
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.updated_at = datetime.now().isoformat()
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def update_state(self, session_id: str, new_state: ConversationState) -> bool:
        """
        Update the conversation state.
        
        Args:
            session_id: The session ID
            new_state: The new conversation state
            
        Returns:
            True if updated successfully
        """
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].update_state(new_state)
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: The session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional message metadata
            
        Returns:
            True if added successfully
        """
        if session_id not in self.sessions:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append(message)
        self.sessions[session_id].increment_turn()
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def get_history(self, session_id: str, limit: int = None) -> List[Dict]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        history = self.conversation_history.get(session_id, [])
        if limit:
            return history[-limit:]
        return history
    
    def add_clarification_request(self, session_id: str, question: str) -> bool:
        """
        Add a clarification request to the session.
        
        Args:
            session_id: The session ID
            question: The clarification question
            
        Returns:
            True if added successfully
        """
        if session_id not in self.sessions:
            return False
        
        context = self.sessions[session_id]
        context.clarification_requests.append(question)
        context.pending_questions.append(question)
        context.update_state(ConversationState.CLARIFYING)
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def resolve_clarification(self, session_id: str, answer: str) -> bool:
        """
        Resolve a pending clarification.
        
        Args:
            session_id: The session ID
            answer: The user's answer
            
        Returns:
            True if resolved successfully
        """
        if session_id not in self.sessions:
            return False
        
        context = self.sessions[session_id]
        if context.pending_questions:
            context.pending_questions.pop(0)
        
        if not context.pending_questions:
            context.update_state(ConversationState.PROCESSING)
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def set_user_preference(self, session_id: str, key: str, value: Any) -> bool:
        """
        Set a user preference for the session.
        
        Args:
            session_id: The session ID
            key: Preference key
            value: Preference value
            
        Returns:
            True if set successfully
        """
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].user_preferences[key] = value
        
        if self.storage_path:
            self._save_session(session_id)
        
        return True
    
    def get_user_preference(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get a user preference from the session.
        
        Args:
            session_id: The session ID
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        if session_id not in self.sessions:
            return default
        
        return self.sessions[session_id].user_preferences.get(key, default)
    
    def end_session(self, session_id: str) -> bool:
        """
        End a conversation session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if ended successfully
        """
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].update_state(ConversationState.COMPLETED)
        
        if self.storage_path:
            self._save_session(session_id)
        
        logger.info(f"Ended conversation session: {session_id}", title="Conversation")
        return True
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation context.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with context summary
        """
        if session_id not in self.sessions:
            return {}
        
        context = self.sessions[session_id]
        history = self.conversation_history.get(session_id, [])
        
        return {
            "session_id": session_id,
            "state": context.state.value,
            "turn_count": context.turn_count,
            "message_count": len(history),
            "has_pending_questions": len(context.pending_questions) > 0,
            "pending_questions": context.pending_questions,
            "user_preferences": context.user_preferences,
            "created_at": context.created_at,
            "updated_at": context.updated_at
        }
    
    def extract_conversation_context(self, session_id: str, max_messages: int = 10) -> str:
        """
        Extract conversation context as a formatted string for agent instructions.
        
        Args:
            session_id: The session ID
            max_messages: Maximum messages to include
            
        Returns:
            Formatted context string
        """
        if session_id not in self.sessions:
            return ""
        
        history = self.get_history(session_id, limit=max_messages)
        context = self.sessions[session_id]
        
        context_parts = []
        
        # Add user preferences
        if context.user_preferences:
            context_parts.append("USER PREFERENCES:")
            for key, value in context.user_preferences.items():
                context_parts.append(f"  - {key}: {value}")
        
        # Add recent conversation
        if history:
            context_parts.append("\nRECENT CONVERSATION:")
            for msg in history:
                role = msg["role"].upper()
                content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
                context_parts.append(f"  [{role}]: {content}")
        
        # Add pending questions
        if context.pending_questions:
            context_parts.append("\nPENDING QUESTIONS:")
            for q in context.pending_questions:
                context_parts.append(f"  - {q}")
        
        return "\n".join(context_parts)
    
    def _save_session(self, session_id: str):
        """Save session to storage"""
        if not self.storage_path or session_id not in self.sessions:
            return
        
        session_file = os.path.join(self.storage_path, f"{session_id}.json")
        data = {
            "context": self.sessions[session_id].model_dump(),
            "history": self.conversation_history.get(session_id, [])
        }
        
        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_sessions(self):
        """Load sessions from storage"""
        if not self.storage_path:
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                session_file = os.path.join(self.storage_path, filename)
                
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    self.sessions[session_id] = ConversationContext(**data["context"])
                    self.conversation_history[session_id] = data.get("history", [])
                except Exception as e:
                    logger.warning(f"Failed to load session {session_id}: {e}", title="Conversation")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up old inactive sessions.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, context in self.sessions.items():
            try:
                updated = datetime.fromisoformat(context.updated_at)
                age_hours = (current_time - updated).total_seconds() / 3600
                
                if age_hours > max_age_hours and context.state == ConversationState.COMPLETED:
                    sessions_to_remove.append(session_id)
            except:
                continue
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            if session_id in self.conversation_history:
                del self.conversation_history[session_id]
            
            if self.storage_path:
                session_file = os.path.join(self.storage_path, f"{session_id}.json")
                if os.path.exists(session_file):
                    os.remove(session_file)
        
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions", title="Conversation")


# Global conversation manager instance
conversation_manager = ConversationManager()


def get_conversation_manager(storage_path: Optional[str] = None) -> ConversationManager:
    """Get or create a conversation manager instance"""
    global conversation_manager
    
    if storage_path and conversation_manager.storage_path != storage_path:
        conversation_manager = ConversationManager(storage_path)
    
    return conversation_manager

