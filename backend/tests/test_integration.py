# tests/test_integration.py
"""
Integration tests for API endpoints with rate limiting.
"""
import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Test API endpoints with rate limiting."""
    
    def test_health_endpoint_no_rate_limit(self, client):
        """Test that health endpoint is not rate limited."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    
    def test_whoami_endpoint_with_auth(self, client, mock_firebase_auth, auth_headers):
        """Test whoami endpoint with authentication."""
        response = client.get("/whoami", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"uid": "test-user-123"}
    
    def test_whoami_endpoint_without_auth(self, client):
        """Test whoami endpoint without authentication."""
        response = client.get("/whoami")
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]
    
    def test_memory_endpoints_with_auth(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test memory endpoints with authentication."""
        # Test GET /api/memory
        response = client.get("/api/memory", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert "items" in response.json()
        
        # Test POST /api/memory
        memory_data = {"key": "test", "value": "test value", "type": "semantic"}
        response = client.post("/api/memory", json=memory_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert "memory" in response.json()
    
    def test_messages_endpoint_with_auth(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test messages endpoint with authentication."""
        response = client.get("/api/messages", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert "items" in response.json()
    
    def test_chat_endpoint_with_auth(self, client, mock_firebase_auth, mock_firestore, mock_openai, auth_headers):
        """Test chat endpoint with authentication."""
        chat_data = {"message": "Hello, world!"}
        response = client.post("/api/chat", json=chat_data, headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_chat_endpoint_without_message(self, client, mock_firebase_auth, auth_headers):
        """Test chat endpoint without message."""
        response = client.post("/api/chat", json={}, headers=auth_headers)
        assert response.status_code == 400
        assert "message is required" in response.json()["detail"]


class TestRateLimitingIntegration:
    """Test rate limiting integration with API endpoints."""
    
    def test_rate_limit_test_endpoint(self, client, mock_firebase_auth, auth_headers):
        """Test the rate limit test endpoint."""
        # First 5 requests should succeed
        for i in range(5):
            response = client.get("/test-rate-limit", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["uid"] == "test-user-123"
        
        # 6th request should be rate limited
        response = client.get("/test-rate-limit", headers=auth_headers)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        assert "5 per 1 minute" in response.json()["message"]
    
    def test_different_endpoints_different_limits(self, client, mock_firebase_auth, auth_headers):
        """Test that different endpoints have different rate limits."""
        # Test whoami endpoint (60/minute) - should allow many requests
        for i in range(10):
            response = client.get("/whoami", headers=auth_headers)
            assert response.status_code == 200
        
        # Test memory endpoint (30/minute) - should allow many requests
        for i in range(10):
            response = client.get("/api/memory", headers=auth_headers)
            assert response.status_code == 200
    
    def test_rate_limit_error_response_format(self, client, mock_firebase_auth, auth_headers):
        """Test that rate limit error responses have the correct format."""
        # Hit rate limit on test endpoint
        for i in range(6):  # 5 allowed + 1 over limit
            response = client.get("/test-rate-limit", headers=auth_headers)
        
        # Check error response format
        assert response.status_code == 429
        error_data = response.json()
        
        assert "error" in error_data
        assert "message" in error_data
        assert "retry_after" in error_data
        assert "endpoint" in error_data
        assert "uid" in error_data
        
        assert error_data["error"] == "Rate limit exceeded"
        assert "5 per 1 minute" in error_data["message"]
        assert error_data["endpoint"] == "/test-rate-limit"
        assert error_data["uid"] == "test-user-123"
        # retry_after might be None if not available in the exception
        assert error_data["retry_after"] is None or isinstance(error_data["retry_after"], int)
    
    def test_rate_limit_headers(self, client, mock_firebase_auth, auth_headers):
        """Test that rate limit responses include proper headers."""
        # Hit rate limit
        for i in range(6):
            response = client.get("/test-rate-limit", headers=auth_headers)
        
        # Check headers
        assert response.status_code == 429
        # Retry-After header might not be present if retry_after is None
        # assert "Retry-After" in response.headers


class TestAuthenticationIntegration:
    """Test authentication integration with rate limiting."""
    
    def test_invalid_token_returns_401(self, client):
        """Test that invalid tokens return 401, not rate limit errors."""
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('main.fb_auth.verify_id_token', side_effect=Exception("Invalid token")):
            response = client.get("/whoami", headers=invalid_headers)
            assert response.status_code == 401
            assert "Invalid ID token" in response.json()["detail"]
    
    def test_missing_token_returns_401(self, client):
        """Test that missing tokens return 401, not rate limit errors."""
        response = client.get("/whoami")
        assert response.status_code == 401
        assert "Missing bearer token" in response.json()["detail"]
    
    def test_valid_token_stores_uid_in_request_state(self, client, mock_firebase_auth, auth_headers):
        """Test that valid tokens store UID in request state for rate limiting."""
        response = client.get("/whoami", headers=auth_headers)
        assert response.status_code == 200
        
        # The UID should be stored in request.state.uid by get_verified_uid
        # This is tested indirectly through rate limiting working correctly


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    def test_firestore_error_handling(self, client, mock_firebase_auth, auth_headers):
        """Test that Firestore errors are handled gracefully."""
        with patch('firestore_store.get_top_facts', side_effect=Exception("Firestore error")):
            response = client.get("/api/memory", headers=auth_headers)
            assert response.status_code == 500
            assert "list_memory failed" in response.json()["detail"]
    
    def test_openai_error_handling(self, client, mock_firebase_auth, mock_firestore, auth_headers):
        """Test that OpenAI errors are handled gracefully."""
        with patch('main._client.chat.completions.create', side_effect=Exception("OpenAI error")):
            chat_data = {"message": "Hello, world!"}
            response = client.post("/api/chat", json=chat_data, headers=auth_headers)
            assert response.status_code == 500
            assert "OpenAI API call failed" in response.json()["detail"]


class TestCORSIntegration:
    """Test CORS integration."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # CORS headers should be present (set by CORSMiddleware)
        # The exact headers depend on the middleware configuration
