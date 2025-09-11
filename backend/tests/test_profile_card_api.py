"""
Tests for Profile Card API endpoints.

This module tests:
- GET /api/profile-card - Retrieve user profile
- POST /api/profile-card - Update user profile  
- GET /api/profile-card/history - Get profile version history
- GET /api/profile-card/stats - Get profile statistics
"""

import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestProfileCardAPI:
    """Test Profile Card API endpoints."""
    
    def test_get_profile_card_success(self, client, mock_firebase_auth, auth_headers):
        """Test successful profile card retrieval."""
        with patch('main.get_profile_card') as mock_get_profile:
            # Mock profile card data - use a real ProfileCard structure
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=1,
                sections={
                    'demographics': {
                        'name': {'value': 'Alex', 'confidence': 0.95, 'count': 1, 'reasons': []},
                        'age': {'value': '8', 'confidence': 0.90, 'count': 1, 'reasons': []}
                    },
                    'preferences': {
                        'favorite_animals': {'triceratops': {'confidence': 0.95, 'count': 3, 'reasons': []}}
                    }
                },
                metadata={'total_facts': 3, 'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            
            response = client.get("/api/profile-card", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "profile" in data
            assert data["profile"]["version"] == 1
            assert data["profile"]["sections"]["demographics"]["name"]["value"] == "Alex"
            mock_get_profile.assert_called_once_with("test-user-123")
    
    def test_get_profile_card_error(self, client, mock_firebase_auth, auth_headers):
        """Test profile card retrieval error handling."""
        with patch('main.get_profile_card', side_effect=Exception("Database error")):
            response = client.get("/api/profile-card", headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get profile card" in data["detail"]
            assert "Database error" in data["detail"]
    
    def test_update_profile_card_success(self, client, mock_firebase_auth, auth_headers):
        """Test successful profile card update."""
        with patch('main.get_profile_card') as mock_get_profile, \
             patch('main.save_profile_card') as mock_save_profile:
            
            # Mock existing profile - use real ProfileCard structure
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=1,
                sections={
                    'demographics': {
                        'name': {'value': 'Alex', 'confidence': 0.95, 'count': 1, 'reasons': []},
                        'age': {'value': '8', 'confidence': 0.90, 'count': 1, 'reasons': []}
                    },
                    'preferences': {
                        'favorite_animals': {}
                    }
                },
                metadata={'total_facts': 2, 'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            mock_save_profile.return_value = True
            
            # Update payload
            update_payload = {
                "sections": {
                    "preferences": {
                        "favorite_animals": {
                            "stegosaurus": {"confidence": 0.90, "count": 2, "reasons": []}
                        }
                    }
                }
            }
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "profile" in data
            mock_get_profile.assert_called_once_with("test-user-123")
            mock_save_profile.assert_called_once()
    
    def test_update_profile_card_save_failure(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update when save fails."""
        with patch('main.get_profile_card') as mock_get_profile, \
             patch('main.save_profile_card') as mock_save_profile:
            
            mock_profile = Mock()
            mock_profile.sections = {}
            mock_get_profile.return_value = mock_profile
            mock_save_profile.return_value = False
            
            update_payload = {"sections": {"demographics": {"name": {"value": "Alex"}}}}
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to save profile card" in data["detail"]
    
    def test_update_profile_card_error(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update error handling."""
        with patch('main.get_profile_card', side_effect=Exception("Update error")):
            update_payload = {"sections": {"demographics": {"name": {"value": "Alex"}}}}
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to update profile card" in data["detail"]
            assert "Update error" in data["detail"]
    
    def test_get_profile_history_success(self, client, mock_firebase_auth, auth_headers):
        """Test successful profile history retrieval."""
        with patch('profile_card.get_profile_history') as mock_get_history:
            # Mock history data - use real ProfileCard structures
            from profile_card import ProfileCard
            mock_history = [
                ProfileCard(id="profile_card", user_id="test-user-123", version=3, sections={}, metadata={'updated_at': 1234567890}),
                ProfileCard(id="profile_card", user_id="test-user-123", version=2, sections={}, metadata={'updated_at': 1234567800}),
                ProfileCard(id="profile_card", user_id="test-user-123", version=1, sections={}, metadata={'updated_at': 1234567700})
            ]
            mock_get_history.return_value = mock_history
            
            response = client.get("/api/profile-card/history", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "history" in data
            assert len(data["history"]) == 3
            assert data["history"][0]["version"] == 3
            mock_get_history.assert_called_once_with("test-user-123", 10)
    
    def test_get_profile_history_with_limit(self, client, mock_firebase_auth, auth_headers):
        """Test profile history retrieval with custom limit."""
        with patch('profile_card.get_profile_history') as mock_get_history:
            mock_get_history.return_value = []
            
            response = client.get("/api/profile-card/history?limit=5", headers=auth_headers)
            
            assert response.status_code == 200
            mock_get_history.assert_called_once_with("test-user-123", 5)
    
    def test_get_profile_history_error(self, client, mock_firebase_auth, auth_headers):
        """Test profile history retrieval error handling."""
        with patch('profile_card.get_profile_history', side_effect=Exception("History error")):
            response = client.get("/api/profile-card/history", headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get profile history" in data["detail"]
            assert "History error" in data["detail"]
    
    def test_get_profile_stats_success(self, client, mock_firebase_auth, auth_headers):
        """Test successful profile statistics retrieval."""
        with patch('main.get_profile_card') as mock_get_profile, \
             patch('profile_card.count_total_facts') as mock_count_facts, \
             patch('profile_card.calculate_tokens') as mock_calculate_tokens:
            
            # Mock profile data - use real ProfileCard structure
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=2,
                sections={
                    'demographics': {'name': {'value': 'Alex'}, 'age': {'value': '8'}},
                    'preferences': {'favorite_animals': {'triceratops': {}}}
                },
                metadata={'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            mock_count_facts.return_value = 3
            mock_calculate_tokens.return_value = 150
            
            response = client.get("/api/profile-card/stats", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert "stats" in data
            
            stats = data["stats"]
            assert stats["total_facts"] == 3
            assert stats["tokens"] == 150
            assert stats["version"] == 2
            assert stats["last_updated"] == 1234567890
            assert "sections" in stats
            assert stats["sections"]["demographics"] == 2
            assert stats["sections"]["preferences"] == 1
            
            mock_get_profile.assert_called_once_with("test-user-123")
            mock_count_facts.assert_called_once_with(mock_profile)
            mock_calculate_tokens.assert_called_once_with(mock_profile)
    
    def test_get_profile_stats_error(self, client, mock_firebase_auth, auth_headers):
        """Test profile statistics retrieval error handling."""
        with patch('main.get_profile_card', side_effect=Exception("Stats error")):
            response = client.get("/api/profile-card/stats", headers=auth_headers)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get profile stats" in data["detail"]
            assert "Stats error" in data["detail"]


class TestProfileCardAPIRateLimiting:
    """Test rate limiting for Profile Card API endpoints."""
    
    def test_profile_card_endpoints_rate_limited(self, client, mock_firebase_auth, auth_headers):
        """Test that profile card endpoints are rate limited."""
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
            
            # Test GET /api/profile-card (20/minute limit)
            for i in range(20):
                response = client.get("/api/profile-card", headers=auth_headers)
                assert response.status_code == 200
            
            # 21st request should be rate limited
            response = client.get("/api/profile-card", headers=auth_headers)
            assert response.status_code == 429
    
    def test_profile_card_history_rate_limited(self, client, mock_firebase_auth, auth_headers):
        """Test that profile history endpoint is rate limited."""
        with patch('profile_card.get_profile_history') as mock_get_history:
            mock_get_history.return_value = []
            
            # Test GET /api/profile-card/history (10/minute limit)
            for i in range(10):
                response = client.get("/api/profile-card/history", headers=auth_headers)
                assert response.status_code == 200
            
            # 11th request should be rate limited
            response = client.get("/api/profile-card/history", headers=auth_headers)
            assert response.status_code == 429


class TestProfileCardAPIAuthentication:
    """Test authentication requirements for Profile Card API endpoints."""
    
    def test_profile_card_endpoints_require_auth(self, client):
        """Test that all profile card endpoints require authentication."""
        endpoints = [
            ("GET", "/api/profile-card"),
            ("POST", "/api/profile-card"),
            ("GET", "/api/profile-card/history"),
            ("GET", "/api/profile-card/stats")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            assert response.status_code == 401
            assert "Missing bearer token" in response.json()["detail"]
    
    def test_profile_card_endpoints_invalid_token(self, client):
        """Test profile card endpoints with invalid token."""
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        
        with patch('main.fb_auth.verify_id_token', side_effect=Exception("Invalid token")):
            response = client.get("/api/profile-card", headers=invalid_headers)
            assert response.status_code == 401
            assert "Invalid ID token" in response.json()["detail"]


class TestProfileCardAPIValidation:
    """Test input validation for Profile Card API endpoints."""
    
    def test_update_profile_card_invalid_payload(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update with invalid payload."""
        with patch('main.get_profile_card') as mock_get_profile:
            from profile_card import ProfileCard
            mock_profile = ProfileCard(
                id="profile_card",
                user_id="test-user-123",
                version=1,
                sections={},
                metadata={'total_facts': 0, 'updated_at': 1234567890}
            )
            mock_get_profile.return_value = mock_profile
            
            # Test with invalid JSON
            response = client.post("/api/profile-card", 
                                 data="invalid json", 
                                 headers={**auth_headers, "Content-Type": "application/json"})
            
            assert response.status_code == 422  # Validation error
    
    def test_update_profile_card_empty_sections(self, client, mock_firebase_auth, auth_headers):
        """Test profile card update with empty sections."""
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
            
            # Empty sections should still work
            update_payload = {"sections": {}}
            
            response = client.post("/api/profile-card", json=update_payload, headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
    
    def test_profile_history_invalid_limit(self, client, mock_firebase_auth, auth_headers):
        """Test profile history with invalid limit parameter."""
        with patch('profile_card.get_profile_history') as mock_get_history:
            mock_get_history.return_value = []
            
            # Test with negative limit
            response = client.get("/api/profile-card/history?limit=-1", headers=auth_headers)
            
            # Should still work, but limit will be handled by the function
            assert response.status_code == 200
            mock_get_history.assert_called_once_with("test-user-123", -1)
