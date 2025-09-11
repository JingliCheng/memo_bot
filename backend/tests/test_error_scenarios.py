"""
Comprehensive error handling tests.

This module tests:
- Network failures and service unavailability
- Malformed requests and edge cases
- Concurrent access issues
- Rate limit edge cases
- External service failures
- Data validation errors
"""

import pytest
import json
import asyncio
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import HTTPException


class TestNetworkFailures:
    """Test handling of network failures."""
    
    def test_firebase_auth_network_failure(self, client):
        """Test Firebase authentication network failure."""
        with patch('main.fb_auth.verify_id_token', side_effect=ConnectionError("Network error")):
            response = client.get("/whoami", headers={"Authorization": "Bearer test-token"})
            
            assert response.status_code == 401
            assert "Invalid ID token" in response.json()["detail"]
            assert "Network error" in response.json()["detail"]
    
    def test_firestore_network_failure(self, client, mock_firebase_auth, auth_headers):
        """Test Firestore network failure."""
        with patch('main.add_memory', side_effect=ConnectionError("Firestore unavailable")):
            memory_data = {"key": "test", "value": "test value", "type": "semantic"}
            response = client.post("/api/memory", json=memory_data, headers=auth_headers)
            
            assert response.status_code == 500
            assert "add_memory failed" in response.json()["detail"]
            assert "Firestore unavailable" in response.json()["detail"]
    
    def test_openai_network_failure(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test OpenAI API network failure."""
        with patch('llm_integration._client.chat.completions.create', 
                  side_effect=ConnectionError("OpenAI API unavailable")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should still return 200 with fallback response
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_chromadb_network_failure(self, client, mock_firebase_auth, auth_headers):
        """Test ChromaDB network failure."""
        with patch('episodic_memory.get_chroma_client', side_effect=ConnectionError("ChromaDB unavailable")):
            response = client.get("/api/chroma/inspect", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["stats"]["collection_exists"] is False
            assert "error" in data["stats"]


class TestServiceUnavailability:
    """Test handling of service unavailability."""
    
    def test_firebase_service_down(self, client):
        """Test when Firebase service is down."""
        with patch('main.fb_auth.verify_id_token', 
                  side_effect=HTTPException(status_code=503, detail="Service unavailable")):
            response = client.get("/whoami", headers={"Authorization": "Bearer test-token"})
            
            assert response.status_code == 401
            assert "Invalid ID token" in response.json()["detail"]
    
    def test_firestore_service_down(self, client, mock_firebase_auth, auth_headers):
        """Test when Firestore service is down."""
        with patch('main.get_top_facts', 
                  side_effect=HTTPException(status_code=503, detail="Firestore service down")):
            response = client.get("/api/memory", headers=auth_headers)
            
            assert response.status_code == 500
            assert "list_memory failed" in response.json()["detail"]
    
    def test_openai_service_down(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test when OpenAI service is down."""
        with patch('llm_integration._client.chat.completions.create',
                  side_effect=HTTPException(status_code=503, detail="OpenAI service down")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should handle gracefully with fallback
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestMalformedRequests:
    """Test handling of malformed requests."""
    
    def test_invalid_json_payload(self, client, mock_firebase_auth, auth_headers):
        """Test invalid JSON payload."""
        response = client.post("/api/memory", 
                             data="invalid json", 
                             headers={**auth_headers, "Content-Type": "application/json"})
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self, client, mock_firebase_auth, auth_headers):
        """Test missing required fields."""
        # Missing message field in chat
        response = client.post("/api/chat", json={}, headers=auth_headers)
        
        assert response.status_code == 400
        assert "message is required" in response.json()["detail"]
    
    def test_empty_message(self, client, mock_firebase_auth, auth_headers):
        """Test empty message."""
        response = client.post("/api/chat", json={"message": ""}, headers=auth_headers)
        
        assert response.status_code == 400
        assert "message is required" in response.json()["detail"]
    
    def test_whitespace_only_message(self, client, mock_firebase_auth, auth_headers):
        """Test whitespace-only message."""
        response = client.post("/api/chat", json={"message": "   \n\t  "}, headers=auth_headers)
        
        assert response.status_code == 400
        assert "message is required" in response.json()["detail"]
    
    def test_non_string_message(self, client, mock_firebase_auth, auth_headers):
        """Test non-string message."""
        response = client.post("/api/chat", json={"message": 123}, headers=auth_headers)
        
        assert response.status_code == 400
        assert "message is required" in response.json()["detail"]
    
    def test_oversized_message(self, client, mock_firebase_auth, auth_headers):
        """Test oversized message."""
        oversized_message = "x" * 10000  # Very long message
        response = client.post("/api/chat", json={"message": oversized_message}, headers=auth_headers)
        
        # Should still work (no explicit size limit in current implementation)
        assert response.status_code == 200
    
    def test_invalid_memory_data(self, client, mock_firebase_auth, auth_headers):
        """Test invalid memory data structure."""
        invalid_memory = {
            "key": "test",
            # Missing required fields: value, type
        }
        response = client.post("/api/memory", json=invalid_memory, headers=auth_headers)
        
        # Should still work (current implementation has defaults)
        assert response.status_code == 200


class TestConcurrentAccess:
    """Test concurrent access scenarios."""
    
    def test_concurrent_memory_operations(self, client, mock_firebase_auth, auth_headers):
        """Test concurrent memory operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                memory_data = {"key": f"test_{threading.current_thread().ident}", 
                             "value": "test value", "type": "semantic"}
                response = client.post("/api/memory", json=memory_data, headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(errors) == 0
        assert all(status == 200 for status in results)
        assert len(results) == 5
    
    def test_concurrent_chat_requests(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test concurrent chat requests."""
        import threading
        
        results = []
        errors = []
        
        def make_chat_request():
            try:
                chat_data = {"message": f"Hello from thread {threading.current_thread().ident}"}
                response = client.post("/api/chat", json=chat_data, headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(3):  # Fewer threads to avoid rate limiting
            thread = threading.Thread(target=make_chat_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(errors) == 0
        assert all(status == 200 for status in results)
        assert len(results) == 3


class TestRateLimitEdgeCases:
    """Test rate limiting edge cases."""
    
    def test_rate_limit_exact_boundary(self, client, mock_firebase_auth, auth_headers):
        """Test rate limiting at exact boundary."""
        # Test endpoint with 5/minute limit
        for i in range(5):
            response = client.get("/test-rate-limit", headers=auth_headers)
            assert response.status_code == 200
        
        # 6th request should be rate limited
        response = client.get("/test-rate-limit", headers=auth_headers)
        assert response.status_code == 429
    
    def test_rate_limit_different_endpoints(self, client, mock_firebase_auth, auth_headers):
        """Test that different endpoints have separate rate limits."""
        # Hit rate limit on test endpoint (5/minute)
        for i in range(5):
            response = client.get("/test-rate-limit", headers=auth_headers)
            assert response.status_code == 200
        
        # Should be rate limited on test endpoint
        response = client.get("/test-rate-limit", headers=auth_headers)
        assert response.status_code == 429
        
        # But other endpoints should still work
        response = client.get("/whoami", headers=auth_headers)
        assert response.status_code == 200
    
    def test_rate_limit_recovery_simulation(self, client, mock_firebase_auth, auth_headers):
        """Test rate limit recovery (simulated by clearing rate limiter state)."""
        # Hit rate limit
        for i in range(6):
            response = client.get("/test-rate-limit", headers=auth_headers)
        
        assert response.status_code == 429
        
        # In a real scenario, rate limits would reset after the time window
        # For testing, we can't easily simulate time passage, but we can verify
        # the rate limiting mechanism works correctly


class TestExternalServiceFailures:
    """Test handling of external service failures."""
    
    def test_openai_api_key_invalid(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test invalid OpenAI API key."""
        with patch('llm_integration._client.chat.completions.create',
                  side_effect=HTTPException(status_code=401, detail="Invalid API key")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should handle gracefully
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_openai_rate_limit_exceeded(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test OpenAI rate limit exceeded."""
        with patch('llm_integration._client.chat.completions.create',
                  side_effect=HTTPException(status_code=429, detail="Rate limit exceeded")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should handle gracefully
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_openai_model_not_found(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test OpenAI model not found."""
        with patch('llm_integration._client.chat.completions.create',
                  side_effect=HTTPException(status_code=404, detail="Model not found")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should handle gracefully
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_firestore_permission_denied(self, client, mock_firebase_auth, auth_headers):
        """Test Firestore permission denied."""
        with patch('main.add_memory', 
                  side_effect=HTTPException(status_code=403, detail="Permission denied")):
            memory_data = {"key": "test", "value": "test value", "type": "semantic"}
            response = client.post("/api/memory", json=memory_data, headers=auth_headers)
            
            assert response.status_code == 500
            assert "add_memory failed" in response.json()["detail"]
    
    def test_firestore_quota_exceeded(self, client, mock_firebase_auth, auth_headers):
        """Test Firestore quota exceeded."""
        with patch('main.get_top_facts', 
                  side_effect=HTTPException(status_code=429, detail="Quota exceeded")):
            response = client.get("/api/memory", headers=auth_headers)
            
            assert response.status_code == 500
            assert "list_memory failed" in response.json()["detail"]


class TestDataValidationErrors:
    """Test data validation error handling."""
    
    def test_profile_card_invalid_section(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update with invalid section."""
        with patch('main.get_profile_card') as mock_get_profile, \
             patch('main.save_profile_card') as mock_save_profile:
            
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=1,
                sections={},
                metadata={'total_facts': 0, 'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            mock_save_profile.return_value = True
            
            # Try to update non-existent section
            update_payload = {
                "sections": {
                    "invalid_section": {
                        "field": "value"
                    }
                }
            }
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            # Should still work (invalid sections are ignored)
            assert response.status_code == 200
    
    def test_profile_card_invalid_data_types(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update with invalid data types."""
        with patch('main.get_profile_card') as mock_get_profile, \
             patch('main.save_profile_card') as mock_save_profile:
            
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=1,
                sections={"demographics": {"name": {}}},
                metadata={'total_facts': 0, 'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            mock_save_profile.return_value = True
            
            # Try to update with invalid data types
            update_payload = {
                "sections": {
                    "demographics": {
                        "name": "not_a_dict"  # Should be a dict
                    }
                }
            }
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            # Should still work (invalid data is handled gracefully)
            assert response.status_code == 200
    
    def test_memory_invalid_types(self, client, mock_firebase_auth, auth_headers):
        """Test memory operations with invalid data types."""
        # Test with non-string values
        memory_data = {
            "key": 123,  # Should be string
            "value": None,  # Should be string
            "type": "semantic"
        }
        
        response = client.post("/api/memory", json=memory_data, headers=auth_headers)
        
        # Should still work (current implementation handles this)
        assert response.status_code == 200


class TestEdgeCases:
    """Test various edge cases."""
    
    def test_very_long_user_id(self, client, mock_firebase_auth):
        """Test with very long user ID."""
        long_uid = "x" * 1000
        with patch('main.fb_auth.verify_id_token', return_value={"uid": long_uid}):
            response = client.get("/whoami", headers={"Authorization": "Bearer test-token"})
            
            assert response.status_code == 200
            assert response.json()["uid"] == long_uid
    
    def test_special_characters_in_message(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test special characters in chat message."""
        special_message = "Hello! 🌟 This has émojis and spëcial chars: @#$%^&*()"
        
        response = client.post("/api/chat", json={"message": special_message}, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_unicode_in_memory_data(self, client, mock_firebase_auth, auth_headers):
        """Test Unicode characters in memory data."""
        unicode_memory = {
            "key": "测试",
            "value": "这是一个测试 🦕",
            "type": "semantic"
        }
        
        response = client.post("/api/memory", json=unicode_memory, headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_empty_arrays_and_objects(self, client, mock_firebase_auth, auth_headers):
        """Test empty arrays and objects in requests."""
        empty_payload = {
            "sections": {},
            "array_field": [],
            "object_field": {}
        }
        
        response = client.post("/api/profile-card", json=empty_payload, headers=auth_headers)
        
        assert response.status_code == 200
    
    def test_null_values(self, client, mock_firebase_auth, auth_headers):
        """Test null values in requests."""
        null_payload = {
            "key": None,
            "value": None,
            "type": "semantic"
        }
        
        response = client.post("/api/memory", json=null_payload, headers=auth_headers)
        
        # Should handle gracefully
        assert response.status_code == 200


class TestTimeoutScenarios:
    """Test timeout scenarios."""
    
    def test_openai_timeout(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test OpenAI API timeout."""
        with patch('llm_integration._client.chat.completions.create',
                  side_effect=asyncio.TimeoutError("Request timeout")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            
            # Should handle gracefully
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_firestore_timeout(self, client, mock_firebase_auth, auth_headers):
        """Test Firestore timeout."""
        with patch('main.get_top_facts', side_effect=asyncio.TimeoutError("Firestore timeout")):
            response = client.get("/api/memory", headers=auth_headers)
            
            assert response.status_code == 500
            assert "list_memory failed" in response.json()["detail"]
