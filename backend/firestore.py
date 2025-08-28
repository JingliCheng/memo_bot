"""
Firestore module for AI Companion chatbot with memory.

This module provides functions to interact with Google Cloud Firestore for storing
and retrieving user memories and messages. It implements the memory model described
in the high-level design document.

Memory types:
- semantic: stable truths (likes/dislikes/preferences)
- episodic: short events for possible later promotion

Collections:
- users/{uid}/memories: stores memory items with type, key, value, confidence, salience, ts
- users/{uid}/messages: stores conversation messages with role, content, ts
"""

import os
import logging
from typing import Dict, List, Optional, Any
from time import time
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore client
try:
    # For local development, you can set GOOGLE_APPLICATION_CREDENTIALS
    # For production (Cloud Run), it will use default service account
    db = firestore.Client()
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")
    db = None


class FirestoreError(Exception):
    """Custom exception for Firestore operations."""
    pass


def _get_memories_collection(uid: str) -> firestore.CollectionReference:
    """
    Get the memories collection reference for a user.
    
    Args:
        uid: User identifier
        
    Returns:
        Firestore collection reference for user memories
        
    Raises:
        FirestoreError: If Firestore client is not initialized
    """
    if db is None:
        raise FirestoreError("Firestore client not initialized")
    return db.collection("users").document(uid).collection("memories")


def _get_messages_collection(uid: str) -> firestore.CollectionReference:
    """
    Get the messages collection reference for a user.
    
    Args:
        uid: User identifier
        
    Returns:
        Firestore collection reference for user messages
        
    Raises:
        FirestoreError: If Firestore client is not initialized
    """
    if db is None:
        raise FirestoreError("Firestore client not initialized")
    return db.collection("users").document(uid).collection("messages")


def get_top_facts(uid: str, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Retrieve top semantic facts for a user, ordered by salience and confidence.
    
    This function queries the user's memories collection for semantic-type memories
    and returns them sorted by the product of salience and confidence scores.
    
    Args:
        uid: User identifier
        limit: Maximum number of facts to return (default: 6)
        
    Returns:
        List of memory dictionaries with highest salience*confidence scores
        
    Raises:
        FirestoreError: If query fails
        
    Example:
        >>> facts = get_top_facts("user123", limit=3)
        >>> print(facts[0]["key"])  # "likes_animals"
        >>> print(facts[0]["value"])  # "triceratops"
    """
    try:
        memories_ref = _get_memories_collection(uid)
        
        # Query for semantic memories only
        query = memories_ref.where(
            filter=FieldFilter("type", "==", "semantic")
        ).order_by("salience", direction=firestore.Query.DESCENDING).order_by(
            "confidence", direction=firestore.Query.DESCENDING
        ).limit(limit)
        
        docs = query.stream()
        facts = []
        
        for doc in docs:
            memory_data = doc.to_dict()
            memory_data["id"] = doc.id  # Include document ID for reference
            facts.append(memory_data)
        
        # Sort by salience * confidence for final ordering
        facts.sort(key=lambda m: m.get("salience", 0) * m.get("confidence", 0), reverse=True)
        
        logger.info(f"Retrieved {len(facts)} top facts for user {uid}")
        return facts[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get top facts for user {uid}: {e}")
        raise FirestoreError(f"Failed to retrieve top facts: {e}")


def add_memory(uid: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a memory item to the user's memories collection.
    
    This function stores a memory item with the specified type, key, value,
    confidence, and salience. If a memory with the same key already exists,
    it will be updated with the new values.
    
    Args:
        uid: User identifier
        item: Memory item dictionary containing:
            - type: "semantic" or "episodic"
            - key: Memory key/identifier
            - value: Memory value/content
            - confidence: Confidence score (0.0-1.0)
            - salience: Salience score (0.0-1.0)
            - ts: Timestamp (optional, will be set if not provided)
            
    Returns:
        Dictionary with operation result including document ID and count
        
    Raises:
        FirestoreError: If operation fails
        
    Example:
        >>> memory_item = {
        ...     "type": "semantic",
        ...     "key": "likes_animals",
        ...     "value": "triceratops",
        ...     "confidence": 0.9,
        ...     "salience": 1.0
        ... }
        >>> result = add_memory("user123", memory_item)
        >>> print(result["doc_id"])  # Document ID
    """
    try:
        memories_ref = _get_memories_collection(uid)
        
        # Ensure timestamp is set
        if "ts" not in item:
            item["ts"] = time()
        
        # Validate required fields
        required_fields = ["type", "key", "value", "confidence", "salience"]
        for field in required_fields:
            if field not in item:
                raise ValueError(f"Missing required field: {field}")
        
        # Check if memory with same key already exists
        existing_query = memories_ref.where(
            filter=FieldFilter("key", "==", item["key"])
        ).limit(1)
        
        existing_docs = list(existing_query.stream())
        
        if existing_docs:
            # Update existing memory
            doc_ref = existing_docs[0].reference
            doc_ref.update(item)
            doc_id = doc_ref.id
            logger.info(f"Updated existing memory for user {uid}, key: {item['key']}")
        else:
            # Create new memory
            doc_ref = memories_ref.add(item)
            doc_id = doc_ref[1].id
            logger.info(f"Created new memory for user {uid}, key: {item['key']}")
        
        # Get total count of memories for this user
        total_count = len(list(memories_ref.stream()))
        
        return {
            "ok": True,
            "doc_id": doc_id,
            "count": total_count,
            "action": "updated" if existing_docs else "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to add memory for user {uid}: {e}")
        raise FirestoreError(f"Failed to add memory: {e}")


def get_last_messages(uid: str, limit: int = 12) -> List[Dict[str, Any]]:
    """
    Retrieve the last N messages for a user, ordered by timestamp.
    
    This function queries the user's messages collection and returns the most
    recent messages, which are used for conversation context.
    
    Args:
        uid: User identifier
        limit: Maximum number of messages to return (default: 12)
        
    Returns:
        List of message dictionaries ordered by timestamp (newest first)
        
    Raises:
        FirestoreError: If query fails
        
    Example:
        >>> messages = get_last_messages("user123", limit=6)
        >>> print(messages[0]["role"])  # "user" or "assistant"
        >>> print(messages[0]["content"])  # Message content
    """
    try:
        messages_ref = _get_messages_collection(uid)
        
        # Query messages ordered by timestamp (newest first)
        query = messages_ref.order_by("ts", direction=firestore.Query.DESCENDING).limit(limit)
        
        docs = query.stream()
        messages = []
        
        for doc in docs:
            message_data = doc.to_dict()
            message_data["id"] = doc.id  # Include document ID for reference
            messages.append(message_data)
        
        # Return in chronological order (oldest first) for conversation context
        messages.reverse()
        
        logger.info(f"Retrieved {len(messages)} messages for user {uid}")
        return messages
        
    except Exception as e:
        logger.error(f"Failed to get messages for user {uid}: {e}")
        raise FirestoreError(f"Failed to retrieve messages: {e}")


def add_message(uid: str, role: str, content: str, timestamp: Optional[float] = None) -> str:
    """
    Add a message to the user's messages collection.
    
    This function stores a conversation message (user or assistant) with
    the specified role and content.
    
    Args:
        uid: User identifier
        role: Message role ("user" or "assistant")
        content: Message content
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        Document ID of the created message
        
    Raises:
        FirestoreError: If operation fails
        
    Example:
        >>> msg_id = add_message("user123", "user", "Hello, bot!")
        >>> print(msg_id)  # Document ID
    """
    try:
        messages_ref = _get_messages_collection(uid)
        
        message_data = {
            "role": role,
            "content": content,
            "ts": timestamp or time()
        }
        
        doc_ref = messages_ref.add(message_data)
        doc_id = doc_ref[1].id
        
        logger.info(f"Added {role} message for user {uid}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to add message for user {uid}: {e}")
        raise FirestoreError(f"Failed to add message: {e}")


def delete_memory(uid: str, memory_id: str) -> bool:
    """
    Delete a specific memory by its document ID.
    
    Args:
        uid: User identifier
        memory_id: Document ID of the memory to delete
        
    Returns:
        True if deletion was successful
        
    Raises:
        FirestoreError: If operation fails
    """
    try:
        memories_ref = _get_memories_collection(uid)
        doc_ref = memories_ref.document(memory_id)
        doc_ref.delete()
        
        logger.info(f"Deleted memory {memory_id} for user {uid}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete memory {memory_id} for user {uid}: {e}")
        raise FirestoreError(f"Failed to delete memory: {e}")


def get_all_memories(uid: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all memories for a user, optionally filtered by type.
    
    Args:
        uid: User identifier
        memory_type: Optional filter by memory type ("semantic" or "episodic")
        
    Returns:
        List of all memory dictionaries
        
    Raises:
        FirestoreError: If query fails
    """
    try:
        memories_ref = _get_memories_collection(uid)
        
        if memory_type:
            query = memories_ref.where(
                filter=FieldFilter("type", "==", memory_type)
            )
        else:
            query = memories_ref
        
        docs = query.stream()
        memories = []
        
        for doc in docs:
            memory_data = doc.to_dict()
            memory_data["id"] = doc.id
            memories.append(memory_data)
        
        logger.info(f"Retrieved {len(memories)} memories for user {uid}")
        return memories
        
    except Exception as e:
        logger.error(f"Failed to get memories for user {uid}: {e}")
        raise FirestoreError(f"Failed to retrieve memories: {e}")


def consolidate_memories(uid: str, promotion_threshold: int = 3) -> Dict[str, int]:
    """
    Consolidate episodic memories into semantic memories based on frequency.
    
    This function promotes frequently mentioned episodic memories to semantic
    memories, which is part of the memory consolidation process described
    in the high-level design.
    
    Args:
        uid: User identifier
        promotion_threshold: Number of occurrences required for promotion
        
    Returns:
        Dictionary with consolidation statistics
        
    Raises:
        FirestoreError: If operation fails
    """
    try:
        memories_ref = _get_memories_collection(uid)
        
        # Get all episodic memories
        episodic_query = memories_ref.where(
            filter=FieldFilter("type", "==", "episodic")
        )
        
        episodic_docs = list(episodic_query.stream())
        
        # Count occurrences by key
        key_counts = {}
        for doc in episodic_docs:
            data = doc.to_dict()
            key = data.get("key")
            if key:
                key_counts[key] = key_counts.get(key, 0) + 1
        
        # Promote frequently mentioned memories
        promoted_count = 0
        for key, count in key_counts.items():
            if count >= promotion_threshold:
                # Find the most recent episodic memory with this key
                key_query = memories_ref.where(
                    filter=FieldFilter("key", "==", key)
                ).where(
                    filter=FieldFilter("type", "==", "episodic")
                ).order_by("ts", direction=firestore.Query.DESCENDING).limit(1)
                
                key_docs = list(key_query.stream())
                if key_docs:
                    doc_ref = key_docs[0].reference
                    doc_ref.update({"type": "semantic", "salience": min(1.0, count * 0.1)})
                    promoted_count += 1
        
        logger.info(f"Consolidated {promoted_count} memories for user {uid}")
        return {
            "promoted_count": promoted_count,
            "total_episodic": len(episodic_docs)
        }
        
    except Exception as e:
        logger.error(f"Failed to consolidate memories for user {uid}: {e}")
        raise FirestoreError(f"Failed to consolidate memories: {e}")


# Health check function
def health_check() -> Dict[str, Any]:
    """
    Check if Firestore connection is healthy.
    
    Returns:
        Dictionary with health status and connection info
    """
    try:
        if db is None:
            return {"healthy": False, "error": "Firestore client not initialized"}
        
        # Try to read from a test collection
        test_ref = db.collection("_health_check")
        test_ref.limit(1).stream()
        
        return {
            "healthy": True,
            "project_id": db.project,
            "client_initialized": True
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "client_initialized": db is not None
        }
