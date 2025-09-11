# Memo Bot Backend - Complete Functionality Documentation

## Overview
The Memo Bot backend is a FastAPI-based AI companion service designed for children aged 6-10. It features a playful dinosaur character "Roary" that learns about users through conversation and maintains persistent memory systems.

## Core Architecture

### 1. Main Application (`main.py`)
**Purpose**: FastAPI application entry point with authentication, CORS, and API endpoints.

**Key Features**:
- Firebase Authentication integration
- CORS middleware for web frontend
- Rate limiting per endpoint
- Structured logging
- Health check endpoint

**API Endpoints**:
- `GET /health` - Health check
- `GET /whoami` - User authentication verification
- `GET /api/profile-card` - Retrieve user's profile card
- `POST /api/profile-card` - Update profile card manually
- `GET /api/profile-card/history` - Get profile version history
- `GET /api/profile-card/stats` - Get profile statistics
- `POST /api/memory` - Add memory/fact
- `GET /api/memory` - Retrieve user memories
- `GET /api/messages` - Get conversation history
- `GET /api/chroma/inspect` - Debug ChromaDB contents
- `POST /api/chat` - Main chat endpoint with streaming

### 2. Profile Card System (`profile_card.py`)
**Purpose**: MECE (Mutually Exclusive, Collectively Exhaustive) user profile management.

**Structure**:
- **Demographics**: name, age, gender, location
- **Interests**: primary_interests, secondary_interests
- **Preferences**: favorite_animals, favorite_foods, favorite_colors, favorite_activities
- **Constraints**: safety_limits, schedule_limits, health_limits
- **Goals**: learning_goals, personal_goals
- **Context**: recent_events, current_projects
- **Communication**: style, learning_level, attention_span, language_preference

**Key Features**:
- Confidence tracking for each fact
- Version history with timestamps
- Automatic validation of new information
- Firestore persistence
- Token calculation for LLM context

### 3. LLM Integration (`llm_integration.py`)
**Purpose**: OpenAI integration with streaming responses and automatic profile updates.

**Key Features**:
- Streaming chat responses
- Function calling for profile updates
- Context injection from profile cards and episodic memory
- Background profile update processing
- Conversation history integration
- Fallback mechanisms for API failures

**Roary Character**:
- Playful dinosaur personality
- Child-friendly language (ages 6-10)
- Encouraging and safe interactions
- Catchphrases and rewards system

### 4. Episodic Memory (`episodic_memory.py`)
**Purpose**: Vector-based conversation storage using ChromaDB for semantic search.

**Key Features**:
- ChromaDB integration (local or cloud)
- OpenAI embeddings for semantic search
- Episode storage with metadata
- Conversation round tracking
- Session management
- Similarity-based retrieval

**Data Model**:
- Episode ID, user_id, user_message, ai_response
- Round number, session_id, timestamp
- Embeddings (user, AI, combined)
- Token count estimation

### 5. Firestore Storage (`firestore_store.py`)
**Purpose**: Primary data persistence layer.

**Collections**:
- `users/{uid}/memories` - Semantic facts with confidence/salience scoring
- `users/{uid}/messages` - Conversation history
- `users/{uid}/meta/profile` - Profile card data
- `users/{uid}/profile_history` - Profile version history

**Key Features**:
- Non-transactional upserts for MVP
- Confidence and salience scoring
- Chronological message ordering
- Slug-based document IDs

### 6. Rate Limiting (`rate_limiter.py`)
**Purpose**: User-based rate limiting to prevent abuse.

**Configuration**:
- `/api/chat`: 10/minute (most expensive)
- `/api/memory`: 30/minute
- `/api/messages`: 30/minute
- `/api/profile-card`: 20/minute
- `/whoami`: 60/minute
- Default: 30/minute

**Features**:
- Redis backend (optional, falls back to in-memory)
- User+IP based keys for isolation
- Custom error responses with retry information
- Metrics integration

### 7. Monitoring (`monitoring.py`)
**Purpose**: Google Cloud Monitoring integration for observability.

**Metrics Tracked**:
- OpenAI API usage (tokens, latency, cost, success rate)
- Rate limiting events
- Custom application metrics
- User-specific metrics with labels

### 8. Logging (`logging_config.py`)
**Purpose**: Structured JSON logging for production monitoring.

**Features**:
- JSON formatted logs
- Request correlation IDs
- User ID tracking
- Performance metrics
- Exception handling

## Data Flow

### Chat Request Flow:
1. **Authentication**: Verify Firebase ID token
2. **Rate Limiting**: Check user quotas
3. **Profile Retrieval**: Get current user profile card
4. **Context Building**: 
   - Format profile for LLM
   - Retrieve relevant episodes from ChromaDB
   - Get recent conversation history
5. **LLM Processing**: 
   - Stream response with function calling
   - Extract profile updates from function calls
6. **Background Processing**:
   - Validate and apply profile updates
   - Store conversation as episode in ChromaDB
   - Log messages to Firestore
7. **Response**: Stream content to user

### Memory Storage Flow:
1. **User Input**: Memory/fact submission
2. **Validation**: Check for duplicates and confidence
3. **Storage**: Upsert to Firestore with scoring
4. **Indexing**: Create embeddings for semantic search

## Configuration

### Environment Variables:
- `OPENAI_API_KEY` - OpenAI API access
- `OPENAI_MODEL` - Model to use (default: gpt-5-nano)
- `FIRESTORE_PROJECT` - Google Cloud project ID
- `CHROMA_API_KEY` - ChromaDB cloud access
- `CHROMA_TENANT` - ChromaDB tenant
- `CHROMA_DATABASE` - ChromaDB database name
- `CHROMA_MODE` - "local" or "cloud"
- `REDIS_URL` - Redis for rate limiting (optional)
- `WEB_ORIGIN` - CORS allowed origins

### Dependencies:
- FastAPI - Web framework
- OpenAI - LLM integration
- Google Cloud Firestore - Primary storage
- ChromaDB - Vector storage
- Firebase Admin - Authentication
- SlowAPI - Rate limiting
- Redis - Rate limiting backend (optional)

## Security Features

1. **Authentication**: Firebase ID token verification
2. **Rate Limiting**: Per-user quotas to prevent abuse
3. **CORS**: Configured for specific origins
4. **Input Validation**: Pydantic models for request validation
5. **Error Handling**: Graceful degradation without exposing internals
6. **Child Safety**: Content filtering and safe interaction guidelines

## Performance Optimizations

1. **Streaming Responses**: Real-time chat experience
2. **Background Processing**: Non-blocking profile updates
3. **Caching**: Profile cards cached in memory
4. **Connection Pooling**: Reused database connections
5. **Efficient Queries**: Indexed Firestore queries
6. **Semantic Search**: Vector similarity for relevant context

## Monitoring & Observability

1. **Structured Logging**: JSON logs with correlation IDs
2. **Metrics**: Custom Google Cloud metrics
3. **Health Checks**: Application status monitoring
4. **Error Tracking**: Comprehensive exception handling
5. **Performance Tracking**: Latency and token usage monitoring

## Deployment

- **Container**: Docker-based deployment
- **Platform**: Google Cloud Run
- **Scaling**: Automatic scaling based on demand
- **Environment**: Production-ready with proper logging and monitoring

## Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end API testing
- **Rate Limiting Tests**: Load and limit validation
- **Multi-user Tests**: Concurrent user scenarios
- **Firestore Tests**: Database operation validation

This backend provides a robust, scalable foundation for the Memo Bot AI companion, with comprehensive memory systems, user profiling, and child-safe interactions.
