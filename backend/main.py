import asyncio, os, json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from time import time
from firestore import get_top_facts, add_memory, get_last_messages, add_message, FirestoreError

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/chat")
async def chat(payload: dict):
    # MVP: just echo back as a stream; swap with OpenAI later

    uid = (payload or {}).get("uid", "demo")
    msg = (payload or {}).get("message", "")

    try:
        # Add user message to Firestore
        add_message(uid, "user", msg)
        
        # Get top facts from Firestore
        facts = get_top_facts(uid)
        memory_bullets = "\n".join(
            [f"- {f['key']}: {f['value']}" for f in facts]
        )
        prompt_preview = f"MEMORY:\n{memory_bullets}\n\nUSER:\n{msg}\n\nASSISTANT:"

        async def stream():
            for piece in ["(using memory) ", prompt_preview[:120], " ..."]:
                yield f"data:{json.dumps(piece)}\n\n"
                await asyncio.sleep(0.03)
            yield "data:[DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")
        
    except FirestoreError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/memory")
def add_memory_endpoint(payload: dict):
    """Add a memory item to Firestore."""
    uid = payload.get("uid", "demo")
    item = {
        "type": payload.get("type", "semantic"),
        "key": payload.get("key", ""),
        "value": payload.get("value", ""),
        "confidence": payload.get("confidence", 0.9),
        "salience": payload.get("salience", 1.0),
        "ts": time(),
    }
    
    try:
        result = add_memory(uid, item)
        return result
    except FirestoreError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/memory")
def get_memories(uid: str = "demo", memory_type: str = None):
    """Get memories for a user, optionally filtered by type."""
    try:
        from firestore import get_all_memories
        memories = get_all_memories(uid, memory_type)
        return {"memories": memories, "count": len(memories)}
    except FirestoreError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/messages")
def get_messages(uid: str = "demo", limit: int = 12):
    """Get recent messages for a user."""
    try:
        messages = get_last_messages(uid, limit)
        return {"messages": messages, "count": len(messages)}
    except FirestoreError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/health")
def health_detailed():
    """Detailed health check including Firestore status."""
    try:
        from firestore import health_check
        firestore_health = health_check()
        return {
            "ok": True,
            "firestore": firestore_health,
            "timestamp": time()
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "timestamp": time()
        }
