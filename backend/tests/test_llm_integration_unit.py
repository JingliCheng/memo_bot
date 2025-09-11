"""
Unit tests for LLM integration functionality.

This module tests:
- Streaming response handling
- Function calling for profile updates
- Context injection logic
- Background profile processing
- Error handling and fallbacks
- Message formatting
"""

import pytest
import json
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from fastapi.responses import StreamingResponse

from llm_integration import (
    format_llm_messages,
    format_profile_for_llm,
    get_episode_context,
    get_profile_update_function_definition,
    stream_llm_response,
    handle_profile_updates_background,
    log_profile_update,
    chat_with_streaming_profile_update,
    simple_streaming_chat
)


class TestMessageFormatting:
    """Test LLM message formatting."""
    
    def test_format_profile_for_llm(self):
        """Test formatting profile for LLM context."""
        from profile_card import ProfileCard
        
        # Create mock profile
        profile = Mock(spec=ProfileCard)
        profile.sections = {
            'demographics': {
                'name': {'value': 'Alex', 'confidence': 0.95, 'count': 1, 'reasons': []},
                'age': {'value': '8', 'confidence': 0.90, 'count': 1, 'reasons': []},
                'location': {'value': 'Seattle', 'confidence': 0.85, 'count': 1, 'reasons': []}
            },
            'interests': {
                'primary_interests': {'dinosaurs': {'confidence': 0.95, 'count': 3, 'reasons': []}}
            },
            'preferences': {
                'favorite_animals': {'triceratops': {'confidence': 0.95, 'count': 3, 'reasons': []}},
                'favorite_foods': {'pizza': {'confidence': 0.90, 'count': 2, 'reasons': []}},
                'favorite_colors': {'blue': {'confidence': 0.85, 'count': 1, 'reasons': []}}
            },
            'constraints': {
                'safety_limits': {'no_scary_content': {'confidence': 0.95, 'count': 1, 'reasons': []}},
                'schedule_limits': {},
                'health_limits': {}
            },
            'goals': {
                'learning_goals': {'paleontology': {'confidence': 0.90, 'count': 2, 'reasons': []}},
                'personal_goals': {}
            },
            'context': {
                'recent_events': {'birthday_party': {'confidence': 0.95, 'count': 1, 'reasons': []}},
                'current_projects': {}
            },
            'communication': {
                'style': {'value': 'playful', 'confidence': 0.90, 'count': 1, 'reasons': []},
                'learning_level': {'value': 'beginner', 'confidence': 0.85, 'count': 1, 'reasons': []},
                'attention_span': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'language_preference': {'value': 'English', 'confidence': 0.95, 'count': 1, 'reasons': []}
            }
        }
        
        formatted = format_profile_for_llm(profile)
        
        assert "Alex" in formatted
        assert "8" in formatted
        assert "Seattle" in formatted
        assert "dinosaurs" in formatted
        assert "triceratops" in formatted
        assert "pizza" in formatted
        assert "blue" in formatted
        assert "no_scary_content" in formatted
        assert "paleontology" in formatted
        assert "birthday_party" in formatted
        assert "playful" in formatted
        assert "beginner" in formatted
        assert "User Profile:" in formatted
    
    def test_format_profile_for_llm_empty_profile(self):
        """Test formatting empty profile for LLM context."""
        from profile_card import ProfileCard
        
        # Create empty profile
        profile = Mock(spec=ProfileCard)
        profile.sections = {
            'demographics': {
                'name': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'age': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'location': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []}
            },
            'interests': {'primary_interests': {}},
            'preferences': {
                'favorite_animals': {},
                'favorite_foods': {},
                'favorite_colors': {}
            },
            'constraints': {
                'safety_limits': {},
                'schedule_limits': {},
                'health_limits': {}
            },
            'goals': {
                'learning_goals': {},
                'personal_goals': {}
            },
            'context': {
                'recent_events': {},
                'current_projects': {}
            },
            'communication': {
                'style': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'learning_level': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'attention_span': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []},
                'language_preference': {'value': 'English', 'confidence': 0.95, 'count': 1, 'reasons': []}
            }
        }
        
        formatted = format_profile_for_llm(profile)
        
        assert "User Profile:" in formatted
        assert "English" in formatted  # Default language preference
        # Should handle empty values gracefully
    
    @patch('llm_integration.search_user_episodes')
    @patch('llm_integration.get_user_recent_episodes')
    def test_get_episode_context_with_relevant_episodes(self, mock_get_recent, mock_search):
        """Test getting episode context with relevant episodes."""
        mock_search.return_value = [
            {
                "user_message": "I love dinosaurs",
                "ai_response": "That's wonderful!",
                "round_number": 1,
                "session_id": "session_1",
                "timestamp": "2023-01-01T00:00:00",
                "tokens": 5
            }
        ]
        mock_get_recent.return_value = []
        
        context = get_episode_context("test_user", "Tell me about dinosaurs")
        
        assert "Recent Relevant Conversations" in context
        assert "I love dinosaurs" in context
        assert "That's wonderful!" in context
        assert "Round 1" in context
        mock_search.assert_called_once_with("test_user", "Tell me about dinosaurs", limit=3)
    
    @patch('llm_integration.search_user_episodes')
    @patch('llm_integration.get_user_recent_episodes')
    def test_get_episode_context_fallback_to_recent(self, mock_get_recent, mock_search):
        """Test episode context fallback to recent episodes."""
        mock_search.return_value = []  # No relevant episodes
        mock_get_recent.return_value = [
            {
                "user_message": "Hello there",
                "ai_response": "Hi!",
                "round_number": 2,
                "session_id": "session_1",
                "timestamp": "2023-01-01T00:01:00",
                "tokens": 3
            }
        ]
        
        context = get_episode_context("test_user", "Tell me about dinosaurs")
        
        assert "Recent Relevant Conversations" in context
        assert "Hello there" in context
        assert "Hi!" in context
        assert "Round 2" in context
        mock_search.assert_called_once()
        mock_get_recent.assert_called_once_with("test_user", limit=3)
    
    @patch('llm_integration.search_user_episodes')
    @patch('llm_integration.get_user_recent_episodes')
    def test_get_episode_context_no_episodes(self, mock_get_recent, mock_search):
        """Test episode context with no episodes available."""
        mock_search.return_value = []
        mock_get_recent.return_value = []
        
        context = get_episode_context("test_user", "Tell me about dinosaurs")
        
        assert context == ""
        mock_search.assert_called_once()
        mock_get_recent.assert_called_once()
    
    @patch('llm_integration.search_user_episodes')
    def test_get_episode_context_error(self, mock_search):
        """Test episode context error handling."""
        mock_search.side_effect = Exception("Search error")
        
        context = get_episode_context("test_user", "Tell me about dinosaurs")
        
        assert context == ""
    
    def test_format_llm_messages(self):
        """Test formatting messages for LLM."""
        from profile_card import ProfileCard
        
        # Mock profile
        profile = Mock(spec=ProfileCard)
        profile.sections = {
            'demographics': {'name': {'value': 'Alex'}},
            'interests': {'primary_interests': {}},
            'preferences': {'favorite_animals': {}},
            'constraints': {'safety_limits': {}},
            'goals': {'learning_goals': {}},
            'context': {'recent_events': {}},
            'communication': {'style': {'value': 'playful'}, 'learning_level': {'value': 'beginner'}}
        }
        
        with patch('llm_integration.format_profile_for_llm') as mock_format_profile, \
             patch('llm_integration.get_episode_context') as mock_get_context, \
             patch('llm_integration.get_last_messages') as mock_get_messages:
            
            mock_format_profile.return_value = "User Profile: Alex"
            mock_get_context.return_value = "Episode context"
            mock_get_messages.return_value = [
                {"role": "user", "content": "Previous message"},
                {"role": "assistant", "content": "Previous response"}
            ]
            
            messages = format_llm_messages("test_user", "Hello world", profile)
            
            assert len(messages) == 4  # system + 2 history + current
            assert messages[0]["role"] == "system"
            assert "Roary" in messages[0]["content"]
            assert "User Profile: Alex" in messages[0]["content"]
            assert "Episode context" in messages[0]["content"]
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "Previous message"
            assert messages[2]["role"] == "assistant"
            assert messages[2]["content"] == "Previous response"
            assert messages[3]["role"] == "user"
            assert messages[3]["content"] == "Hello world"


class TestFunctionCalling:
    """Test function calling functionality."""
    
    def test_get_profile_update_function_definition(self):
        """Test profile update function definition."""
        func_def = get_profile_update_function_definition()
        
        assert func_def["name"] == "profile_update"
        assert "description" in func_def
        assert "parameters" in func_def
        
        params = func_def["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "updates" in params["properties"]
        
        updates_prop = params["properties"]["updates"]
        assert updates_prop["type"] == "array"
        assert "items" in updates_prop
        
        item_props = updates_prop["items"]["properties"]
        required_fields = ["section", "field", "value", "confidence", "reason"]
        for field in required_fields:
            assert field in item_props
        
        assert "required" in updates_prop["items"]
        assert all(field in updates_prop["items"]["required"] for field in required_fields)


class TestStreamingResponse:
    """Test streaming response handling."""
    
    @patch('llm_integration._use_openai', False)
    @pytest.mark.asyncio
    async def test_stream_llm_response_no_openai(self):
        """Test streaming response without OpenAI."""
        messages = [{"role": "user", "content": "Hello"}]
        
        chunks = []
        async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
            chunks.append((chunk, profile_updates_json, raw_chunk))
        
        assert len(chunks) == 1
        chunk, profile_updates_json, raw_chunk = chunks[0]
        assert "don't have access to OpenAI API" in chunk
        assert profile_updates_json == '{"updates": []}'
    
    @patch('llm_integration._client')
    @pytest.mark.asyncio
    async def test_stream_llm_response_success(self, mock_client):
        """Test successful streaming response."""
        # Mock streaming response
        mock_response1 = Mock()
        mock_response1.choices = [Mock()]
        mock_response1.choices[0].delta = Mock()
        mock_response1.choices[0].delta.content = "Hello"
        mock_response1.choices[0].finish_reason = None
        
        mock_response2 = Mock()
        mock_response2.choices = [Mock()]
        mock_response2.choices[0].delta = Mock()
        mock_response2.choices[0].delta.content = " there!"
        mock_response2.choices[0].finish_reason = None
        
        mock_response3 = Mock()
        mock_response3.choices = [Mock()]
        mock_response3.choices[0].delta = Mock()
        mock_response3.choices[0].delta = None
        mock_response3.choices[0].finish_reason = "stop"
        
        mock_client.chat.completions.create.return_value = iter([mock_response1, mock_response2, mock_response3])
        
        messages = [{"role": "user", "content": "Hello"}]
        
        chunks = []
        async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
            chunks.append((chunk, profile_updates_json, raw_chunk))
        
        assert len(chunks) == 3
        assert chunks[0][0] == "Hello"
        assert chunks[1][0] == " there!"
        assert chunks[2][0] == ""  # Final chunk
        assert chunks[2][1] == '{"updates": []}'  # No profile updates
    
    @patch('llm_integration._client')
    @pytest.mark.asyncio
    async def test_stream_llm_response_with_function_call(self, mock_client):
        """Test streaming response with function call."""
        # Mock streaming response with function call
        mock_response1 = Mock()
        mock_response1.choices = [Mock()]
        mock_response1.choices[0].delta = Mock()
        mock_response1.choices[0].delta.content = "Thanks for sharing!"
        mock_response1.choices[0].finish_reason = None
        
        mock_response2 = Mock()
        mock_response2.choices = [Mock()]
        mock_response2.choices[0].delta = Mock()
        mock_response2.choices[0].delta.content = None
        mock_response2.choices[0].delta.function_call = Mock()
        mock_response2.choices[0].delta.function_call.arguments = '{"updates": [{"section": "demographics", "field": "name", "value": "Alex", "confidence": 0.95, "reason": "User stated name"}]}'
        mock_response2.choices[0].finish_reason = "function_call"
        
        mock_client.chat.completions.create.return_value = iter([mock_response1, mock_response2])
        
        messages = [{"role": "user", "content": "My name is Alex"}]
        
        chunks = []
        async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
            chunks.append((chunk, profile_updates_json, raw_chunk))
        
        assert len(chunks) == 2
        assert chunks[0][0] == "Thanks for sharing!"
        assert chunks[1][0] == ""  # Final chunk
        assert chunks[1][1] == '{"updates": [{"section": "demographics", "field": "name", "value": "Alex", "confidence": 0.95, "reason": "User stated name"}]}'
    
    @patch('llm_integration._client')
    @pytest.mark.asyncio
    async def test_stream_llm_response_error(self, mock_client):
        """Test streaming response error handling."""
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        chunks = []
        async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
            chunks.append((chunk, profile_updates_json, raw_chunk))
        
        assert len(chunks) == 1
        assert "error processing your request" in chunks[0][0]
        assert chunks[0][1] == '{"updates": []}'


class TestBackgroundProfileProcessing:
    """Test background profile processing."""
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_success(self):
        """Test successful background profile processing."""
        from profile_card import ProfileCard
        
        # Mock profile
        profile = Mock(spec=ProfileCard)
        profile.sections = {
            'demographics': {'name': {'value': '', 'confidence': 0.0, 'count': 0, 'reasons': []}}
        }
        
        profile_updates = {
            "updates": [
                {
                    "section": "demographics",
                    "field": "name",
                    "value": "Alex",
                    "confidence": 0.95,
                    "reason": "User stated name"
                }
            ]
        }
        
        with patch('llm_integration.validate_updates') as mock_validate, \
             patch('llm_integration.update_profile_with_confidence') as mock_update, \
             patch('llm_integration.save_profile_card') as mock_save, \
             patch('llm_integration.log_profile_update') as mock_log:
            
            mock_validate.return_value = profile_updates["updates"]
            mock_update.return_value = profile
            mock_save.return_value = True
            
            await handle_profile_updates_background("test_user", profile_updates, profile)
            
            mock_validate.assert_called_once_with(profile_updates["updates"], profile)
            mock_update.assert_called_once_with(profile, profile_updates["updates"])
            mock_save.assert_called_once_with("test_user", profile)
            mock_log.assert_called_once_with("test_user", profile_updates["updates"])
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_invalid_structure(self):
        """Test background processing with invalid structure."""
        profile = Mock()
        
        invalid_updates = {"invalid": "structure"}
        
        with patch('llm_integration.validate_updates') as mock_validate:
            await handle_profile_updates_background("test_user", invalid_updates, profile)
            
            # Should not call validate_updates for invalid structure
            mock_validate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_no_valid_updates(self):
        """Test background processing with no valid updates."""
        profile = Mock()
        
        profile_updates = {
            "updates": [
                {
                    "section": "demographics",
                    "field": "name",
                    "value": "Alex",
                    "confidence": 1.5,  # Invalid confidence > 1.0
                    "reason": "User stated name"
                }
            ]
        }
        
        with patch('llm_integration.validate_updates') as mock_validate:
            mock_validate.return_value = []  # No valid updates
            
            await handle_profile_updates_background("test_user", profile_updates, profile)
            
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_error(self):
        """Test background processing error handling."""
        profile = Mock()
        
        profile_updates = {
            "updates": [
                {
                    "section": "demographics",
                    "field": "name",
                    "value": "Alex",
                    "confidence": 0.95,
                    "reason": "User stated name"
                }
            ]
        }
        
        with patch('llm_integration.validate_updates', side_effect=Exception("Validation error")):
            # Should not raise exception
            await handle_profile_updates_background("test_user", profile_updates, profile)
    
    def test_log_profile_update(self):
        """Test profile update logging."""
        updates = [
            {
                "section": "demographics",
                "field": "name",
                "value": "Alex",
                "confidence": 0.95,
                "reason": "User stated name"
            }
        ]
        
        with patch('llm_integration.log_request') as mock_log_request:
            log_profile_update("test_user", updates)
            
            mock_log_request.assert_called_once_with(
                "info", "Profile fact updated",
                user_id="test_user",
                section="demographics",
                field="name",
                value="Alex",
                confidence=0.95,
                reason="User stated name"
            )


class TestMainChatFunctionality:
    """Test main chat functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_with_streaming_profile_update_success(self):
        """Test successful chat with streaming and profile update."""
        with patch('llm_integration.get_profile_card') as mock_get_profile, \
             patch('llm_integration.format_llm_messages') as mock_format_messages, \
             patch('llm_integration.stream_llm_response') as mock_stream, \
             patch('llm_integration.log_message') as mock_log_message, \
             patch('llm_integration.store_conversation_round') as mock_store_episode, \
             patch('llm_integration.handle_profile_updates_background') as mock_handle_updates, \
             patch('llm_integration.metrics') as mock_metrics, \
             patch('llm_integration.log_request') as mock_log_request:
            
            # Mock profile
            mock_profile = Mock()
            mock_get_profile.return_value = mock_profile
            
            # Mock messages
            mock_messages = [{"role": "user", "content": "Hello"}]
            mock_format_messages.return_value = mock_messages
            
            # Mock streaming response
            async def mock_stream_gen():
                yield ("Hello", "", "")
                yield (" there!", "", "")
                yield ("", '{"updates": [{"section": "demographics", "field": "name", "value": "Alex", "confidence": 0.95, "reason": "User stated name"}]}', "")
            
            mock_stream.return_value = mock_stream_gen()
            
            # Mock episode storage
            mock_store_episode.return_value = "episode_123"
            
            response = await chat_with_streaming_profile_update("test_user", "Hello")
            
            assert isinstance(response, StreamingResponse)
            assert response.media_type == "text/event-stream"
            
            # Verify calls
            mock_get_profile.assert_called_once_with("test_user")
            mock_format_messages.assert_called_once_with("test_user", "Hello", mock_profile)
            mock_log_message.assert_called_once_with("test_user", "user", "Hello")
            mock_store_episode.assert_called_once()
            mock_handle_updates.assert_called_once()
            mock_metrics.record_openai_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_with_streaming_profile_update_error(self):
        """Test chat error handling."""
        with patch('llm_integration.get_profile_card', side_effect=Exception("Profile error")), \
             patch('llm_integration.log_request') as mock_log_request:
            
            response = await chat_with_streaming_profile_update("test_user", "Hello")
            
            assert isinstance(response, StreamingResponse)
            mock_log_request.assert_called()
    
    @pytest.mark.asyncio
    async def test_simple_streaming_chat(self):
        """Test simple streaming chat fallback."""
        with patch('llm_integration.log_message') as mock_log_message:
            response = await simple_streaming_chat("test_user", "Hello world")
            
            assert isinstance(response, StreamingResponse)
            assert response.media_type == "text/event-stream"
            mock_log_message.assert_called_once_with("test_user", "assistant", "I received your message: Hello world")


class TestErrorHandling:
    """Test error handling in LLM integration."""
    
    @pytest.mark.asyncio
    async def test_stream_llm_response_json_parse_error(self):
        """Test JSON parsing error in function call."""
        with patch('llm_integration._client') as mock_client:
            # Mock streaming response with malformed JSON
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].delta = Mock()
            mock_response.choices[0].delta.content = None
            mock_response.choices[0].delta.function_call = Mock()
            mock_response.choices[0].delta.function_call.arguments = '{"invalid": json}'  # Malformed JSON
            mock_response.choices[0].finish_reason = "function_call"
            
            mock_client.chat.completions.create.return_value = iter([mock_response])
            
            messages = [{"role": "user", "content": "Hello"}]
            
            chunks = []
            async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
                chunks.append((chunk, profile_updates_json, raw_chunk))
            
            assert len(chunks) == 1
            assert chunks[0][1] == '{"updates": []}'  # Should fallback to empty updates
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_validation_error(self):
        """Test background processing with validation error."""
        profile = Mock()
        
        profile_updates = {
            "updates": [
                {
                    "section": "invalid_section",  # Invalid section
                    "field": "name",
                    "value": "Alex",
                    "confidence": 0.95,
                    "reason": "User stated name"
                }
            ]
        }
        
        with patch('llm_integration.validate_updates') as mock_validate:
            mock_validate.return_value = []  # No valid updates after validation
            
            await handle_profile_updates_background("test_user", profile_updates, profile)
            
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_profile_updates_background_save_error(self):
        """Test background processing with save error."""
        from profile_card import ProfileCard
        
        profile = Mock(spec=ProfileCard)
        profile_updates = {
            "updates": [
                {
                    "section": "demographics",
                    "field": "name",
                    "value": "Alex",
                    "confidence": 0.95,
                    "reason": "User stated name"
                }
            ]
        }
        
        with patch('llm_integration.validate_updates') as mock_validate, \
             patch('llm_integration.update_profile_with_confidence') as mock_update, \
             patch('llm_integration.save_profile_card') as mock_save, \
             patch('llm_integration.log_request') as mock_log_request:
            
            mock_validate.return_value = profile_updates["updates"]
            mock_update.return_value = profile
            mock_save.side_effect = Exception("Save error")
            
            # Should not raise exception
            await handle_profile_updates_background("test_user", profile_updates, profile)
            
            mock_log_request.assert_called()
