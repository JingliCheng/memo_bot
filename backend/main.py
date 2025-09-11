"""
Memo Bot Backend - FastAPI application for AI companion service.

This is the main entry point for the Memo Bot backend, providing:
- Firebase authentication
- Rate limiting
- Profile card management
- Chat functionality with streaming
- Memory storage and retrieval
- Monitoring and logging
"""

import os
import json
from typing import Dict, Any, Optional

import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from slowapi.errors import RateLimitExceeded

# Local imports
from rate_limiter import limiter, rate_limit_exceeded_handler, apply_rate_limit
from monitoring import metrics
from logging_config import setup_logging, log_request
from profile_card import (
    get_profile_card, 
    save_profile_card, 
    create_default_profile_card, 
    ProfileCard
)
from llm_integration import chat_with_streaming_profile_update
from firestore_store import add_memory, get_top_facts, log_message, get_last_messages

# Load environment variables
load_dotenv(override=True)

# Setup structured logging
setup_logging()

# Firebase Admin initialization
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': 'gen-lang-client-0574433212'
    })

def get_verified_uid(request: Request) -> str:
    """
    Verify Firebase ID token and extract user UID.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Verified user UID
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    authz = request.headers.get("authorization") or request.headers.get("Authorization")
    if not authz or not authz.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    
    token = authz.split(" ", 1)[1].strip()
    try:
        decoded = fb_auth.verify_id_token(token)
        uid = decoded.get("uid")
        if not uid:
            raise ValueError("No uid in token")
        
        # Store UID in request state for rate limiting
        request.state.uid = uid
        return uid
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}")


# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

# Log API key info (safely - only show first/last few chars)
if OPENAI_API_KEY:
    masked_key = f"{OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}" if len(OPENAI_API_KEY) > 12 else "***"
    print(f"OpenAI API Key: {masked_key}")
    print(f"OpenAI Model: {OPENAI_MODEL}")
else:
    print("WARNING: OPENAI_API_KEY not found in environment variables")

# FastAPI application setup
app = FastAPI(
    title="Memo Bot Backend",
    description="AI companion service for children",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("WEB_ORIGIN", "http://127.0.0.1:3000"),
        "http://localhost:3000",
        "http://localhost:5173",
        "https://talkydino-ui.vercel.app",
        "https://memo-bot-ui.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Health and authentication endpoints
@app.get("/health")
def health() -> Dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}

@app.get("/test-rate-limit")
@apply_rate_limit("/test-rate-limit")
def test_rate_limit(request: Request, uid: str = Depends(get_verified_uid)) -> Dict[str, str]:
    """Test endpoint for rate limiting functionality."""
    return {"message": "Rate limit test successful", "uid": uid}

@app.get("/whoami")
@apply_rate_limit("/whoami")
def whoami(request: Request, uid: str = Depends(get_verified_uid)) -> Dict[str, str]:
    """Get current user information."""
    return {"uid": uid}

# Profile Card API endpoints
@app.get("/api/profile-card")
@apply_rate_limit("/api/profile-card")
def api_get_profile_card(
    request: Request, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Get user's profile card."""
    try:
        profile = get_profile_card(uid)
        return {"ok": True, "profile": profile}
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile card: {e}")

@app.post("/api/profile-card")
@apply_rate_limit("/api/profile-card")
def api_update_profile_card(
    request: Request, 
    payload: Dict[str, Any], 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Manually update profile card."""
    try:
        profile = get_profile_card(uid)
        
        # Update sections with provided data
        if "sections" in payload:
            for section_name, section_data in payload["sections"].items():
                if section_name in profile.sections:
                    profile.sections[section_name].update(section_data)
        
        success = save_profile_card(uid, profile)
        
        if success:
            return {"ok": True, "profile": profile}
        else:
            raise HTTPException(500, "Failed to save profile card")
            
    except Exception as e:
        raise HTTPException(500, f"Failed to update profile card: {e}")

@app.get("/api/profile-card/history")
@apply_rate_limit("/api/profile-card/history")
def api_get_profile_history(
    request: Request, 
    limit: Optional[int] = 10, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Get profile card version history."""
    try:
        from profile_card import get_profile_history
        history = get_profile_history(uid, limit or 10)
        return {"ok": True, "history": history}
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile history: {e}")

@app.get("/api/profile-card/stats")
@apply_rate_limit("/api/profile-card/stats")
def api_get_profile_stats(
    request: Request, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Get profile card statistics."""
    try:
        profile = get_profile_card(uid)
        from profile_card import count_total_facts, calculate_tokens
        
        stats = {
            "total_facts": count_total_facts(profile),
            "tokens": calculate_tokens(profile),
            "version": profile.version,
            "last_updated": profile.metadata.get("updated_at"),
            "sections": {
                section_name: len(section_data) if isinstance(section_data, dict) else 0
                for section_name, section_data in profile.sections.items()
            }
        }
        
        return {"ok": True, "stats": stats}
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile stats: {e}")

# Memory API endpoints
@app.post("/api/memory")
@apply_rate_limit("/api/memory")
def api_add_memory(
    request: Request, 
    payload: Dict[str, Any], 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Add a memory/fact for the user."""
    try:
        saved = add_memory(uid, payload)
        return {"ok": True, "memory": saved}
    except Exception as e:
        raise HTTPException(500, f"add_memory failed: {e}")


@app.get("/api/memory")
@apply_rate_limit("/api/memory")
def api_list_memory(
    request: Request, 
    limit: Optional[int] = 12, 
    offset: Optional[int] = 0, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Get user's memories/facts."""
    try:
        items = get_top_facts(uid, limit or 12, offset or 0)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_memory failed: {e}")


# Messages API endpoints
@app.get("/api/messages")
@apply_rate_limit("/api/messages")
def api_list_messages(
    request: Request, 
    limit: Optional[int] = 12, 
    offset: Optional[int] = 0, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Get user's conversation history."""
    try:
        items = get_last_messages(uid, limit or 12, offset or 0)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_messages failed: {e}")

# Debug endpoints
@app.get("/api/chroma/inspect")
@apply_rate_limit("/api/chroma/inspect")
def api_inspect_chroma(
    request: Request, 
    uid: str = Depends(get_verified_uid)
) -> Dict[str, Any]:
    """Inspect ChromaDB contents for debugging purposes."""
    try:
        from episodic_memory import get_chroma_client, get_episodic_collection
        
        # Get Chroma client and ensure collection exists
        client = get_chroma_client()
        
        try:
            collection = client.get_collection("episodic_memory")
        except Exception:
            collection = client.create_collection(
                name="episodic_memory",
                metadata={"description": "Conversation rounds stored as episodes with embeddings"}
            )
        
        # Get all episodes for the user
        episodes = collection.get(where={"user_id": uid})
        
        # Format episodes for display
        formatted_episodes = []
        if episodes['metadatas']:
            for i, metadata in enumerate(episodes['metadatas']):
                episode = {
                    "id": episodes['ids'][i],
                    "user_message": metadata.get("user_message", ""),
                    "ai_response": metadata.get("ai_response", ""),
                    "round_number": metadata.get("round_number", 0),
                    "session_id": metadata.get("session_id", ""),
                    "timestamp": metadata.get("timestamp", ""),
                    "tokens": metadata.get("tokens", 0)
                }
                formatted_episodes.append(episode)
        
        # Sort by timestamp (most recent first)
        formatted_episodes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        stats = {
            "total_episodes": len(formatted_episodes),
            "collection_name": "episodic_memory",
            "chroma_mode": os.getenv("CHROMA_MODE", "local"),
            "collection_exists": True
        }
        
        return {
            "ok": True, 
            "episodes": formatted_episodes,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "ok": True,
            "episodes": [],
            "stats": {
                "total_episodes": 0,
                "collection_name": "episodic_memory",
                "chroma_mode": os.getenv("CHROMA_MODE", "local"),
                "collection_exists": False,
                "error": str(e)
            }
        }
    
# Chat API endpoint
@app.post("/api/chat")
@apply_rate_limit("/api/chat")
async def chat(
    request: Request, 
    payload: Dict[str, Any], 
    uid: str = Depends(get_verified_uid)
) -> StreamingResponse:
    """Chat endpoint with Profile Card integration and streaming responses."""
    
    msg = (payload or {}).get("message", "")
    if not isinstance(msg, str) or not msg.strip():
        raise HTTPException(400, "message is required")

    # Persist user message
    log_message(uid, "user", msg)

    # Use Profile Card system with streaming
    try:
        return await chat_with_streaming_profile_update(uid, msg)
    except Exception as e:
        # Fallback to simple response if Profile Card system fails
        log_request("error", f"Profile Card chat failed, using fallback: {e}",
                   user_id=uid,
                   endpoint="/api/chat")
        
        async def fallback_stream():
            yield f"data:{json.dumps('I received your message: ' + msg)}\n\n"
            yield "data:[DONE]\n\n"
        
        return StreamingResponse(fallback_stream(), media_type="text/event-stream")