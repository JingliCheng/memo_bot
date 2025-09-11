"""
LLM integration with streaming responses and automatic profile updates.

This module handles:
- OpenAI API integration with streaming
- Function calling for profile updates
- Context injection from profile cards and episodic memory
- Background processing of profile updates
- Conversation history management
"""

from __future__ import annotations
import os
import json
import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from openai import OpenAI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

# Local imports
from profile_card import (
    ProfileCard, 
    get_profile_card, 
    save_profile_card, 
    update_profile_with_confidence, 
    validate_updates, 
    contains_new_information
)
from monitoring import metrics
from logging_config import log_request
from firestore_store import log_message, get_last_messages
from episodic_memory import store_conversation_round, search_user_episodes, get_user_recent_episodes

load_dotenv(override=True)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

if OPENAI_API_KEY:
    _client = OpenAI(api_key=OPENAI_API_KEY)
    _use_openai = True
else:
    _client = None
    _use_openai = False

# LLM prompt templates and context formatting
def format_llm_messages(user_id: str, user_message: str, profile_card: ProfileCard) -> List[Dict[str, str]]:
    """Format messages for LLM using system and user roles with function calling."""
    
    profile_context = format_profile_for_llm(profile_card)
    
    # Get relevant episodes for context
    episode_context = get_episode_context(user_id, user_message)
    
    # System message contains instructions and context
    system_content = f"""You are **Roary**, a playful, curious dinosaur buddy for kids aged 6–10.  
You love making friends, asking questions, and collecting “dino-snacks of knowledge.”  
You are excitable, sometimes clumsy, but always encouraging and safe.  
Your mission: be a fun companion that sparks curiosity and imagination, while also learning about the user to provide personalized experiences.  

# Instructions

* ALWAYS respond conversationally to the user’s message first, in Roary’s voice:
  - Short, cheerful sentences (1–3 lines).
  - Warm, silly, and encouraging tone.
  - Sprinkle in catchphrases like:
    - “Roaaary, that’s exciting!”  
    - “Oops, I tripped over my tail again!”  
    - “I’m so curious, tell me more!”  
  - Give playful rewards like “You earned a shiny dino sticker!”  
  - End many responses with a fun little question or choice.

* AFTER your conversational response, if you learned NEW information about the user, call the `profile_update` function.

* Your response must always include the conversational message first, then the function call if needed.  
  Do not output function calls without speaking first.

* Only include updates for NEW information that:
  1. Is explicitly stated by the user
  2. Is not already in the profile
  3. Is a fact about the user (not general knowledge)

# Guidelines for profile updates:
  - demographics: name, age, gender, location
  - interests: primary_interests, secondary_interests
  - preferences: favorite_animals, favorite_foods, favorite_colors, favorite_activities
  - constraints: safety_limits, schedule_limits, health_limits
  - goals: learning_goals, personal_goals
  - context: recent_events, current_projects
  - communication: style, learning_level, attention_span, language_preference

# Safety Boundaries
- Never ask for private info (real name, address, etc.). Use nicknames if shared.
- Avoid adult, violent, scary, or negative topics. Redirect gently to safe play.
- Never promise real gifts or meetings.

# Context

<user_profile>
{profile_context}
</user_profile>

{episode_context}
"""

    # Get conversation history (past 6 rounds = 12 messages)
    conversation_history = get_last_messages(user_id, limit=12, offset=0)
    
    # Build messages array starting with system message
    messages = [{"role": "system", "content": system_content}]
    
    # Add conversation history
    for msg in conversation_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content.strip():  # Only add non-empty messages
            messages.append({"role": role, "content": content})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages

def format_profile_for_llm(profile: ProfileCard) -> str:
    """Format profile card for LLM context injection."""
    sections = profile.sections
    
    # Helper function to format dictionary fields
    def format_dict_field(field_dict: Dict[str, Any]) -> str:
        if not field_dict:
            return ""
        return ", ".join(field_dict.keys())
    
    # Helper function to format single value fields
    def format_value_field(field_dict: Dict[str, Any]) -> str:
        if not field_dict or not field_dict.get("value"):
            return ""
        return field_dict["value"]
    
    context = f"""User Profile:
Name: {format_value_field(sections['demographics']['name'])}, Age: {format_value_field(sections['demographics']['age'])}
Location: {format_value_field(sections['demographics']['location'])}

Interests: {format_dict_field(sections['interests']['primary_interests'])}

Preferences:
- Favorite animals: {format_dict_field(sections['preferences']['favorite_animals'])}
- Favorite foods: {format_dict_field(sections['preferences']['favorite_foods'])}
- Favorite colors: {format_dict_field(sections['preferences']['favorite_colors'])}

Constraints:
- Safety: {format_dict_field(sections['constraints']['safety_limits'])}
- Schedule: {format_dict_field(sections['constraints']['schedule_limits'])}
- Health: {format_dict_field(sections['constraints']['health_limits'])}

Current Context:
- Goals: {format_dict_field(sections['goals']['learning_goals'])}
- Recent events: {format_dict_field(sections['context']['recent_events'])}

Communication Style: {format_value_field(sections['communication']['style'])}
Learning Level: {format_value_field(sections['communication']['learning_level'])}
"""
    
    return context

def get_episode_context(user_id: str, user_message: str, max_episodes: int = 3) -> str:
    """Get relevant episodes for context injection."""
    try:
        # Search for relevant episodes
        episodes = search_user_episodes(user_id, user_message, limit=max_episodes)
        
        if not episodes:
            # Fallback to recent episodes if no relevant ones found
            episodes = get_user_recent_episodes(user_id, limit=max_episodes)
        
        if not episodes:
            return ""
        
        # Format episodes for context
        episode_texts = []
        for episode in episodes:
            episode_text = f"• [Round {episode['round_number']}] User: {episode['user_message'][:100]}{'...' if len(episode['user_message']) > 100 else ''}\n  AI: {episode['ai_response'][:100]}{'...' if len(episode['ai_response']) > 100 else ''}"
            episode_texts.append(episode_text)
        
        return f"\n# Recent Relevant Conversations\n" + "\n".join(episode_texts)
        
    except Exception as e:
        print(f"Error getting episode context: {e}")
        return ""


# Function definitions for OpenAI function calling
def get_profile_update_function_definition() -> Dict[str, Any]:
    """Get the function definition for profile updates."""
    return {
        "name": "profile_update",
        "description": "Update user profile with new information learned during conversation",
        "parameters": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "description": "Array of profile updates to apply",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "description": "Profile section to update",
                                "enum": ["demographics", "interests", "preferences", "constraints", "goals", "context", "communication"]
                            },
                            "field": {
                                "type": "string",
                                "description": "Field within the section to update"
                            },
                            "value": {
                                "type": "string",
                                "description": "New value for the field"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence level for this update (0.0 to 1.0)"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for this update based on user input"
                            }
                        },
                        "required": ["section", "field", "value", "confidence", "reason"]
                    }
                }
            },
            "required": ["updates"]
        }
    }


# Streaming LLM response handling
async def stream_llm_response(messages: List[Dict[str, str]]):
    """Stream LLM response with function call handling. Returns (chunk, profile_updates, raw_output)."""
    
    if not _use_openai:
        # Fallback for testing without OpenAI key
        fallback_response = "I'm sorry, but I don't have access to OpenAI API. Please check your API key configuration."
        yield (fallback_response, '{"updates": []}', fallback_response)
        return
    
    try:
        # Use OpenAI streaming API with function calling
        # Use "auto" but with strong prompting to ensure content generation
        stream = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            functions=[get_profile_update_function_definition()],
            function_call="auto",
            stream=True,
        )
        
        buffer = ""
        raw_output = ""
        profile_updates = {"updates": []}
        function_call_buffer = ""
        in_function_call = False
        
        for event in stream:
            delta = event.choices[0].delta
            
            # Handle content (visible text)
            if delta.content:
                buffer += delta.content
                raw_output += delta.content
                yield (delta.content, "", "")
            
            # Handle function calls
            if delta.function_call:
                function_call_buffer += delta.function_call.arguments or ""
                raw_output += f"<function_call>{delta.function_call.arguments or ''}</function_call>"
                continue
            
            # Check if function call is complete
            if event.choices[0].finish_reason == "function_call":
                try:
                    # Parse the buffered function call arguments
                    function_args = json.loads(function_call_buffer)
                    if function_args.get("updates"):
                        profile_updates = function_args
                        print(f"DEBUG: Parsed {len(profile_updates['updates'])} profile updates from function call")
                except json.JSONDecodeError as e:
                    print(f"Error parsing function call arguments: {e}")
                    print(f"DEBUG: Function call buffer: '{function_call_buffer}'")
        
        # If we have no content but have profile updates, generate a default response
        if not buffer.strip() and profile_updates.get("updates"):
            default_response = "Thanks for sharing that information! I've updated your profile with what you told me."
            buffer = default_response
            raw_output += default_response
            yield (default_response, "", "")
        
        # Send final profile updates
        yield ("", json.dumps(profile_updates), raw_output)
            
    except Exception as e:
        error_msg = f"I'm sorry, there was an error processing your request: {e}"
        print(f"Error in LLM streaming: {e}")
        yield (error_msg, '{"updates": []}', error_msg)

# Background profile update processing
async def handle_profile_updates_background(user_id: str, profile_updates: Dict[str, Any], profile_card: ProfileCard):
    """Handle profile updates in the background with robust validation and idempotent persistence."""
    
    try:
        # Validate the profile updates structure
        if not isinstance(profile_updates, dict) or "updates" not in profile_updates:
            print(f"Invalid profile updates structure for user {user_id}: {profile_updates}")
            return
        
        updates = profile_updates["updates"]
        if not isinstance(updates, list):
            print(f"Invalid updates format for user {user_id}: {updates}")
            return
        
        # Validate each update has required fields
        valid_updates = []
        for update in updates:
            if not isinstance(update, dict):
                print(f"Skipping invalid update format: {update}")
                continue
                
            required_fields = ["section", "field", "value", "confidence", "reason"]
            if not all(field in update for field in required_fields):
                print(f"Skipping incomplete update: {update}")
                continue
                
            # Validate confidence is a number between 0 and 1
            try:
                confidence = float(update["confidence"])
                if not 0.0 <= confidence <= 1.0:
                    print(f"Skipping update with invalid confidence {confidence}: {update}")
                    continue
                update["confidence"] = confidence
            except (ValueError, TypeError):
                print(f"Skipping update with non-numeric confidence: {update}")
                continue
            
            # Validate section is valid
            valid_sections = ["demographics", "interests", "preferences", "constraints", "goals", "context", "communication"]
            if update["section"] not in valid_sections:
                print(f"Skipping update with invalid section '{update['section']}': {update}")
                continue
                
            valid_updates.append(update)
        
        if not valid_updates:
            print(f"No valid updates found for user {user_id}")
            return
        
        # Validate updates are actually new information
        validated_updates = validate_updates(valid_updates, profile_card)
        
        if validated_updates:
            # Update profile with confidence tracking
            updated_profile = update_profile_with_confidence(profile_card, validated_updates)
            save_profile_card(user_id, updated_profile)
            
            # Log the update
            log_profile_update(user_id, validated_updates)
            
            print(f"Profile updated for user {user_id}: {len(validated_updates)} new facts")
        else:
            print(f"No new information to update for user {user_id}")
            
    except Exception as e:
        # Log error but don't fail the user experience
        print(f"Background profile update failed for user {user_id}: {e}")
        log_request("error", f"Background profile update failed: {e}", 
                   user_id=user_id, endpoint="/api/chat")

def log_profile_update(user_id: str, updates: List[Dict[str, Any]]):
    """Log profile updates for monitoring."""
    
    for update in updates:
        log_request("info", "Profile fact updated",
                   user_id=user_id,
                   section=update["section"],
                   field=update["field"],
                   value=update["value"],
                   confidence=update["confidence"],
                   reason=update["reason"])

# Main chat functionality
async def chat_with_streaming_profile_update(user_id: str, user_message: str) -> StreamingResponse:
    """Chat endpoint that streams response and updates profile in background."""
    
    request_id = str(time.time())
    start_time = time.time()
    
    log_request("info", "Chat request started", 
               user_id=user_id, 
               endpoint="/api/chat", 
               request_id=request_id)
    
    # 1. Get current profile card
    profile_card = get_profile_card(user_id)
    
    # 2. Format messages for LLM using developer and user roles
    messages = format_llm_messages(user_id, user_message, profile_card)
    
    # 3. Create streaming response
    async def stream_response():
        full_response = ""
        profile_updates = None
        raw_llm_output = ""
        
        try:
            # Stream the LLM response
            async for chunk, profile_updates_json, raw_chunk in stream_llm_response(messages):
                # Add chunk to full response
                full_response += chunk
                raw_llm_output += raw_chunk
                
                # Check if this is the final chunk with profile updates
                if profile_updates_json and not chunk:
                    # This is the final chunk with profile updates
                    try:
                        profile_updates = json.loads(profile_updates_json)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing profile updates JSON: {e}")
                        profile_updates = {"updates": []}
                    break
                elif chunk:
                    # Send only the content chunk to UI (no raw output metadata)
                    chunk_data = {
                        "content": chunk
                    }
                    yield f"data:{json.dumps(chunk_data)}\n\n"
            
            # Send completion marker with final raw output
            completion_data = {
                "done": True,
                "raw_output": raw_llm_output
            }
            yield f"data:{json.dumps(completion_data)}\n\n"
            
            # Log the AI response to Firestore
            if full_response.strip():
                log_message(user_id, "assistant", full_response.strip())
            
            # Store conversation round as episode
            try:
                # Get the next round number by checking existing episodes
                from episodic_memory import get_user_recent_episodes
                existing_episodes = get_user_recent_episodes(user_id, limit=100)  # Get more to find max round
                
                if existing_episodes:
                    # Find the highest round number and add 1
                    max_round = max([ep.get("round_number", 0) for ep in existing_episodes])
                    round_number = max_round + 1
                else:
                    # First conversation
                    round_number = 1
                
                session_id = f"s_{int(time.time())}"  # Simple session ID based on timestamp
                
                print(f"DEBUG: Round calculation - Found {len(existing_episodes)} existing episodes, max round: {max_round if existing_episodes else 0}, setting round_number to {round_number}")
                
                # Store as episode
                episode_id = store_conversation_round(
                    user_id=user_id,
                    user_message=user_message,
                    ai_response=full_response.strip(),
                    round_number=round_number,
                    session_id=session_id
                )
                print(f"Stored episode {episode_id} for user {user_id}")
                
            except Exception as e:
                print(f"Error storing episode: {e}")
                # Don't fail the user experience for episode storage errors
            
            # Handle profile updates in background (after streaming completes)
            if profile_updates and profile_updates["updates"]:
                print(f"DEBUG: Processing {len(profile_updates['updates'])} profile updates for user {user_id}")
                await handle_profile_updates_background(user_id, profile_updates, profile_card)
            else:
                print(f"DEBUG: No profile updates found for user {user_id}")
            
            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            # Calculate input tokens from messages content
            input_content = " ".join([msg["content"] for msg in messages])
            metrics.record_openai_metrics(
                user_id=user_id,
                endpoint="/api/chat",
                model=OPENAI_MODEL if _use_openai else "none",
                input_tokens=len(input_content.split()) * 1.3,  # Rough estimation
                output_tokens=len(full_response.split()) * 1.3,  # Rough estimation
                latency_ms=latency_ms,
                cost_usd=0.0,  # TODO: Calculate actual cost
                success=True
            )
            
            log_request("info", "Chat request completed successfully",
                       user_id=user_id,
                       endpoint="/api/chat",
                       request_id=request_id,
                       latency_ms=latency_ms)
                
        except Exception as e:
            # Log error but don't interrupt user experience
            print(f"Error in streaming response: {e}")
            log_request("error", f"Chat streaming failed: {e}",
                       user_id=user_id,
                       endpoint="/api/chat",
                       request_id=request_id)
            yield "data:[DONE]\n\n"
    
    return StreamingResponse(stream_response(), media_type="text/event-stream")

# Fallback functions
async def simple_streaming_chat(user_id: str, user_message: str) -> StreamingResponse:
    """Fallback to simple streaming without profile updates."""
    
    async def fallback_stream():
        fallback_response = 'I received your message: ' + user_message
        yield f"data:{json.dumps(fallback_response)}\n\n"
        yield "data:[DONE]\n\n"
        
        # Log the fallback response
        log_message(user_id, "assistant", fallback_response)
    
    return StreamingResponse(fallback_stream(), media_type="text/event-stream")

# Version information
VERSION_TAG = "llm_integration v1.0 STREAMING"
