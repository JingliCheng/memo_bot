"""
Unit tests for Episodic Memory functionality.

This module tests:
- ChromaDB client initialization
- Episode creation and storage
- Semantic search functionality
- Embedding generation
- Episode retrieval
- Episode data model
"""

import pytest
import time
import uuid
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from episodic_memory import (
    Episode,
    EpisodicMemory,
    get_chroma_client,
    get_episodic_collection,
    get_embedding,
    create_episode_embeddings,
    create_episode,
    store_conversation_round,
    search_user_episodes,
    get_user_recent_episodes,
    test_episodic_memory
)


class TestEpisodeDataModel:
    """Test Episode data model."""
    
    def test_episode_creation(self):
        """Test creating an episode."""
        user_id = "test_user_123"
        user_message = "I love dinosaurs"
        ai_response = "That's wonderful! Dinosaurs are fascinating creatures."
        round_number = 1
        session_id = "session_001"
        
        episode = Episode(
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response,
            round_number=round_number,
            session_id=session_id
        )
        
        assert episode.user_id == user_id
        assert episode.user_message == user_message
        assert episode.ai_response == ai_response
        assert episode.round_number == round_number
        assert episode.session_id == session_id
        assert isinstance(episode.timestamp, datetime)
        assert episode.id.startswith("ep_")
        assert len(episode.id) > 10  # Should have timestamp + uuid
    
    def test_episode_embeddings_generation(self):
        """Test that episode generates embeddings."""
        episode = Episode(
            user_id="test_user",
            user_message="Hello world",
            ai_response="Hi there!",
            round_number=1,
            session_id="test_session"
        )
        
        # Check that embeddings are generated
        assert hasattr(episode, 'user_embedding')
        assert hasattr(episode, 'ai_embedding')
        assert hasattr(episode, 'combined_embedding')
        
        # Check embedding dimensions (OpenAI text-embedding-3-small = 1536 dimensions)
        assert len(episode.user_embedding) == 1536
        assert len(episode.ai_embedding) == 1536
        assert len(episode.combined_embedding) == 1536
        
        # Combined embedding should be average of user and AI embeddings
        expected_combined = [(u + a) / 2 for u, a in zip(episode.user_embedding, episode.ai_embedding)]
        assert episode.combined_embedding == expected_combined
    
    def test_episode_token_calculation(self):
        """Test token calculation for episodes."""
        episode = Episode(
            user_id="test_user",
            user_message="Hello world",
            ai_response="Hi there!",
            round_number=1,
            session_id="test_session"
        )
        
        # Should calculate tokens based on word count
        assert episode.tokens == 4  # "Hello world" (2) + "Hi there!" (2)
    
    def test_episode_to_dict(self):
        """Test converting episode to dictionary."""
        episode = Episode(
            user_id="test_user",
            user_message="Hello world",
            ai_response="Hi there!",
            round_number=1,
            session_id="test_session"
        )
        
        episode_dict = episode.to_dict()
        
        assert isinstance(episode_dict, dict)
        assert episode_dict["user_id"] == "test_user"
        assert episode_dict["user_message"] == "Hello world"
        assert episode_dict["ai_response"] == "Hi there!"
        assert episode_dict["round_number"] == 1
        assert episode_dict["session_id"] == "test_session"
        assert episode_dict["tokens"] == 4
        assert "timestamp" in episode_dict
        assert "user_embedding" in episode_dict
        assert "ai_embedding" in episode_dict
        assert "combined_embedding" in episode_dict


class TestChromaClientOperations:
    """Test ChromaDB client operations."""
    
    @patch('episodic_memory.os.getenv')
    def test_get_chroma_client_local_mode(self, mock_getenv):
        """Test getting Chroma client in local mode."""
        mock_getenv.side_effect = lambda key, default=None: {
            "CHROMA_MODE": "local",
            "OPENAI_API_KEY": "test_key"
        }.get(key, default)
        
        with patch('episodic_memory.chromadb.PersistentClient') as mock_client:
            client = get_chroma_client()
            
            mock_client.assert_called_once_with(path="./chroma_db")
            assert client == mock_client.return_value
    
    @patch('episodic_memory.os.getenv')
    def test_get_chroma_client_cloud_mode(self, mock_getenv):
        """Test getting Chroma client in cloud mode."""
        mock_getenv.side_effect = lambda key, default=None: {
            "CHROMA_MODE": "cloud",
            "CHROMA_API_KEY": "test_api_key",
            "CHROMA_TENANT": "test_tenant",
            "CHROMA_DATABASE": "test_database",
            "OPENAI_API_KEY": "test_key"
        }.get(key, default)
        
        with patch('episodic_memory.chromadb.CloudClient') as mock_client:
            client = get_chroma_client()
            
            mock_client.assert_called_once_with(
                api_key="test_api_key",
                tenant="test_tenant",
                database="test_database"
            )
            assert client == mock_client.return_value
    
    @patch('episodic_memory.os.getenv')
    def test_get_chroma_client_cloud_mode_missing_vars(self, mock_getenv):
        """Test getting Chroma client in cloud mode with missing environment variables."""
        mock_getenv.side_effect = lambda key, default=None: {
            "CHROMA_MODE": "cloud",
            "CHROMA_API_KEY": "test_api_key",
            # Missing CHROMA_TENANT and CHROMA_DATABASE
            "OPENAI_API_KEY": "test_key"
        }.get(key, default)
        
        with pytest.raises(ValueError, match="Chroma Cloud mode requires"):
            get_chroma_client()
    
    @patch('episodic_memory.get_chroma_client')
    def test_get_episodic_collection_existing(self, mock_get_client):
        """Test getting existing episodic collection."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        collection = get_episodic_collection()
        
        assert collection == mock_collection
        mock_client.get_collection.assert_called_once_with("episodic_memory")
    
    @patch('episodic_memory.get_chroma_client')
    def test_get_episodic_collection_create_new(self, mock_get_client):
        """Test creating new episodic collection when it doesn't exist."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        collection = get_episodic_collection()
        
        assert collection == mock_collection
        mock_client.create_collection.assert_called_once_with(
            name="episodic_memory",
            metadata={"description": "Conversation rounds stored as episodes with embeddings"}
        )


class TestEmbeddingOperations:
    """Test embedding generation operations."""
    
    @patch('episodic_memory._openai_client')
    def test_get_embedding_success(self, mock_client):
        """Test successful embedding generation."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        
        embedding = get_embedding("test text")
        
        assert len(embedding) == 1536
        assert embedding == [0.1] * 1536
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test text"
        )
    
    @patch('episodic_memory._openai_client')
    def test_get_embedding_error(self, mock_client):
        """Test embedding generation error handling."""
        mock_client.embeddings.create.side_effect = Exception("API error")
        
        embedding = get_embedding("test text")
        
        # Should return fallback embedding
        assert len(embedding) == 1536
        assert embedding == [0.0] * 1536
    
    @patch('episodic_memory._use_openai', False)
    def test_get_embedding_no_openai(self):
        """Test embedding generation without OpenAI."""
        embedding = get_embedding("test text")
        
        # Should return fallback embedding
        assert len(embedding) == 1536
        assert embedding == [0.0] * 1536
    
    @patch('episodic_memory.get_embedding')
    def test_create_episode_embeddings(self, mock_get_embedding):
        """Test creating embeddings for episode storage."""
        mock_get_embedding.side_effect = [
            [0.1] * 1536,  # user embedding
            [0.2] * 1536   # ai embedding
        ]
        
        embeddings = create_episode_embeddings("Hello", "Hi there!")
        
        assert "user_embedding" in embeddings
        assert "ai_embedding" in embeddings
        assert "combined_embedding" in embeddings
        
        assert embeddings["user_embedding"] == [0.1] * 1536
        assert embeddings["ai_embedding"] == [0.2] * 1536
        
        # Combined should be average
        expected_combined = [0.15] * 1536
        assert embeddings["combined_embedding"] == expected_combined


class TestEpisodicMemoryOperations:
    """Test EpisodicMemory class operations."""
    
    def test_episodic_memory_initialization(self):
        """Test EpisodicMemory initialization."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            memory = EpisodicMemory()
            
            assert memory.collection == mock_collection
            mock_get_collection.assert_called_once()
    
    def test_store_episode_success(self):
        """Test successful episode storage."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            memory = EpisodicMemory()
            
            episode = Episode(
                user_id="test_user",
                user_message="Hello",
                ai_response="Hi!",
                round_number=1,
                session_id="test_session"
            )
            
            episode_id = memory.store_episode(episode)
            
            assert episode_id == episode.id
            mock_collection.add.assert_called_once()
            
            # Check the call arguments
            call_args = mock_collection.add.call_args
            assert len(call_args[1]['embeddings']) == 1
            assert len(call_args[1]['metadatas']) == 1
            assert len(call_args[1]['ids']) == 1
            assert call_args[1]['ids'][0] == episode.id
    
    def test_store_episode_error(self):
        """Test episode storage error handling."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_collection.add.side_effect = Exception("Storage error")
            mock_get_collection.return_value = mock_collection
            
            memory = EpisodicMemory()
            
            episode = Episode(
                user_id="test_user",
                user_message="Hello",
                ai_response="Hi!",
                round_number=1,
                session_id="test_session"
            )
            
            with pytest.raises(Exception, match="Storage error"):
                memory.store_episode(episode)
    
    def test_search_episodes_success(self):
        """Test successful episode search."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection, \
             patch('episodic_memory.get_embedding') as mock_get_embedding:
            
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            # Mock search results
            mock_results = {
                'metadatas': [[
                    {
                        "user_message": "I love dinosaurs",
                        "ai_response": "That's great!",
                        "round_number": 1,
                        "session_id": "session_1",
                        "timestamp": "2023-01-01T00:00:00",
                        "tokens": 5
                    }
                ]],
                'ids': [['episode_1']],
                'distances': [[0.2]]
            }
            mock_collection.query.return_value = mock_results
            mock_get_embedding.return_value = [0.1] * 1536
            
            memory = EpisodicMemory()
            episodes = memory.search_episodes("test_user", "dinosaurs", limit=5)
            
            assert len(episodes) == 1
            episode = episodes[0]
            assert episode["user_message"] == "I love dinosaurs"
            assert episode["ai_response"] == "That's great!"
            assert episode["similarity"] == 0.8  # 1 - 0.2
            assert episode["id"] == "episode_1"
    
    def test_search_episodes_no_results(self):
        """Test episode search with no results."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection, \
             patch('episodic_memory.get_embedding') as mock_get_embedding:
            
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            # Mock empty results
            mock_results = {
                'metadatas': [[]],
                'ids': [[]],
                'distances': [[]]
            }
            mock_collection.query.return_value = mock_results
            mock_get_embedding.return_value = [0.1] * 1536
            
            memory = EpisodicMemory()
            episodes = memory.search_episodes("test_user", "query", limit=5)
            
            assert episodes == []
    
    def test_search_episodes_error(self):
        """Test episode search error handling."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection, \
             patch('episodic_memory.get_embedding') as mock_get_embedding:
            
            mock_collection = Mock()
            mock_collection.query.side_effect = Exception("Search error")
            mock_get_collection.return_value = mock_collection
            mock_get_embedding.return_value = [0.1] * 1536
            
            memory = EpisodicMemory()
            episodes = memory.search_episodes("test_user", "query", limit=5)
            
            assert episodes == []
    
    def test_get_recent_episodes_success(self):
        """Test successful recent episodes retrieval."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            # Mock recent episodes
            mock_docs = [
                Mock(to_dict=lambda: {
                    "user_message": "Recent message 1",
                    "ai_response": "Response 1",
                    "round_number": 3,
                    "session_id": "session_1",
                    "timestamp": "2023-01-03T00:00:00",
                    "tokens": 5
                }),
                Mock(to_dict=lambda: {
                    "user_message": "Recent message 2",
                    "ai_response": "Response 2",
                    "round_number": 2,
                    "session_id": "session_1",
                    "timestamp": "2023-01-02T00:00:00",
                    "tokens": 4
                })
            ]
            mock_collection.get.return_value = {'metadatas': [doc.to_dict() for doc in mock_docs], 'ids': ['ep1', 'ep2']}
            
            memory = EpisodicMemory()
            episodes = memory.get_recent_episodes("test_user", limit=10)
            
            assert len(episodes) == 2
            assert episodes[0]["user_message"] == "Recent message 1"
            assert episodes[1]["user_message"] == "Recent message 2"
    
    def test_get_recent_episodes_error(self):
        """Test recent episodes retrieval error handling."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_collection.get.side_effect = Exception("Get error")
            mock_get_collection.return_value = mock_collection
            
            memory = EpisodicMemory()
            episodes = memory.get_recent_episodes("test_user", limit=10)
            
            assert episodes == []
    
    def test_get_episode_count_success(self):
        """Test successful episode count retrieval."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            # Mock episode count
            mock_collection.get.return_value = {'ids': ['ep1', 'ep2', 'ep3']}
            
            memory = EpisodicMemory()
            count = memory.get_episode_count("test_user")
            
            assert count == 3
    
    def test_get_episode_count_error(self):
        """Test episode count retrieval error handling."""
        with patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_collection.get.side_effect = Exception("Count error")
            mock_get_collection.return_value = mock_collection
            
            memory = EpisodicMemory()
            count = memory.get_episode_count("test_user")
            
            assert count == 0


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_episode_function(self):
        """Test create_episode convenience function."""
        episode = create_episode(
            user_id="test_user",
            user_message="Hello",
            ai_response="Hi!",
            round_number=1,
            session_id="test_session"
        )
        
        assert isinstance(episode, Episode)
        assert episode.user_id == "test_user"
        assert episode.user_message == "Hello"
        assert episode.ai_response == "Hi!"
        assert episode.round_number == 1
        assert episode.session_id == "test_session"
    
    @patch('episodic_memory.EpisodicMemory')
    def test_store_conversation_round(self, mock_memory_class):
        """Test store_conversation_round convenience function."""
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        mock_memory.store_episode.return_value = "episode_id_123"
        
        episode_id = store_conversation_round(
            user_id="test_user",
            user_message="Hello",
            ai_response="Hi!",
            round_number=1,
            session_id="test_session"
        )
        
        assert episode_id == "episode_id_123"
        mock_memory_class.assert_called_once()
        mock_memory.store_episode.assert_called_once()
    
    @patch('episodic_memory.EpisodicMemory')
    def test_search_user_episodes(self, mock_memory_class):
        """Test search_user_episodes convenience function."""
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        mock_memory.search_episodes.return_value = [{"id": "ep1", "similarity": 0.9}]
        
        episodes = search_user_episodes("test_user", "query", limit=5)
        
        assert len(episodes) == 1
        assert episodes[0]["id"] == "ep1"
        mock_memory_class.assert_called_once()
        mock_memory.search_episodes.assert_called_once_with("test_user", "query", 5)
    
    @patch('episodic_memory.EpisodicMemory')
    def test_get_user_recent_episodes(self, mock_memory_class):
        """Test get_user_recent_episodes convenience function."""
        mock_memory = Mock()
        mock_memory_class.return_value = mock_memory
        mock_memory.get_recent_episodes.return_value = [{"id": "ep1", "round_number": 1}]
        
        episodes = get_user_recent_episodes("test_user", limit=10)
        
        assert len(episodes) == 1
        assert episodes[0]["id"] == "ep1"
        mock_memory_class.assert_called_once()
        mock_memory.get_recent_episodes.assert_called_once_with("test_user", 10)


class TestEpisodicMemoryTestFunction:
    """Test the test_episodic_memory function."""
    
    @patch('episodic_memory.store_conversation_round')
    @patch('episodic_memory.search_user_episodes')
    @patch('episodic_memory.get_user_recent_episodes')
    def test_episodic_memory_test_function(self, mock_get_recent, mock_search, mock_store):
        """Test the episodic memory test function."""
        mock_store.return_value = "episode_id"
        mock_search.return_value = [{"user_message": "I love hiking", "similarity": 0.9}]
        mock_get_recent.return_value = [{"round_number": 1, "user_message": "Hello"}]
        
        # Should not raise any exceptions
        test_episodic_memory()
        
        # Verify that functions were called
        assert mock_store.call_count == 5  # 5 test episodes
        assert mock_search.call_count == 4  # 4 search queries
        assert mock_get_recent.call_count == 1  # 1 recent episodes call
