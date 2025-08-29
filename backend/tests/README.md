# Test Suite for Memo Bot Backend

This directory contains comprehensive tests for the memo bot backend, including rate limiting, authentication, and multi-user isolation.

## Test Structure

### `conftest.py`
- Shared pytest fixtures and configuration
- Mock setups for Firebase auth, Firestore, and OpenAI
- Test client configuration

### `test_rate_limiter.py`
- **Unit tests** for rate limiting functionality
- Tests user identification, rate limit configuration, and error handling
- Tests storage backends (in-memory and Redis)

### `test_integration.py`
- **Integration tests** for API endpoints
- Tests authentication, rate limiting, and error handling
- Tests all endpoints with proper mocking

### `test_multi_user.py`
- **Multi-user isolation tests**
- Tests that different users have separate rate limit buckets
- Tests data isolation between users
- Tests rate limit recovery

## Running Tests

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Files
```bash
# Unit tests only
pytest tests/test_rate_limiter.py

# Integration tests only
pytest tests/test_integration.py

# Multi-user tests only
pytest tests/test_multi_user.py
```

### Run Tests with Markers
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only multi-user tests
pytest -m multi_user
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests with Coverage
```bash
pytest --cov=. --cov-report=html
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Test individual functions and classes
- Mock external dependencies
- Fast execution
- Focus on logic correctness

### Integration Tests (`@pytest.mark.integration`)
- Test API endpoints end-to-end
- Test authentication flow
- Test rate limiting integration
- Test error handling

### Multi-User Tests (`@pytest.mark.multi_user`)
- Test user isolation
- Test rate limiting per user
- Test data separation
- Test concurrent user scenarios

## Key Test Scenarios

### Rate Limiting Tests
- ✅ Different users get separate rate limit buckets
- ✅ Same user from different IPs gets separate limits
- ✅ Different endpoints have different rate limits
- ✅ Rate limits reset after time window
- ✅ Proper error responses with retry information

### Authentication Tests
- ✅ Valid Firebase tokens work correctly
- ✅ Invalid tokens return 401 errors
- ✅ Missing tokens return 401 errors
- ✅ UID is stored in request state for rate limiting

### Multi-User Isolation Tests
- ✅ Memory operations are isolated per user
- ✅ Message operations are isolated per user
- ✅ Rate limiting works independently per user
- ✅ Data cannot leak between users

### Error Handling Tests
- ✅ Firestore errors are handled gracefully
- ✅ OpenAI API errors are handled gracefully
- ✅ Rate limit errors include helpful information
- ✅ Authentication errors are properly formatted

## Mock Strategy

### Firebase Authentication
- Mock `fb_auth.verify_id_token()` to return test UIDs
- Test different UIDs for multi-user scenarios
- Test invalid token scenarios

### Firestore Operations
- Mock all Firestore operations (`add_memory`, `get_top_facts`, etc.)
- Verify correct UIDs are passed to operations
- Test error scenarios

### OpenAI API
- Mock OpenAI client and streaming responses
- Test error handling for API failures
- Test streaming response format

### Rate Limiting
- Use in-memory storage for tests
- Mock time functions for rate limit recovery tests
- Test different IP scenarios

## Test Data

### Test Users
- `user-1`: Test user 1
- `user-2`: Test user 2
- `test-user-123`: Default test user

### Test Endpoints
- `/test-rate-limit`: Special test endpoint (5/minute)
- `/api/chat`: Chat endpoint (10/minute)
- `/api/memory`: Memory endpoint (30/minute)
- `/api/messages`: Messages endpoint (30/minute)
- `/whoami`: Auth endpoint (60/minute)

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external dependencies (all mocked)
- Fast execution
- Deterministic results
- Clear error messages

## Debugging Tests

### Run Single Test
```bash
pytest tests/test_rate_limiter.py::TestUserIdentifier::test_get_user_identifier_with_uid -v
```

### Run with Print Statements
```bash
pytest -s tests/test_rate_limiter.py
```

### Run with PDB Debugger
```bash
pytest --pdb tests/test_rate_limiter.py
```

## Adding New Tests

1. **Unit Tests**: Add to appropriate test file or create new one
2. **Integration Tests**: Add to `test_integration.py`
3. **Multi-User Tests**: Add to `test_multi_user.py`
4. **Fixtures**: Add shared fixtures to `conftest.py`
5. **Markers**: Use appropriate pytest markers

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Descriptive names that explain what is being tested

### Example Test
```python
def test_rate_limit_exceeded_returns_429(self, client, mock_firebase_auth, auth_headers):
    """Test that rate limit exceeded returns 429 status code."""
    # Arrange
    # Act
    # Assert
```
