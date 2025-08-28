# AI Companion – Unified High‑Level Design (Minimal Chatbot with Memory, GCP)

> Goal: Deliver a **minimal online chatbot with working memory** that people can use easily. Focus on building core memory + chat features first. Child‑safe features and advanced controls can be added later.

---

## 1) Primary goals & constraints

**Goals**

* Ship a working chatbot quickly that remembers facts across sessions.
* Be simple enough to deploy on GCP in one weekend.
* Provide basic CRUD on memories and visible “memory peek.”
* Optimize for fast responses and low idle cost.

**Constraints**

* Keep architecture minimal: one service, one DB, one model.
* Stream replies for responsiveness.
* Safety/child‑protection is *optional later* (not priority for MVP).

---

## 2) Personas & use cases

* **User**: chats with bot, wants it to recall preferences and context.
* **You (developer)**: want easy deploy, low ops, cheap to run.

Use cases: remembers likes ("I like triceratops"), recalls routine ("bedtime is 8:30"), fetches recent context to answer naturally.

---

## 3) Memory model (what we store)

* **Semantic facts**: stable truths (likes/dislikes/preferences).
* **Episodic notes**: short events for possible later promotion.
* **Message log**: last few conversation turns.

Each memory item: `type`, `key`, `value`, `confidence`, `salience`, `ts`.

---

## 4) Architecture overview

**Client (Web)**: React (Vite) + Tailwind → HTTPS → Cloud Run URL

**Backend (FastAPI container)**

* `/api/chat`: builds memory block (6 turns + top facts) → calls OpenAI API → streams reply.
* `/api/memory`: CRUD in Firestore.
* `/api/settings`: opt‑in/out toggle.
* `/admin/consolidate`: hourly job to promote repeated episodic → semantic.

**GCP services**

* Cloud Run (container, scales to 0).
* Firestore (memory DB).
* Secret Manager (API keys).
* Cloud Scheduler (cron consolidation).
* Cloud Logging (basic logs).

**Model**: OpenAI API (chat completions).

---

## 5) Firestore schema

```
users/{userId}/memories/{memoryId}
  type, key, value, confidence, salience, ts

users/{userId}/messages/{messageId}
  role, content, ts
```

Queries: top facts (by salience), last 12 messages.

---

## 6) Write path (memory formation)

1. Extract simple candidates (regex: “I like …”).
2. Store/update in Firestore with salience/recency.
3. Optionally log message.
4. Consolidation (hourly): bump frequently repeated facts into semantic.

---

## 7) Read path (context assembly)

1. Grab last \~6 turns.
2. Grab top \~6 semantic facts.
3. Format as compact bullet list (≤300 tokens).
4. Prepend to system prompt and call OpenAI.

Example:

```
MEMORY:
- likes_animals: triceratops
RECENT:
- Yesterday we read Green Eggs and Ham
```

---

## 8) API surface

* `POST /api/chat {userId, message}` → `{reply, memoriesUsed}`
* `GET/POST/DELETE /api/memory`
* `GET/POST /api/settings`
* `POST /admin/consolidate`

---

## 9) Observability & metrics

* Log latency, token usage, which memory IDs used.
* Monitor Firestore reads/writes.

---

## 10) Weekend MVP scope

* **Frontend**: Chat window + memory peek.
* **Backend**: FastAPI serving API + static frontend.
* **Memory**: Firestore store for facts + message log.
* **No advanced safety/child‑safe features** (defer for later).

---

## 11) Deployment checklist

1. Enable APIs: Run, Firestore, Secret Manager, Artifact Registry, Scheduler.
2. `gcloud builds submit --tag ...`
3. Create secrets: `OPENAI_API_KEY`.
4. `gcloud run deploy` with env vars: `FIRESTORE_PROJECT`, `OPENAI_MODEL`.
5. Add Cloud Scheduler hourly POST `/admin/consolidate`.

---

## 12) Timeline (weekend)

**Friday** – scaffold repo, FastAPI hello world, React shell, call OpenAI.

**Saturday** – Firestore collections + CRUD, memory logic, frontend memory peek.

**Sunday** – consolidation job, deploy to Cloud Run, polish UI.

---

## 13) Future upgrades

* Add parent/child safety controls.
* Semantic recall with embeddings (pgvector or Matching Engine).
* Voice I/O, analytics, multi‑user support.

---

**Summary:** This plan prioritizes a **minimal usable chatbot with persistent memory online**. Safety features can be layered on later once the core works.
