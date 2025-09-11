# Memory Management Strategy & Engineering Design (TalkyDino-ready)

Below is a practical, production-minded design that hits all the benchmarked skills: **accurate retrieval, test-time learning, conflict resolution, reflective reasoning, long-term session mgmt, temporal awareness, knowledge updates, confidence/abstention, efficiency/capacity, lifelong learning**.

---

## 0) Executive Summary

* **Tiers:** Profile (semantic facts), Episodes (chat logs), Tasks/Goals, and Reflective Notes.
* **Pipelines:**

  * **Read path (per turn):** ANN → top-M candidates → feature scoring (relevance & confidence) → top-K → prompt assembly.
  * **Write path (per turn):** extraction → write-gate (keep? update? version?) → store → background compaction.
* **Policies:** versioned facts (valid\_from/valid\_to), conflict detection, time decay, summarization, promotion/demotion.
* **Metrics:** Recall\@K, NDCG, ECE/Brier for confidence, token budget, latency P95.

---

## 1) Memory Tiers

1. **User Profile (Semantic)** – compact, durable facts (name, timezone, preferences, skills).
2. **Episodic Memory (Conversations/Events)** – raw multi-turn transcripts + per-session summaries.
3. **Tasks & Goals** – current objectives, deadlines, open loops.
4. **Reflective Memory** – distilled insights (“kid responds better to visuals”), rules of thumb learned in session.

> Rationale: clean separation lets you query only relevant shards and apply different retention/compaction rules.

---

## 2) Storage & Indexing

* **Primary DB:** Postgres (JSONB) or Firestore for objects/metadata.
* **Vector Search:** pgvector (HNSW) or FAISS/Qdrant/Pinecone for embeddings.
* **Shards/Indexes:**

  * `profile_index` (semantic)
  * `episodic_index_hot` (≤ 7–14 days)
  * `episodic_index_warm` (≤ 90 days)
  * `episodic_index_cold` (> 90 days, queried via fallback)
  * `reflective_index`, `tasks_index`

---

## 3) Minimal Data Schemas (JSON-ish)

### 3.1 Profile Fact

```json
{
  "id": "pf_123",
  "user_id": "u1",
  "text": "User lives in Atlanta, GA.",
  "embedding": [ ... ],
  "type": "location|preference|identity|constraint",
  "predicate": "lives_in", "subject": "user", "object": "Atlanta, GA",
  "valid_from": "2025-08-01T00:00:00Z",
  "valid_to": null,                       // closed on update
  "first_seen": "2025-08-01T12:00:00Z",
  "last_seen": "2025-09-05T21:10:00Z",
  "seen_count": 4,
  "source": "user_message|tool|system|inferred",
  "confidence_base": 0.92,
  "intrinsic_importance": 0.7,           // static hint, 0..1
  "tags": ["location"]
}
```

### 3.2 Episode Chunk

```json
{
  "id": "ep_777",
  "user_id": "u1",
  "session_id": "s_2025-09-05_01",
  "turn_range": [120, 148],
  "summary": "They lost toy dinosaur; asked for help.",
  "raw_excerpt": "…",
  "embedding": [ ... ],
  "timestamp_start": "2025-09-05T18:20:00Z",
  "timestamp_end": "2025-09-05T18:35:00Z",
  "source": "chat",
  "tags": ["loss", "emotion:sad"]
}
```

### 3.3 Reflective Note

```json
{
  "id": "rf_009",
  "user_id": "u1",
  "text": "Child calms down if response includes a short story.",
  "embedding": [ ... ],
  "origin": "llm_reflection|human_feedback",
  "confidence_base": 0.75,
  "tags": ["strategy","engagement"]
}
```

### 3.4 Task/Goal

```json
{
  "id": "tk_045",
  "user_id": "u1",
  "title": "Find lost toy workflow",
  "status": "active|done|stalled",
  "due": null,
  "embedding": [ ... ],
  "created_at": "2025-09-05T18:22:00Z",
  "updated_at": "2025-09-05T18:34:00Z",
  "tags": ["goal"]
}
```

---

## 4) Read Path (Per Turn)

**Step A – Candidate Fetch (fast):**

* For each relevant shard (profile, tasks, episodic\_hot, reflective):

  * Compute query embedding.
  * ANN top-M (e.g., M=50 per shard).
  * Optional keyword/field filters (must-have terms, tags, date ranges).

**Step B – Feature Scoring (precise):**
Compute per candidate:

* **Relevance (aka salience\_now)**
  \`relevance = w\_q \* cosine(query, fact) + w\_g \* cosine(active\_goal, fact)

  * w\_e \* emotion\_match + w\_r \* recency\_score + w\_f \* freq\_score + w\_i \* intrinsic\_importance\`
* **Confidence (confidence\_now)**
  \`confidence = c\_b \* confidence\_base + c\_s \* cosine(query,fact)

  * c\_v \* vote\_agreement + c\_p \* source\_reliability\`

Defaults (good starting point):

* `w_q=0.45, w_g=0.15, w_e=0.10, w_r=0.10, w_f=0.10, w_i=0.10`
* `c_b=0.40, c_s=0.20, c_v=0.25, c_p=0.15`

**Step C – Priority & Diversity:**

* `priority = relevance * confidence`
* Take **top-K** overall (e.g., K=16), then **MMR** to enforce diversity.

**Step D – Prompt Assembly (token budgets):**

* Hard caps per section (example for a 128k window):

  * System: ≤ 300 tokens
  * **User Profile (condensed):** ≤ 200
  * **Active Goals:** ≤ 120
  * **Reflective Notes (if any):** ≤ 120
  * **Top semantic facts:** ≤ 400
  * **Top episodic snippets:** ≤ 600
* Stable headings & bullet formatting so the model grounds reliably.

---

## 5) Write Path (Per Turn)

**Step 1 – Extract candidates to write:**

* Small LLM or rule extractor produces `facts`, `reflective_notes`, and `task_updates` from the current turn.

**Step 2 – Write-Gate (should we store?):**

* Keep only items that pass:

  * **Novelty:** not near-duplicate of existing (cosine < 0.92 to nearest).
  * **Confidence threshold:** extractor\_conf ≥ 0.7 (tunable).
  * **Sensitivity policy:** skip if PII/sensitive and user hasn’t opted-in.

**Step 3 – Merge / Update / Version:**

* **Profile facts** share `(subject,predicate)` keys.

  * If **same value**: increment `seen_count`, `last_seen`.
  * If **new value**: close old (`valid_to = now`), write new (`valid_from = now`).
  * If **contradiction** (negation), mark both and queue for resolution (see §6).

**Step 4 – Indexing:**

* Compute embeddings; upsert into the right index shard.
* Tag with session\_id/time for later temporal queries.

**Step 5 – Background Compaction (async jobs):**

* Deduplicate, cluster near-duplicates; bump `seen_count`.
* **Session summarization:** produce concise episode notes.
* **Promotion:** patterns repeated across days → become profile facts or reflective notes.
* **Demotion/archival:** old, low-priority episodic chunks → warm/cold shards.

---

## 6) Conflict Detection & Resolution

* **Detection:**

  * Same `(subject,predicate)` with mutually exclusive `object` values OR explicit negations.
  * Heuristics + a short LLM check (“Are these statements inconsistent?” → yes/no & why).

* **Resolution policy:**

  1. Prefer **more recent** and **higher source reliability**.
  2. If still unclear and **priority is high**, **ask the user** (“Did you move to Seattle recently? I have Atlanta from before.”).
  3. Keep **version history** (don’t delete), close the older with `valid_to`.
  4. If marked “uncertain”, lower its `confidence_base` and exclude from default retrieval unless user asks explicitly.

---

## 7) Temporal Awareness

* Every object has `timestamp_*` and for profile facts `valid_from/valid_to`.
* **Time-aware retrieval:** boost relevance if the query contains temporal cues (“yesterday”, “last week”, dates).
* Provide a helper: `time_bucket ∈ {hot, warm, cold}` and `recency_score = exp(-Δt / τ)` with τ tuned per tier.

---

## 8) Reflective Reasoning Support

* After meaningful sessions (or every N turns), run a **reflection pass**:

  * Generate 1–3 short **Reflective Notes** capturing strategies, preferences inferred, pitfalls.
  * Write with moderate `confidence_base` (e.g., 0.7) and **require agreement** (vote\_agreement) before using strongly.

---

## 9) Confidence & Abstention

* **Per item:** use `confidence_now` to decide tone:

  * ≥ 0.8: assertive; 0.6–0.8: hedge; < 0.6: avoid unless user asks.
* **Per answer:** if **top answer priority is high but confidence low**, trigger:

  * **Clarifying question** (safe) OR
  * **Tool call** (verify) OR
  * **Do not answer** (abstain) with a short rationale.

---

## 10) Efficiency & Capacity

* **Two-stage retrieval:** ANN → re-rank top-M only (**not O(N)**).
* **Shards & filters:** query only likely tiers; cap M per tier (e.g., 50).
* **Token budgets:** hard caps per section; cut by priority.
* **Compaction policy:**

  * Episodic: keep raw hot; summarize into episodes for warm; archive raw to cold storage/object store.
  * Profile: keep latest active version + last N historic versions.
  * Reflective: cap to 100 per user; prune by priority.

---

## 11) Implementation Interfaces (thin, composable)

**Retrieval API**

```http
POST /memory/retrieve
{ "user_id": "u1", "query": "...", "active_goal": "...", "K": 16 }
→ { "profile":[...], "episodic":[...], "tasks":[...], "reflective":[...], "debug":{scores...} }
```

**Write API**

```http
POST /memory/write
{ "user_id":"u1", "facts":[...], "episodes":[...], "reflective":[...], "tasks":[...] }
→ { "accepted":[ids...], "rejected":[{item,reason}...] }
```

**Update/Close Fact**

```http
POST /memory/profile/version
{ "fact_id":"pf_123", "valid_to":"2025-09-05T21:10:00Z" }
```

**Admin/Compaction**

```http
POST /memory/compact  { "user_id":"u1" }
```

---

## 12) Feature Computation (practical recipes)

* **emotion\_match:** lexicon + tiny sentiment classifier now; upgrade to emotion embeddings later.
* **freq\_score:** `1 - exp(-seen_count/3)` (diminishing returns).
* **intrinsic\_importance:** rule table by `type/tag` (safety 0.9, identity 0.7, preference 0.4, chit-chat 0.2).
* **confidence\_base:** extractor self-score or rules; calibrate later.
* **source\_reliability:** user\_message 0.95, verified tool 0.9–0.98, system 0.8, inferred 0.7, web\_scraped 0.6.
* **vote\_agreement:** among top-M, count agreeing near-duplicates (cosine ≥ 0.8), `min(count/3,1)`.

---

## 13) Prompt Layout (example)

```
# System
…bot persona, safety, time/place…

# User Profile (200 tokens)
- Lives in …
- Likes …
- Constraints: …

# Active Goals (≤ 120 tokens)
- …

# Reflective Notes (≤ 120)
- …

# Relevant Facts (≤ 400)
• …

# Episodic Highlights (≤ 600)
• [2025-09-05] Lost toy dinosaur; asked for help (summary) …
```

---

## 14) Evaluation Plan (maps to benchmarks)

* **Accurate Retrieval:** Recall\@K, NDCG on labeled “gold” memories.
* **Test-time Learning:** seed new facts mid-dialogue, check later recall/use.
* **Conflict Resolution:** synthetic conflicting updates; measure correct version chosen & clarification rate.
* **Reflective Memory:** tasks that require using a prior “strategy” note; measure success.
* **Long-term Session Mgmt:** LoCoMo-style long chats; measure QA from deep history.
* **Temporal Reasoning:** queries with dates; measure correct time-aware recall.
* **Knowledge Updates:** change of city/job; ensure old version closed, new used.
* **Confidence/Abstention:** selective accuracy above thresholds; ECE/Brier.
* **Efficiency/Capacity:** tokens per answer, latency P95, index size.
* **Lifelong Learning:** promotion rate of repeated facts to profile; downstream win rate.

---

## 15) How This Compares to Your Plan

**Your plan (great start):**
0\) System prompt basics ✔️

1. **User Profile** (≤200 tokens, session-update) ✔️
2. **Related semantic memory** (compressed → dense + keyword → rerank) ✔️
3. **Related episodic** (time decay + dense + keyword → rerank; no compression) ✔️

**Improvements I’m adding:**

* **Separate reflective notes** and **explicit task/goal tier** (agents need both).
* **Versioned profile facts** with `valid_from/valid_to` for clean updates.
* **Conflict detection/resolution** logic + user confirmations.
* **Sharded episodic indices (hot/warm/cold)** and **episode summaries** (you said “no compression”; I recommend summarizing *older* episodes only to save cost without losing recency detail).
* **Confidence/abstention policy** tied to thresholds.
* **Promotion/demotion** rules for lifelong learning.
* **Clear APIs** and **metrics** for continuous improvement.

If you really want “no compression” for episodes, limit it to **hot window only** (e.g., 7–14 days). Beyond that, summaries are essential for cost and retrieval quality.

---

## 16) Default Knobs (so you can ship fast)

* `M=50` candidates per shard; `K=16` final.
* Hot/warm/cold cutoffs: 14d / 90d.
* `τ` (recency decay): 7d episodic, 30d profile refresh.
* Write-gate thresholds: extractor\_conf ≥ 0.7; novelty cosine < 0.92.
* Promotion: fact priority ≥ 0.6 on ≥ 3 different days → move to profile/reflective.
* Abstain/clarify if top item `confidence_now < 0.6` and `relevance > 0.6`.

---

### Implementation Checklist

* [ ] Create tables/collections & vector indexes per tier.
* [ ] Build retrieval endpoint (ANN → re-rank → MMR → top-K).
* [ ] Build write-gate + versioning for profile facts.
* [ ] Add episodic summarizer (trigger at session end or warm rollover).
* [ ] Add reflection pass (every N turns or significant events).
* [ ] Add conflict detector + user clarification prompt.
* [ ] Token budgeted prompt assembler.
* [ ] Logging/metrics dashboards (Retrieval\@K, ECE/Brier, latency, tokens).
* [ ] A/B switch for weights in a `weights.yaml`.

---

If you want, I can turn this into a **small reference implementation** (Python: scorer + retrieval + write-gate) and a **`weights.yaml`** so you can tune without redeploying.
