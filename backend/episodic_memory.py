"""
Episodic Memory System using Chroma Cloud for vector storage and retrieval.
Stores conversation rounds as episodes with embeddings for semantic search.
"""
from __future__ import annotations
import os
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ---- Configuration ----
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT") 
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Chroma deployment mode: "local" or "cloud"
CHROMA_MODE = os.getenv("CHROMA_MODE", "local").lower()

# Initialize OpenAI client for embeddings
if OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    _use_openai = True
else:
    _openai_client = None
    _use_openai = False

# ---- Chroma Client Setup ----
def get_chroma_client():
    """Initialize and return Chroma client (local or cloud based on CHROMA_MODE)."""
    
    if CHROMA_MODE == "cloud":
        # Use Chroma Cloud
        if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE]):
            raise ValueError(
                "Chroma Cloud mode requires CHROMA_API_KEY, CHROMA_TENANT, and CHROMA_DATABASE environment variables."
            )
        
        print("Using Chroma Cloud")
        return chromadb.Client(
            chroma_cloud_api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
        )
    
    else:
        # Use local Chroma (default)
        print("Using local Chroma database")
        return chromadb.PersistentClient(
            path="./chroma_db"  # Local persistence
        )

def get_episodic_collection():
    """Get or create the episodic memory collection."""
    client = get_chroma_client()
    
    try:
        # Try to get existing collection
        collection = client.get_collection("episodic_memory")
    except Exception:
        # Create collection if it doesn't exist
        collection = client.create_collection(
            name="episodic_memory",
            metadata={"description": "Conversation rounds stored as episodes with embeddings"}
        )
    
    return collection

# ---- Embedding Functions ----
def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI's text-embedding-3-small model."""
    if not _use_openai:
        # Fallback: return random embedding for testing
        return [0.0] * 1536
    
    try:
        response = _openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0.0] * 1536

def create_episode_embeddings(user_message: str, ai_response: str) -> Dict[str, List[float]]:
    """Create embeddings for episode storage."""
    
    # Get individual embeddings
    user_embedding = get_embedding(user_message)
    ai_embedding = get_embedding(ai_response)
    
    # Combined embedding as average
    combined_embedding = [
        (u + a) / 2 for u, a in zip(user_embedding, ai_embedding)
    ]
    
    return {
        "user_embedding": user_embedding,
        "ai_embedding": ai_embedding,
        "combined_embedding": combined_embedding
    }

# ---- Episode Data Model ----
class Episode:
    """Represents a single conversation round as an episode."""
    
    def __init__(self, user_id: str, user_message: str, ai_response: str, 
                 round_number: int, session_id: str, timestamp: Optional[datetime] = None):
        self.id = f"ep_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.user_message = user_message
        self.ai_response = ai_response
        self.round_number = round_number
        self.session_id = session_id
        self.timestamp = timestamp or datetime.utcnow()
        
        # Generate embeddings
        embeddings = create_episode_embeddings(user_message, ai_response)
        self.user_embedding = embeddings["user_embedding"]
        self.ai_embedding = embeddings["ai_embedding"]
        self.combined_embedding = embeddings["combined_embedding"]
        
        # Calculate tokens (rough estimation)
        self.tokens = len(user_message.split()) + len(ai_response.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert episode to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "round_number": self.round_number,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "tokens": self.tokens,
            "user_embedding": self.user_embedding,
            "ai_embedding": self.ai_embedding,
            "combined_embedding": self.combined_embedding
        }

# ---- Episode Storage ----
class EpisodicMemory:
    """Manages episodic memory storage and retrieval using Chroma Cloud."""
    
    def __init__(self):
        self.collection = get_episodic_collection()
    
    def store_episode(self, episode: Episode) -> str:
        """Store an episode in Chroma Cloud."""
        try:
            # Prepare data for Chroma
            episode_data = episode.to_dict()
            
            # Store in Chroma collection
            self.collection.add(
                embeddings=[episode.combined_embedding],
                metadatas=[{
                    "user_id": episode.user_id,
                    "user_message": episode.user_message,
                    "ai_response": episode.ai_response,
                    "round_number": episode.round_number,
                    "session_id": episode.session_id,
                    "timestamp": episode.timestamp.isoformat(),
                    "tokens": episode.tokens
                }],
                ids=[episode.id]
            )
            
            print(f"Stored episode {episode.id} for user {episode.user_id}")
            return episode.id
            
        except Exception as e:
            print(f"Error storing episode: {e}")
            raise
    
    def search_episodes(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant episodes using semantic similarity."""
        try:
            # Get query embedding
            query_embedding = get_embedding(query)
            
            # Search in Chroma with user_id filter
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where={"user_id": user_id}  # Filter by user_id
            )
            
            # Format results
            episodes = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    episode = {
                        "id": results['ids'][0][i],
                        "user_message": metadata["user_message"],
                        "ai_response": metadata["ai_response"],
                        "round_number": metadata["round_number"],
                        "session_id": metadata["session_id"],
                        "timestamp": metadata["timestamp"],
                        "tokens": metadata["tokens"],
                        "similarity": 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                    episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            print(f"Error searching episodes: {e}")
            return []
    
    def get_recent_episodes(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent episodes for a user (fallback when no query provided)."""
        try:
            # Get all episodes for user (this is a limitation of Chroma - no direct timestamp ordering)
            # We'll need to implement this differently or use a different approach
            results = self.collection.get(
                where={"user_id": user_id}
            )
            
            # Sort by timestamp if available
            episodes = []
            if results['metadatas']:
                for i, metadata in enumerate(results['metadatas']):
                    episode = {
                        "id": results['ids'][i],
                        "user_message": metadata["user_message"],
                        "ai_response": metadata["ai_response"],
                        "round_number": metadata["round_number"],
                        "session_id": metadata["session_id"],
                        "timestamp": metadata["timestamp"],
                        "tokens": metadata["tokens"]
                    }
                    episodes.append(episode)
            
            # Sort by timestamp (most recent first)
            episodes.sort(key=lambda x: x["timestamp"], reverse=True)
            return episodes[:limit]
            
        except Exception as e:
            print(f"Error getting recent episodes: {e}")
            return []
    
    def get_episode_count(self, user_id: str) -> int:
        """Get total number of episodes for a user."""
        try:
            results = self.collection.get(
                where={"user_id": user_id}
            )
            return len(results['ids']) if results['ids'] else 0
        except Exception as e:
            print(f"Error getting episode count: {e}")
            return 0

# ---- Convenience Functions ----
def create_episode(user_id: str, user_message: str, ai_response: str, 
                  round_number: int, session_id: str) -> Episode:
    """Create a new episode from conversation round."""
    return Episode(
        user_id=user_id,
        user_message=user_message,
        ai_response=ai_response,
        round_number=round_number,
        session_id=session_id
    )

def store_conversation_round(user_id: str, user_message: str, ai_response: str, 
                           round_number: int, session_id: str) -> str:
    """Store a conversation round as an episode."""
    episode = create_episode(user_id, user_message, ai_response, round_number, session_id)
    memory = EpisodicMemory()
    return memory.store_episode(episode)

def search_user_episodes(user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for episodes relevant to a query."""
    memory = EpisodicMemory()
    return memory.search_episodes(user_id, query, limit)

def get_user_recent_episodes(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent episodes for a user."""
    memory = EpisodicMemory()
    return memory.get_recent_episodes(user_id, limit)

# ---- Test Functions ----
def test_episodic_memory():
    """Test the episodic memory system."""
    print("Testing Episodic Memory System...")
    
    # Test data
    user_id = "test_user_123"
    session_id = "test_session_001"
    
    # Create test episodes
    episodes = [
        ("I love hiking in the mountains near Seattle", "That sounds wonderful! Seattle has some beautiful mountain trails."),
        ("What's the weather like today?", "I don't have access to real-time weather data, but I can help you find weather information."),
        ("I'm learning Python programming", "That's great! Python is an excellent language to learn. What are you working on?"),
        ("I have a pet dog named Max", "Max sounds like a wonderful companion! What breed is Max?"),
        ("I'm planning a trip to Japan", "Japan is a fascinating country! What cities are you planning to visit?")
    ]
    
    # Store episodes
    for i, (user_msg, ai_msg) in enumerate(episodes, 1):
        episode_id = store_conversation_round(user_id, user_msg, ai_msg, i, session_id)
        print(f"Stored episode {i}: {episode_id}")
    
    # Test search
    print("\nTesting search...")
    search_queries = [
        "hiking and outdoor activities",
        "programming and coding",
        "pets and animals",
        "travel and vacations"
    ]
    
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        results = search_user_episodes(user_id, query, limit=2)
        for result in results:
            print(f"  - {result['user_message'][:50]}... (similarity: {result['similarity']:.3f})")
    
    # Test recent episodes
    print(f"\nRecent episodes for {user_id}:")
    recent = get_user_recent_episodes(user_id, limit=3)
    for episode in recent:
        print(f"  - Round {episode['round_number']}: {episode['user_message'][:50]}...")
    
    print("\nEpisodic Memory test completed!")

if __name__ == "__main__":
    test_episodic_memory()
