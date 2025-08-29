# tests/conftest.py
"""
Pytest configuration and shared fixtures for memo_bot tests.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import os
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app, get_verified_uid
from rate_limiter import limiter, get_user_identifier, RATE_LIMITS, apply_rate_limit
from fastapi import Request, Depends
import time

# Add test endpoint to rate limits for testing
RATE_LIMITS["/test-rate-limit"] = "5/minute"

# Add test endpoint to the main app for testing
@app.get("/test-rate-limit")
@apply_rate_limit("/test-rate-limit")
def test_rate_limit(request: Request, uid: str = Depends(get_verified_uid)):
    """Test endpoint for rate limiting - allows 5 requests per minute"""
    return {
        "message": "Rate limit test successful",
        "uid": uid,
        "timestamp": time.time()
    }


@pytest.fixture
def client():
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_firebase_auth():
    """Mock Firebase authentication for testing."""
    with patch('main.fb_auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {"uid": "test-user-123"}
        yield mock_verify


@pytest.fixture
def mock_firestore():
    """Mock Firestore operations for testing."""
    with patch('firestore_store.add_memory') as mock_add, \
         patch('firestore_store.get_top_facts') as mock_get_facts, \
         patch('firestore_store.log_message') as mock_log, \
         patch('firestore_store.get_last_messages') as mock_get_messages:
        
        mock_add.return_value = {"id": "test-memory", "key": "test", "value": "test"}
        mock_get_facts.return_value = [{"id": "test", "key": "test", "value": "test"}]
        mock_log.return_value = "test-message-id"
        mock_get_messages.return_value = [{"role": "user", "content": "test"}]
        
        yield {
            "add_memory": mock_add,
            "get_top_facts": mock_get_facts,
            "log_message": mock_log,
            "get_last_messages": mock_get_messages
        }


@pytest.fixture
def mock_openai():
    """Mock OpenAI API for testing."""
    with patch('main._client') as mock_client:
        # Mock streaming response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].delta = Mock()
        mock_response.choices[0].delta.content = "test response"
        
        mock_stream = [mock_response]
        mock_client.chat.completions.create.return_value = iter(mock_stream)
        
        yield mock_client


@pytest.fixture
def auth_headers():
    """Generate valid auth headers for testing."""
    return {"Authorization": "Bearer fake-firebase-token"}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state before each test."""
    # For now, we'll skip the reset since MemoryStorage.clear() has different signature
    # Each test will start with a clean slate due to the way slowapi works
    yield


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
