# Multi-User Isolation Test Plan

## Step B3 Authorization Policy - Test Instructions

### Prerequisites
1. Make sure your backend is running: `cd backend && python main.py`
2. Make sure your frontend is running: `cd web && npm run dev`

### Test Steps

#### 1. Open Two Browser Sessions
- **Tab A**: Open `http://localhost:5173` in your main browser
- **Tab B**: Open `http://localhost:5173` in an incognito/private window (or different browser)

#### 2. Verify Different UIDs
- Each tab should show a different UID in the blue badge at the top right
- Note down the UIDs: Tab A = `UID: abc12345...`, Tab B = `UID: def67890...`

#### 3. Test Memory Isolation
**In Tab A:**
1. Send message: "My favorite language is English and Chinese"
2. Wait for response
3. Check the Memory panel - should show language preference

**In Tab B:**
1. Send message: "My favorite language is Spanish" 
2. Wait for response
3. Check the Memory panel - should show Spanish preference

#### 4. Test Cross-Contamination Prevention
**In Tab A:**
1. Ask: "What language do I prefer?"
2. Should answer: "English and Chinese" (from Tab A's memory)

**In Tab B:**
1. Ask: "What language do I prefer?"
2. Should answer: "Spanish" (from Tab B's memory)

#### 5. Verify Firestore Data Structure
Check your Firestore console:
- Go to `users/{uidA}/memories` - should contain English/Chinese preference
- Go to `users/{uidB}/memories` - should contain Spanish preference
- Data should be completely isolated between users

### Expected Results
✅ Each browser session gets a unique, stable UID  
✅ Memories are stored under `users/{uid}/memories`  
✅ No cross-contamination between users  
✅ Backend verifies Firebase ID tokens (not client-sent UIDs)  
✅ All API calls use Authorization header with valid tokens  

### Troubleshooting
- If UIDs are the same: Clear browser data and try incognito mode
- If memories are shared: Check that backend is using `Depends(get_verified_uid)`
- If API calls fail: Check browser console for authentication errors

## Security Verification

Your implementation now has:
- ✅ **Server-side UID verification**: Backend extracts UID from verified Firebase ID token
- ✅ **No client-sent UID trust**: All endpoints ignore any UID in request body
- ✅ **Proper authorization**: Each user can only access their own `users/{uid}/` data
- ✅ **Token refresh**: Frontend automatically refreshes expired tokens
- ✅ **CORS protection**: Only your frontend domain can make requests

This is **~90% to "real"** production-ready multi-user isolation!
