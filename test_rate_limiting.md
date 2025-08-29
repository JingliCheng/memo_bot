# Rate Limiting Test Plan

## Step B4 - Rate Limiting per User - Test Instructions

### Prerequisites
1. Install new dependencies: `cd backend && pip install -r requirements.txt`
2. Make sure your backend is running: `cd backend && python main.py`
3. Make sure your frontend is running: `cd web && npm run dev`

### Rate Limit Configuration
- **Chat endpoint** (`/api/chat`): 10 requests per minute (most expensive)
- **Memory endpoints** (`/api/memory`): 30 requests per minute
- **Messages endpoint** (`/api/messages`): 30 requests per minute  
- **Auth endpoint** (`/whoami`): 60 requests per minute (lightweight)

### Test Steps

#### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2. Test Single User Rate Limiting
**In one browser tab:**
1. Open `http://localhost:5173`
2. Send 12+ chat messages quickly (within 1 minute)
3. After 10 messages, you should get a 429 error with message:
   ```json
   {
     "error": "Rate limit exceeded",
     "message": "Too many requests. Limit: 10/minute",
     "retry_after": 60,
     "endpoint": "/api/chat",
     "uid": "your-uid-here"
   }
   ```

#### 3. Test User Isolation
**Open two browser tabs (different UIDs):**
1. **Tab A**: Send 10+ chat messages (should hit rate limit)
2. **Tab B**: Send chat messages (should work fine - different user)
3. Each user should have their own rate limit bucket

#### 4. Test Different Endpoint Limits
**In the same tab:**
1. Hit chat rate limit (10/min)
2. Try refreshing memory panel (30/min) - should still work
3. Try refreshing messages panel (30/min) - should still work
4. Try `/whoami` calls (60/min) - should still work

#### 5. Test Rate Limit Recovery
1. Wait 1 minute after hitting rate limit
2. Try sending a chat message - should work again
3. Rate limits reset every minute

### Expected Results
✅ **User Isolation**: Each user gets their own rate limit bucket  
✅ **Endpoint-Specific**: Different limits for different endpoints  
✅ **Proper Error Messages**: 429 responses with helpful information  
✅ **Recovery**: Rate limits reset after the time window  
✅ **NAT Protection**: Users behind same IP get separate limits  

### Rate Limiting Key Strategy
- **Primary Key**: `user:{uid}:{ip}` 
- **Fallback**: `ip:{ip}` (if no UID available)
- **Storage**: In-memory (development) or Redis (production)

### Production Notes
- Set `REDIS_URL` environment variable to use Redis for distributed rate limiting
- Rate limits are per-user, preventing heavy users from affecting others
- Each endpoint has appropriate limits based on resource usage

### Troubleshooting
- **Import errors**: Make sure to install dependencies with `pip install -r requirements.txt`
- **Rate limits not working**: Check backend logs for rate limiter initialization
- **Same limits for all users**: Verify UID is being stored in `request.state.uid`

## Security Benefits
- ✅ **Prevents abuse**: Heavy users can't spam expensive OpenAI calls
- ✅ **User isolation**: One user's usage doesn't affect others
- ✅ **Resource protection**: Backend and OpenAI API are protected from overuse
- ✅ **Fair usage**: Each user gets their own quota
