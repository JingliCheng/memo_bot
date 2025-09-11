"""
Tests for ChromaDB inspection API endpoint.

This module tests:
- GET /api/chroma/inspect - ChromaDB contents inspection
- Error handling for ChromaDB operations
- Response formatting and structure
"""

import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestChromaInspectAPI:
    """Test ChromaDB inspection API endpoint."""
    
    def test_chroma_inspect_success(self, client, mock_firebase_auth, auth_headers):
        """Test successful ChromaDB inspection."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            # Mock Chroma client and collection
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock episodes data
            mock_episodes = {
                'metadatas': [
                    {
                        "user_message": "I love dinosaurs",
                        "ai_response": "That's wonderful!",
                        "round_number": 1,
                        "session_id": "session_001",
                        "timestamp": "2023-01-01T00:00:00",
                        "tokens": 5
                    },
                    {
                        "user_message": "What's your favorite dinosaur?",
                        "ai_response": "I love triceratops!",
                        "round_number": 2,
                        "session_id": "session_001",
                        "timestamp": "2023-01-01T00:01:00",
                        "tokens": 6
                    }
                ],
                'ids': ['episode_1', 'episode_2']
            }
            mock_collection.get.return_value = mock_episodes
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["ok"] is True
            assert "episodes" in data
            assert "stats" in data
            
            # Check episodes structure
            episodes = data["episodes"]
            assert len(episodes) == 2
            
            # Episodes should be sorted by timestamp (most recent first)
            assert episodes[0]["user_message"] == "What's your favorite dinosaur?"
            assert episodes[1]["user_message"] == "I love dinosaurs"
            
            # Check episode structure
            episode = episodes[0]
            assert "id" in episode
            assert "user_message" in episode
            assert "ai_response" in episode
            assert "round_number" in episode
            assert "session_id" in episode
            assert "timestamp" in episode
            assert "tokens" in episode
            
            # Check stats structure
            stats = data["stats"]
            assert stats["total_episodes"] == 2
            assert stats["collection_name"] == "episodic_memory"
            assert stats["collection_exists"] is True
            assert "chroma_mode" in stats
    
    def test_chroma_inspect_no_episodes(self, client, mock_firebase_auth, auth_headers):
        """Test ChromaDB inspection with no episodes."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock empty episodes
            mock_collection.get.return_value = {'metadatas': [], 'ids': []}
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["ok"] is True
            assert data["episodes"] == []
            assert data["stats"]["total_episodes"] == 0
            assert data["stats"]["collection_exists"] is True
    
    def test_chroma_inspect_collection_not_exists(self, client, mock_firebase_auth, auth_headers):
        """Test ChromaDB inspection when collection doesn't exist."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            
            # Mock collection creation
            mock_get_collection.side_effect = [
                Exception("Collection not found"),  # First call fails
                mock_collection  # Second call succeeds (after creation)
            ]
            
            # Mock empty episodes for new collection
            mock_collection.get.return_value = {'metadatas': [], 'ids': []}
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["ok"] is True
            assert data["episodes"] == []
            assert data["stats"]["total_episodes"] == 0
            assert data["stats"]["collection_exists"] is True
    
    def test_chroma_inspect_chroma_error(self, client, mock_firebase_auth, auth_headers):
        """Test ChromaDB inspection with ChromaDB error."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.side_effect = Exception("ChromaDB connection error")
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return error response but still 200 status
            assert data["ok"] is True
            assert data["episodes"] == []
            assert data["stats"]["total_episodes"] == 0
            assert data["stats"]["collection_exists"] is False
            assert "error" in data["stats"]
            assert "ChromaDB connection error" in data["stats"]["error"]
    
    def test_chroma_inspect_episode_formatting(self, client, mock_firebase_auth, auth_headers):
        """Test that episodes are properly formatted in response."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock episode with all fields
            mock_episodes = {
                'metadatas': [
                    {
                        "user_message": "Hello world",
                        "ai_response": "Hi there!",
                        "round_number": 5,
                        "session_id": "session_123",
                        "timestamp": "2023-01-01T12:00:00",
                        "tokens": 3
                    }
                ],
                'ids': ['episode_123']
            }
            mock_collection.get.return_value = mock_episodes
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            episode = data["episodes"][0]
            assert episode["id"] == "episode_123"
            assert episode["user_message"] == "Hello world"
            assert episode["ai_response"] == "Hi there!"
            assert episode["round_number"] == 5
            assert episode["session_id"] == "session_123"
            assert episode["timestamp"] == "2023-01-01T12:00:00"
            assert episode["tokens"] == 3
    
    def test_chroma_inspect_sorting(self, client, mock_firebase_auth, auth_headers):
        """Test that episodes are sorted by timestamp (most recent first)."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock episodes with different timestamps
            mock_episodes = {
                'metadatas': [
                    {
                        "user_message": "Oldest message",
                        "ai_response": "Old response",
                        "round_number": 1,
                        "session_id": "session_1",
                        "timestamp": "2023-01-01T00:00:00",
                        "tokens": 2
                    },
                    {
                        "user_message": "Newest message",
                        "ai_response": "New response",
                        "round_number": 3,
                        "session_id": "session_1",
                        "timestamp": "2023-01-01T02:00:00",
                        "tokens": 2
                    },
                    {
                        "user_message": "Middle message",
                        "ai_response": "Middle response",
                        "round_number": 2,
                        "session_id": "session_1",
                        "timestamp": "2023-01-01T01:00:00",
                        "tokens": 2
                    }
                ],
                'ids': ['episode_1', 'episode_3', 'episode_2']
            }
            mock_collection.get.return_value = mock_episodes
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            episodes = data["episodes"]
            assert len(episodes) == 3
            
            # Should be sorted by timestamp (most recent first)
            assert episodes[0]["user_message"] == "Newest message"
            assert episodes[1]["user_message"] == "Middle message"
            assert episodes[2]["user_message"] == "Oldest message"
    
    def test_chroma_inspect_stats_structure(self, client, mock_firebase_auth, auth_headers):
        """Test that stats have the correct structure."""
        with patch('main.get_chroma_client') as mock_get_client, \
             patch('main.get_episodic_collection') as mock_get_collection, \
             patch('main.os.getenv') as mock_getenv:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            mock_getenv.return_value = "local"
            
            mock_collection.get.return_value = {'metadatas': [], 'ids': []}
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            stats = data["stats"]
            assert "total_episodes" in stats
            assert "collection_name" in stats
            assert "chroma_mode" in stats
            assert "collection_exists" in stats
            
            assert stats["total_episodes"] == 0
            assert stats["collection_name"] == "episodic_memory"
            assert stats["chroma_mode"] == "local"
            assert stats["collection_exists"] is True


class TestChromaInspectAPIRateLimiting:
    """Test rate limiting for ChromaDB inspection endpoint."""
    
    def test_chroma_inspect_rate_limited(self, client, mock_firebase_auth, auth_headers):
        """Test that ChromaDB inspection endpoint is rate limited."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            mock_collection.get.return_value = {'metadatas': [], 'ids': []}
            
            # Test GET /api/chroma/inspect (30/minute limit)
            for i in range(30):
                response = client.get("/api/chroma/inspect", headers=auth_headers)
                assert response.status_code == 200
            
            # 31st request should be rate limited
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            assert response.status_code == 429


class TestChromaInspectAPIAuthentication:
    """Test authentication requirements for ChromaDB inspection endpoint."""
    
    def test_chroma_inspect_requires_auth(self, client):
        """Test that ChromaDB inspection endpoint requires authentication."""
        response = client.get("/api/chroma/inspect")
        
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]
    
    def test_chroma_inspect_invalid_token(self, client):
        """Test ChromaDB inspection endpoint with invalid token."""
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('main.fb_auth.verify_id_token', side_effect=Exception("Invalid token")):
            response = client.get("/api/chroma/inspect", headers=invalid_headers)
            assert response.status_code == 401
            assert "Invalid ID token" in response.json()["detail"]


class TestChromaInspectAPIErrorHandling:
    """Test error handling for ChromaDB inspection endpoint."""
    
    def test_chroma_inspect_malformed_episode_data(self, client, mock_firebase_auth, auth_headers):
        """Test handling of malformed episode data."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock malformed episode data (missing fields)
            mock_episodes = {
                'metadatas': [
                    {
                        "user_message": "Hello",
                        # Missing other required fields
                    }
                ],
                'ids': ['episode_1']
            }
            mock_collection.get.return_value = mock_episodes
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should handle missing fields gracefully
            assert data["ok"] is True
            assert len(data["episodes"]) == 1
            episode = data["episodes"][0]
            assert episode["user_message"] == "Hello"
            # Missing fields should have default values
            assert episode.get("ai_response", "") == ""
            assert episode.get("round_number", 0) == 0
    
    def test_chroma_inspect_empty_metadata(self, client, mock_firebase_auth, auth_headers):
        """Test handling of empty metadata."""
        with patch('episodic_memory.get_chroma_client') as mock_get_client, \
             patch('episodic_memory.get_episodic_collection') as mock_get_collection:
            
            mock_client = Mock()
            mock_collection = Mock()
            mock_get_client.return_value = mock_client
            mock_get_collection.return_value = mock_collection
            
            # Mock empty metadata
            mock_collection.get.return_value = {'metadatas': None, 'ids': []}
            
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["ok"] is True
            assert data["episodes"] == []
            assert data["stats"]["total_episodes"] == 0
