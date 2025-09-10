# main.py
import os, json, asyncio, time, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import HTTPException
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from openai import OpenAI
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Depends, Request, HTTPException
from slowapi.errors import RateLimitExceeded
from rate_limiter import limiter, rate_limit_exceeded_handler, apply_rate_limit

# Import monitoring and logging
from monitoring import metrics
from logging_config import setup_logging, log_request

# Import Profile Card system
from profile_card import get_profile_card, save_profile_card, create_default_profile_card, ProfileCard
from llm_integration import chat_with_streaming_profile_update


load_dotenv(override=True)

# Setup structured logging
setup_logging()

# Firebase Admin init (uses ADC: gcloud auth application-default login for local dev)
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    # Initialize with the correct project ID to match frontend
    firebase_admin.initialize_app(cred, {
        'projectId': 'gen-lang-client-0574433212'
    })

def get_verified_uid(request: Request) -> str:
    # Expect "Authorization: Bearer <Firebase ID Token>"
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


from firestore_store import add_memory, get_top_facts, log_message, get_last_messages
import firestore_store
print("Loaded:", firestore_store.__file__, "|", firestore_store.VERSION_TAG)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-5-nano")

# Log API key info (safely - only show first/last few chars)
if OPENAI_API_KEY:
    masked_key = f"{OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}" if len(OPENAI_API_KEY) > 12 else "***"
    print(f"OpenAI API Key: {masked_key}")
    print(f"OpenAI Model: {OPENAI_MODEL}")
else:
    print("WARNING: OPENAI_API_KEY not found in environment variables")

app = FastAPI()
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

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/whoami")
@apply_rate_limit("/whoami")
def whoami(request: Request, uid: str = Depends(get_verified_uid)):
    return {"uid": uid}

# ---- Profile Card API Endpoints ----

@app.get("/api/profile-card")
@apply_rate_limit("/api/profile-card")
def api_get_profile_card(request: Request, uid: str = Depends(get_verified_uid)):
    """Get user's profile card."""
    try:
        profile = get_profile_card(uid)
        return {"ok": True, "profile": profile}
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile card: {e}")

@app.post("/api/profile-card")
@apply_rate_limit("/api/profile-card")
def api_update_profile_card(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    """Manually update profile card."""
    try:
        # Get current profile
        profile = get_profile_card(uid)
        
        # Update sections with provided data
        if "sections" in payload:
            for section_name, section_data in payload["sections"].items():
                if section_name in profile.sections:
                    profile.sections[section_name].update(section_data)
        
        # Save updated profile
        success = save_profile_card(uid, profile)
        
        if success:
            return {"ok": True, "profile": profile}
        else:
            raise HTTPException(500, "Failed to save profile card")
            
    except Exception as e:
        raise HTTPException(500, f"Failed to update profile card: {e}")

@app.get("/api/profile-card/history")
@apply_rate_limit("/api/profile-card/history")
def api_get_profile_history(request: Request, limit: Optional[int] = 10, uid: str = Depends(get_verified_uid)):
    """Get profile card version history."""
    try:
        from profile_card import get_profile_history
        history = get_profile_history(uid, limit or 10)
        return {"ok": True, "history": history}
    except Exception as e:
        raise HTTPException(500, f"Failed to get profile history: {e}")

@app.get("/api/profile-card/stats")
@apply_rate_limit("/api/profile-card/stats")
def api_get_profile_stats(request: Request, uid: str = Depends(get_verified_uid)):
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

# POST /api/memory  (ignore any uid in payload)
@app.post("/api/memory")
@apply_rate_limit("/api/memory")
def api_add_memory(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    try:
        saved = add_memory(uid, payload)
        return {"ok": True, "memory": saved}
    except Exception as e:
        raise HTTPException(500, f"add_memory failed: {e}")


# GET /api/memory  (query by verified user)
@app.get("/api/memory")
@apply_rate_limit("/api/memory")
def api_list_memory(request: Request, limit: Optional[int] = 12, offset: Optional[int] = 0, uid: str = Depends(get_verified_uid)):
    try:
        items = get_top_facts(uid, limit or 12, offset or 0)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_memory failed: {e}")


# GET /api/messages  (query by verified user)
@app.get("/api/messages")
@apply_rate_limit("/api/messages")
def api_list_messages(request: Request, limit: Optional[int] = 12, offset: Optional[int] = 0, uid: str = Depends(get_verified_uid)):
    try:
        items = get_last_messages(uid, limit or 12, offset or 0)  # chronological
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_messages failed: {e}")

# GET /api/chroma/inspect  (inspect Chroma DB contents)
@app.get("/api/chroma/inspect")
@apply_rate_limit("/api/chroma/inspect")
def api_inspect_chroma(request: Request, uid: str = Depends(get_verified_uid)):
    """Inspect Chroma DB contents for debugging purposes."""
    try:
        from episodic_memory import EpisodicMemory, get_chroma_client, get_episodic_collection
        import os
        
        # Get Chroma client and ensure collection exists
        client = get_chroma_client()
        
        # Try to get existing collection, create if it doesn't exist
        try:
            collection = client.get_collection("episodic_memory")
        except Exception:
            # Collection doesn't exist, create it
            collection = client.create_collection(
                name="episodic_memory",
                metadata={"description": "Conversation rounds stored as episodes with embeddings"}
            )
        
        # Get all episodes for the user
        episodes = collection.get(
            where={"user_id": uid}
        )
        
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
        
        # Get stats
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
        # Return empty result instead of error for better UX
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
    
# --- Chat ---
# Chat functionality now handled by llm_integration.py with Profile Card system

@app.post("/api/chat")
@apply_rate_limit("/api/chat")
async def chat(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    """Chat endpoint with Profile Card integration and streaming responses."""
    
    msg = (payload or {}).get("message", "")
    if not isinstance(msg, str) or not msg.strip():
        raise HTTPException(400, "message is required")

    # Persist user message
    log_message(uid, "user", msg)

    # Use new Profile Card system with streaming
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