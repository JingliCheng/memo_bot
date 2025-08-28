# AI Companion – Memory System High‑Level Design (Memory‑Centric)

> Goal: Design a production‑ready memory system for a child‑safe AI companion that learns user‑specific facts, preferences, routines, and boundaries, and injects only the right memories into context to improve usefulness without sacrificing safety, privacy, or latency.

---

## 1) Product goals & constraints

**Primary goals**

* Personalize conversations (tone, interests, routines) while staying age‑appropriate and safe.
* Be fast enough for real‑time voice (target P95 end‑to‑end < 1.5–2.0s cloud path; < 300ms on device cueing).
* Learn continuously but conservatively (avoid fabricating or over‑generalizing from one‑offs).
* Provide transparent, editable memories (parents can view/edit; user can correct or ask to forget).

**Constraints**

* Child safety & parental controls (COPPA‑like posture; opt‑in memory; easy “forget me”).
* Privacy‑first defaults (PII minimization, encryption at rest, key rotation, least‑privilege access).
* Edge + Cloud hybrid: Raspberry Pi for on‑device hot cache and wake‑word; cloud for LLM + long‑term storage.
* Strict cost & latency budgets; operate with intermittent connectivity.

---

## 2) Personas & use cases

* **Child user**: conversational fun, learning assistant, habit‑forming (reading logs, chores).
* **Parent/guardian**: supervision, safety controls, memory visibility, opt‑in/out, export & delete.
* **System maintainer**: adjust policies, rollouts, observability, incident response.

**Representative memory use cases**

* Preferences ("loves dinosaurs"), routines ("bedtime 8:30pm"), capabilities ("can read short words"), boundaries ("no scary stories"), device environment ("bedroom speaker").

---

## 3) Memory taxonomy (what we store)

* **Episodic**: time‑stamped events ("We read *Green Eggs and Ham* on 2025‑08‑26"). TTL: medium; compress to summaries.
* **Semantic (long‑term facts)**: stable truths/preferences ("favorite animal: triceratops"). Long TTL; versioned.
* **Identity & relationships**: names (family, friends), roles, contact relations (minimized PII; hashed/opaque IDs when possible).
* **Safety/guardrails memory**: user‑specific redlines (allergies, topics to avoid), parent‑defined rules.
* **Task/skill memory**: progress on learning goals; streaks; badges.
* **Device/context memory**: locale, time zone, device persona (voice, character), capabilities.

> Each memory has **source** (user said, parent set, sensor/event), **confidence**, **salience**, **privacy flags**, **retention policy**, and **links** to other memories (graph edges).

---

## 4) Architecture (Azure‑centric example; portable to other clouds)

**Edge (Raspberry Pi)**

* Wake word + VAD; short‑term working memory cache; safety pre‑filters; local TTS; offline fallback.
* Local KV (e.g., SQLite + write‑behind queue) for immediate episodic notes and pinned preferences.

**Cloud**

* **API gateway** → **Session Orchestrator** (LangGraph/LangChain‑like) → **Memory Service** → **Tools** (RAG, policy, TTS/ASR).
* **Memory Service** (core):

  * **Transactional store**: Postgres (Azure Database for PostgreSQL) for canonical memory rows (ACID, versioning, audit).
  * **Vector index**: Azure AI Search vector index or pgvector for semantic recall.
  * **Cache**: Azure Cache for Redis for hot, per‑session working memory.
  * **Blob**: Azure Storage for raw episodes (audio snippets, drawings) & snapshots.
  * **Events**: Event Hubs (append‑only) for write path, consolidation jobs, and CDC.
  * **Policy**: Safety rules, PII classifier, Do‑Not‑Learn lists.
* **Model**: Azure OpenAI (or equivalent) for NLU, summarization, distillation; controllable via system prompts + tools.
* **Observability**: App Insights + custom traces for memory read/write decisions and safety outcomes.
* **Secrets**: Key Vault; field‑level encryption for sensitive fields.

**Data flows**

1. **Write path**: User utterance → NLU extract candidates → policy checks → dedupe/merge → commit → index → schedule consolidation.
2. **Read path**: Query intent → retrieval policy → rank/trim → assemble context → generate → post‑checks (citations, redaction).

---

## 5) Data model (canonical)

**Table: `memory_item`**

* `id (uuid)`, `user_id`, `type` (episodic|semantic|safety|skill|device), `subject`, `predicate`, `value_text`, `value_json`,
* `source` (child|parent|system|sensor), `confidence` \[0–1], `salience` \[0–1], `emotion` {valence,intensity},
* `created_at`, `updated_at`, `valid_from`, `valid_to`, `ttl_policy` (enum), `version`,
* `pii_flags` (bitmask), `safety_flags` (bitmask), `tags` (array), `origin_event_id`, `links` (array of memory ids).

**Vector sidecar**

* `memory_id`, `embedding (vector)`, `modality` (text|audio|image), `norm`, `last_reindexed_at`.

**Audit & policy**

* `memory_log` with **CRUD**, actor (system/parent/child), reason, old/new snapshots.

---

## 6) Write path (memory formation)

**Stages**

1. **Candidate extraction**:

   * Slot‑filling: (subject, predicate, value, certainty). Extract from conversation + metadata (time, location if allowed).
   * Classify **type** (episodic vs semantic) and **safety** relevance; compute preliminary **confidence**.
2. **Policy filtering**:

   * PII minimization (e.g., avoid storing addresses unless whitelisted by parent).
   * Age‑appropriateness, Do‑Not‑Learn topics, profanity/unsafe content.
3. **Dedup/merge**:

   * Resolve conflicts: prefer parent‑set memory; otherwise choose higher‑confidence or most‑recent with hysteresis.
   * Merge strategy for counters/preferences; maintain history in versions.
4. **Commit + index**:

   * ACID insert/update in Postgres → publish CDC event → async index into vector store.
5. **Consolidation** (batch or streaming):

   * Summarize episodic items into semantic facts when repeated (e.g., 3+ occurrences → "likes dinosaurs").
   * Apply **time‑decay** and **frequency** to update `salience`; compress stale episodes into monthly summaries.

**Salience score** *(tunable)*

```
salience = w_r * recency_decay(Δt) + w_f * frequency + w_e * emotion_intensity
         + w_p * parent_pin + w_n * novelty + w_t * task_relevance
```

---

## 7) Read path (retrieval & context assembly)

1. **Intent gating**: classify whether the turn needs memory (small talk vs task vs safety check).
2. **Candidate retrieval (hybrid)**:

   * Filters: `user_id`, `type` subset, tags.
   * BM25/keyword over `value_text` + **vector KNN** over embeddings.
   * **RRF (reciprocal rank fusion)** to combine lexical + vector.
3. **Rerank** with task‑specific scoring:

   * weight `salience`, `recency`, `confidence`, and **policy fitness** (don’t surface restricted facts).
4. **Trim** to budget: e.g., pack <= N tokens; prefer short, high‑signal facts; convert to key‑value bullets.
5. **Attribution**: mark each inserted memory with `[memory:id, source, confidence]` internally for logs.
6. **Post‑gen checks**: ensure no restricted memory leaked; redact PII; attach short citations (“You told me this on …”).

---

## 8) Safety, privacy, and compliance

* **Consent & transparency**: parental portal to turn memory on/off; per‑category toggles; per‑item view/edit; full export.
* **Right‑to‑Forget**: hard delete from primary; tombstone & purge from indices/blobs; verify via background job.
* **PII controls**: field‑level encryption; tokenization; stored only when necessary and whitelisted.
* **Safety memory**: immutable by child; editable by parent; enforced at retrieval time (prevents unsafe prompts/responses).
* **Data residency**: pin storage/compute to required regions.
* **Incident response**: memory leak playbook; automated alerts on anomalous memory usages.

---

## 9) APIs (sketch)

**Write**

* `POST /v1/memory/candidates` → accepts extracted candidates; returns upserted items with ids.
* `POST /v1/memory/commit` → atomic commit of batch with policies applied.
* `POST /v1/memory/feedback` → user/parent corrections (approve/deny, edit, pin, forget).

**Read**

* `POST /v1/memory/retrieve` → {intent, query, filters, k, budget} → ranked items.
* `POST /v1/memory/contextify` → returns compressed, token‑bounded memory snippets for the LLM.

**Admin/Parent**

* `GET /v1/memory/list` (filters); `PATCH /v1/memory/{id}`; `DELETE /v1/memory/{id}`; `POST /v1/memory/export`.

---

## 10) Evaluation & metrics

**Quality**

* Retrieval P\@k / nDCG using labeled traces.
* **Groundedness**: % of memory claims that map to committed items with ≥ threshold confidence.
* **Correction acceptance rate**: fraction of user/parent edits that stop future errors.
* **Personalization win‑rate**: A/B uplift on engagement or task success when memory is on vs off.

**Safety & privacy**

* Memory leak rate (incidents / 10k sessions), PII exposure rate, blocked‑turn recall.

**Latency & cost**

* P95 read path, write path; cache hit rate; vector QPS; storage cost per user.

---

## 11) Operational plan

* **Schemas as code** (migrations + versioning); **feature flags** for new memory types.
* **Backfills & reindexing** jobs (idempotent; chunked; resumable).
* **Observability**: per‑turn Memory Decision Log (why we retrieved or suppressed X).
* **A/B**: vary consolidation thresholds, salience weights, and context budgets.
* **Rate limits**: per user and per org; abuse detection.

---

## 12) Walkthrough example

1. Child says: "I love triceratops and stegosaurus!" → candidate preferences x2; confidence 0.8.
2. Policy: allowed; PII‑free → commit episodic items; salience low‑medium.
3. Repetition over a week (3+ mentions) → consolidation promotes **semantic**: `likes_animals = [triceratops, stegosaurus]`, confidence 0.92.
4. Next session: user asks for a bedtime story → retrieval ranks "no scary stories" (safety) + "likes dinosaurs" (semantic) → context yields a friendly dinosaur story, no scary parts.

---

## 13) Data contracts & prompts (examples)

**Extraction prompt contract** (LLM/tool): return JSON with `subject, predicate, value, certainty, type, pii_flags`.
**Contextify format**: bullet KVs, one line each, max 30 tokens, include `(since: YYYY‑MM‑DD)`.

---

## 14) Tech choices (swappable)

* **Primary DB**: Postgres (Azure Database for PostgreSQL Flexible Server).
* **Vector**: Azure AI Search vector index or pgvector; RRF with BM25.
* **Cache**: Redis.
* **Queue/Events**: Azure Event Hubs or Service Bus.
* **Blob**: Azure Storage.
* **Models**: Azure OpenAI for NLU/summarize; on‑device TTS.

---

## 15) Roadmap (phased)

* **v0 (internal)**: working memory only (ephemeral), no LTM; parent portal mock.
* **v1 (beta)**: opt‑in LTM for preferences + safety; manual review queue for new memory types; export/delete.
* **v2**: consolidation + salience; parent portal edit; A/B infra.
* **v3**: skill/task memory; progress charts; offline summaries on‑device; multi‑child households.

---

## 16) Open questions & risks

* What is the minimal, privacy‑respectful set of PII needed for value?
* How to keep consolidation faithful without drifting (e.g., over‑generalization)?
* Parent UX for transparency that a child can still understand.
* Cost of vector search at scale vs PG‑only hybrid; need per‑tenant sharding.
* Long‑horizon safety: preventing model from inferring sensitive traits even if not stored.

---

## 17) Appendix – quick schemas & scoring

**`memory_item` (DDL sketch)**

```sql
CREATE TABLE memory_item (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  type TEXT CHECK (type IN ('episodic','semantic','safety','skill','device')),
  subject TEXT, predicate TEXT,
  value_text TEXT, value_json JSONB,
  source TEXT, confidence REAL, salience REAL,
  emotion JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  valid_from TIMESTAMPTZ, valid_to TIMESTAMPTZ,
  ttl_policy TEXT, version INT DEFAULT 1,
  pii_flags INT DEFAULT 0, safety_flags INT DEFAULT 0,
  tags TEXT[], origin_event_id UUID,
  links UUID[]
);
```

**Read‑path ranking (pseudo)**

```python
score = 0.35*salience + 0.20*recency_decay + 0.15*confidence \
      + 0.15*lexical_rank_norm + 0.15*vector_rank_norm
# suppress if violates safety_policy(memory)
```
