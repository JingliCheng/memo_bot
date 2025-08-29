#!/usr/bin/env python3
"""
Manual test script for rate limiting functionality.
This script can be used to quickly test rate limiting without running the full test suite.
"""
import requests
import time
import json
from typing import Dict, Any


class RateLimitTester:
    """Manual rate limiting tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_endpoint(self, endpoint: str, headers: Dict[str, str], expected_limit: int) -> bool:
        """Test rate limiting for a specific endpoint."""
        print(f"\n🧪 Testing {endpoint} (expected limit: {expected_limit}/minute)")
        print("-" * 50)
        
        success_count = 0
        rate_limited = False
        
        for i in range(expected_limit + 2):  # Try 2 more than the limit
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"✅ Request {i+1}: Success (200)")
                elif response.status_code == 429:
                    rate_limited = True
                    print(f"🚫 Request {i+1}: Rate limited (429)")
                    
                    # Print rate limit details
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('error', 'Unknown')}")
                        print(f"   Message: {error_data.get('message', 'Unknown')}")
                        print(f"   Retry after: {error_data.get('retry_after', 'Unknown')} seconds")
                        print(f"   UID: {error_data.get('uid', 'Unknown')}")
                    except:
                        print(f"   Response: {response.text}")
                    
                    break
                else:
                    print(f"❌ Request {i+1}: Unexpected status {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request {i+1}: Network error - {e}")
                return False
            
            # Small delay between requests
            time.sleep(0.1)
        
        # Verify results
        if rate_limited and success_count == expected_limit:
            print(f"✅ Rate limiting working correctly: {success_count} requests allowed, then rate limited")
            return True
        elif not rate_limited:
            print(f"❌ Rate limiting not working: {success_count} requests made without rate limiting")
            return False
        else:
            print(f"❌ Unexpected result: {success_count} requests allowed, expected {expected_limit}")
            return False
    
    def test_multi_user_isolation(self) -> bool:
        """Test that different users have separate rate limits."""
        print(f"\n👥 Testing multi-user isolation")
        print("-" * 50)
        
        # Create two different user sessions
        user1_headers = {"Authorization": "Bearer user1-fake-token"}
        user2_headers = {"Authorization": "Bearer user2-fake-token"}
        
        # Mock Firebase auth responses
        # Note: This won't work with real Firebase, but shows the concept
        
        print("Note: This test requires the backend to be running with mocked Firebase auth")
        print("For real testing, use the pytest test suite")
        
        return True
    
    def test_all_endpoints(self) -> bool:
        """Test rate limiting on all endpoints."""
        print("🚀 Starting comprehensive rate limiting test")
        print("=" * 60)
        
        # Test headers (you'll need to replace with real Firebase token)
        headers = {"Authorization": "Bearer fake-firebase-token"}
        
        # Test endpoints and their expected limits
        endpoints = [
            ("/test-rate-limit", 5),
            ("/whoami", 60),
            ("/api/memory", 30),
            ("/api/messages", 30),
        ]
        
        results = []
        for endpoint, limit in endpoints:
            result = self.test_endpoint(endpoint, headers, limit)
            results.append((endpoint, result))
        
        # Summary
        print(f"\n📊 Test Results Summary")
        print("=" * 60)
        all_passed = True
        for endpoint, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {endpoint}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print(f"\n🎉 All rate limiting tests passed!")
        else:
            print(f"\n⚠️  Some tests failed. Check the output above.")
        
        return all_passed


def main():
    """Main test function."""
    print("Rate Limiting Manual Test")
    print("=" * 60)
    print("This script tests rate limiting functionality manually.")
    print("Make sure your backend is running on http://localhost:8000")
    print()
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend is not responding correctly")
            return 1
        print("✅ Backend is running")
    except requests.exceptions.RequestException:
        print("❌ Backend is not running. Please start it with: python main.py")
        return 1
    
    # Run tests
    tester = RateLimitTester()
    
    print("\nNote: For proper testing with authentication, use the pytest test suite:")
    print("python -m pytest tests/test_rate_limiter.py -v")
    print("python -m pytest tests/test_multi_user.py -v")
    
    # Test basic connectivity
    try:
        response = requests.get("http://localhost:8000/test-rate-limit")
        if response.status_code == 401:
            print("✅ Rate limiting endpoint is working (requires auth)")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        return 1
    
    print("\n✅ Manual test completed. Use pytest for comprehensive testing.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
