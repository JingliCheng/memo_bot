# Testing Guide for Rate Limiting Implementation

This guide explains how to test the rate limiting functionality that was implemented in Step B4.

## 🧪 Test Suite Overview

The test suite is located in the `backend/tests/` directory and includes:

### Test Files
- **`test_rate_limiter.py`** - Unit tests for rate limiting logic
- **`test_integration.py`** - Integration tests for API endpoints
- **`test_multi_user.py`** - Multi-user isolation tests
- **`conftest.py`** - Shared fixtures and configuration

### Test Categories
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints end-to-end
- **Multi-User Tests**: Test user isolation and rate limiting per user

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run All Tests
```bash
python -m pytest
```

### 3. Run Specific Test Suites
```bash
# Unit tests only
python -m pytest tests/test_rate_limiter.py -v

# Integration tests only
python -m pytest tests/test_integration.py -v

# Multi-user tests only
python -m pytest tests/test_multi_user.py -v
```

### 4. Use the Test Runner Script
```bash
# Run all tests
python run_tests.py all

# Run unit tests only
python run_tests.py unit

# Run with coverage
python run_tests.py all --coverage

# Install dependencies and run tests
python run_tests.py all --install-deps
```

## 🔍 What the Tests Verify

### Rate Limiting Functionality
- ✅ **User Identification**: Correct UID + IP key generation
- ✅ **Endpoint Limits**: Different limits for different endpoints
- ✅ **Rate Limit Enforcement**: Requests are blocked after limit
- ✅ **Error Responses**: Proper 429 responses with retry info
- ✅ **Time Window Reset**: Rate limits reset after time window

### Multi-User Isolation
- ✅ **Separate Buckets**: Different users get separate rate limit buckets
- ✅ **IP Isolation**: Same user from different IPs gets separate limits
- ✅ **Data Isolation**: User data is properly isolated
- ✅ **Concurrent Users**: Multiple users can use the system simultaneously

### API Integration
- ✅ **Authentication**: Firebase token verification works
- ✅ **Endpoint Protection**: All endpoints are rate limited
- ✅ **Error Handling**: Graceful error handling for all scenarios
- ✅ **Response Format**: Proper JSON responses with error details

## 📊 Rate Limit Configuration

| Endpoint | Limit | Reason |
|----------|-------|---------|
| `/api/chat` | 10/minute | Expensive OpenAI API calls |
| `/api/memory` | 30/minute | Moderate Firestore operations |
| `/api/messages` | 30/minute | Lightweight data retrieval |
| `/whoami` | 60/minute | Very lightweight auth check |
| `/test-rate-limit` | 5/minute | Easy testing endpoint |

## 🧪 Manual Testing

### 1. Start the Backend
```bash
cd backend
python main.py
```

### 2. Test Rate Limiting Manually
```bash
# Run the manual test script
python test_rate_limiting_manual.py
```

### 3. Test with Browser
1. Open `http://localhost:5173` in your browser
2. Send 12+ chat messages quickly
3. After 10 messages, you should get rate limited
4. Open a second browser tab (incognito) - should work fine

### 4. Test Different Endpoints
- Hit chat rate limit (10/min)
- Try refreshing memory panel (30/min) - should still work
- Try refreshing messages panel (30/min) - should still work
- Try `/whoami` calls (60/min) - should still work

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Markers for different test types
- Output formatting
- Async test support

### Test Fixtures (`conftest.py`)
- Mock Firebase authentication
- Mock Firestore operations
- Mock OpenAI API
- Test client setup
- Rate limiter reset

### Environment Variables
- `REDIS_URL`: Optional Redis connection for distributed rate limiting
- `OPENAI_API_KEY`: Required for chat functionality
- `FIRESTORE_PROJECT`: Required for Firestore operations

## 🐛 Debugging Tests

### Run Single Test
```bash
pytest tests/test_rate_limiter.py::TestUserIdentifier::test_get_user_identifier_with_uid -v
```

### Run with Print Statements
```bash
pytest -s tests/test_rate_limiter.py
```

### Run with Debugger
```bash
pytest --pdb tests/test_rate_limiter.py
```

### Check Test Coverage
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

## 📝 Adding New Tests

### 1. Unit Tests
Add to `test_rate_limiter.py`:
```python
def test_new_functionality(self):
    """Test description."""
    # Arrange
    # Act
    # Assert
```

### 2. Integration Tests
Add to `test_integration.py`:
```python
def test_new_endpoint(self, client, mock_firebase_auth, auth_headers):
    """Test new endpoint."""
    response = client.get("/new-endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### 3. Multi-User Tests
Add to `test_multi_user.py`:
```python
def test_new_multi_user_scenario(self, client):
    """Test multi-user scenario."""
    # Test with multiple users
```

## 🚨 Common Issues

### Import Errors
- Make sure to install dependencies: `pip install -r requirements.txt`
- Check that you're in the backend directory

### Rate Limiting Not Working
- Check backend logs for rate limiter initialization
- Verify UID is being stored in `request.state.uid`
- Check that rate limiter middleware is properly configured

### Authentication Errors
- Verify Firebase configuration
- Check that tokens are being passed correctly
- Ensure `get_verified_uid` is working

### Test Failures
- Check that all mocks are properly configured
- Verify test data matches expected format
- Check for timing issues in rate limit tests

## 📈 Performance Testing

### Load Testing
```bash
# Install locust for load testing
pip install locust

# Create load test script
# Run load test
locust -f load_test.py --host=http://localhost:8000
```

### Rate Limit Stress Testing
```bash
# Test rate limiting under load
python -c "
import requests
import threading
import time

def make_requests():
    for i in range(20):
        try:
            response = requests.get('http://localhost:8000/test-rate-limit')
            print(f'Request {i}: {response.status_code}')
        except Exception as e:
            print(f'Error: {e}')
        time.sleep(0.1)

# Run multiple threads
threads = []
for i in range(5):
    t = threading.Thread(target=make_requests)
    threads.append(t)
    t.start()

for t in threads:
    t.join()
"
```

## 🎯 Success Criteria

Your rate limiting implementation is working correctly if:

- ✅ All tests pass: `pytest` returns 0 exit code
- ✅ Different users get separate rate limit buckets
- ✅ Rate limits are enforced per endpoint
- ✅ 429 responses include helpful retry information
- ✅ Rate limits reset after time window
- ✅ No cross-contamination between users
- ✅ Authentication works with rate limiting

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [slowapi Documentation](https://github.com/laurents/slowapi)
- [Firebase Admin SDK Testing](https://firebase.google.com/docs/admin/setup)

---

**Happy Testing! 🧪✨**
