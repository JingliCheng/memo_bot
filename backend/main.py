# main.py
import os, json, asyncio
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


load_dotenv(override=True)

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
        os.getenv("WEB_ORIGIN", "http://localhost:5173"),
        "https://talkydino-ui.vercel.app/",
        "https://memo-bot-ui.vercel.app/"
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
def api_list_memory(request: Request, limit: Optional[int] = 12, uid: str = Depends(get_verified_uid)):
    try:
        items = get_top_facts(uid, limit or 12)
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_memory failed: {e}")


# GET /api/messages  (query by verified user)
@app.get("/api/messages")
@apply_rate_limit("/api/messages")
def api_list_messages(request: Request, limit: Optional[int] = 12, uid: str = Depends(get_verified_uid)):
    try:
        items = get_last_messages(uid, limit or 12)  # chronological
        return {"ok": True, "items": items}
    except Exception as e:
        raise HTTPException(500, f"list_messages failed: {e}")
    
# --- Chat ---

_use_openai = bool(OPENAI_API_KEY)
if _use_openai:
    from openai import OpenAI
    _client = OpenAI(api_key=OPENAI_API_KEY)

def _build_system_prompt(facts):
    bullets = "\n".join(f"- {f.get('key')}: {f.get('value')}" for f in facts)
    return (
        "You are a friendly assistant. Prefer explicit facts from MEMORY. "
        "If info is missing, ask one short clarifying question.\n"
        f"MEMORY:\n{bullets}"
    )

@app.post("/api/chat")
@apply_rate_limit("/api/chat")
async def chat(request: Request, payload: Dict[str, Any], uid: str = Depends(get_verified_uid)):
    msg = (payload or {}).get("message", "")
    if not isinstance(msg, str) or not msg.strip():
        raise HTTPException(400, "message is required")

    # Persist user message
    log_message(uid, "user", msg)

    # Assemble context
    facts = get_top_facts(uid, limit=6)
    system_prompt = _build_system_prompt(facts)
    history = get_last_messages(uid, limit=6)

    if not _use_openai:
        async def fake_stream():
            for piece in ["(no OpenAI key) ", "You said: ", msg]:
                yield f"data:{json.dumps(piece)}\n\n"
                await asyncio.sleep(0.02)
            yield "data:[DONE]\n\n"
        return StreamingResponse(fake_stream(), media_type="text/event-stream")

    def to_messages():
        msgs = [{"role": "system", "content": system_prompt}]
        for h in history:
            msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": msg})
        return msgs

    # Log the API call details
    print(f"Making OpenAI API call with:")
    print(f"  Model: {OPENAI_MODEL}")
    print(f"  API Key: {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:] if OPENAI_API_KEY else 'None'}")
    print(f"  Messages count: {len(to_messages())}")
    
    try:
        stream = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=to_messages(),
            stream=True,
        )
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        print(f"Error type: {type(e).__name__}")
        raise HTTPException(500, f"OpenAI API call failed: {e}")

    async def sse():
        full = []
        for event in stream:
            delta = (event.choices[0].delta or {})
            token = getattr(delta, "content", None) if hasattr(delta, "content") else delta.get("content")
            if token:
                full.append(token)
                yield f"data:{json.dumps(token)}\n\n"
        assistant_text = "".join(full)
        log_message(uid, "assistant", assistant_text)
        yield "data:[DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")