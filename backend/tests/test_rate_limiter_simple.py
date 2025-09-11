#!/usr/bin/env python3
"""
Simple test to verify rate limiting functionality works.
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_rate_limiter_import():
    """Test that we can import the rate limiter module."""
    try:
        from rate_limiter import get_user_identifier, get_rate_limit_for_endpoint
        print("✅ Successfully imported rate limiter functions")
        return True
    except Exception as e:
        print(f"❌ Failed to import rate limiter: {e}")
        return False

def test_rate_limit_configuration():
    """Test rate limit configuration."""
    try:
        from rate_limiter import get_rate_limit_for_endpoint, RATE_LIMITS
        
        # Test known endpoints
        assert get_rate_limit_for_endpoint("/api/chat") == "10/minute"
        assert get_rate_limit_for_endpoint("/api/memory") == "30/minute"
        
        print("✅ Rate limit configuration is correct")
        return True
    except Exception as e:
        print(f"❌ Rate limit configuration test failed: {e}")
        return False

def test_user_identifier():
    """Test user identifier function."""
    try:
        from rate_limiter import get_user_identifier
        from unittest.mock import Mock
        
        # Create mock request
        request = Mock()
        request.state.uid = "test-user-123"
        
        # Mock get_remote_address
        from unittest.mock import patch
        with patch('rate_limiter.get_remote_address', return_value="192.168.1.1"):
            identifier = get_user_identifier(request)
            assert identifier == "user:test-user-123:192.168.1.1"
        
        print("✅ User identifier function works correctly")
        return True
    except Exception as e:
        print(f"❌ User identifier test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running simple rate limiter tests...")
    print("=" * 50)
    
    tests = [
        test_rate_limiter_import,
        test_rate_limit_configuration,
        test_user_identifier,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
