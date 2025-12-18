#!/usr/bin/env python3
"""
Test script for JWT verification implementation.

This script demonstrates:
1. How to test JWT endpoints with authentication
2. How the JWT verification works
3. How to handle authentication errors

Prerequisites:
- S13 service must be running
- Identity Service must be available and returning JWKS
- Valid JWT token from Identity Service
"""

import requests
import sys
import json


# Configuration
S13_BASE_URL = "http://localhost:5013"
IDENTITY_SERVICE_URL = "http://localhost:5010"


def test_without_jwt():
    """Test endpoint without JWT - should return 401"""
    print("\n" + "="*60)
    print("TEST 1: Request without JWT (should return 401)")
    print("="*60)
    
    url = f"{S13_BASE_URL}/api/v1/conversations"
    response = requests.get(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("✅ Test passed - Correctly rejected request without JWT")
    else:
        print("❌ Test failed - Expected 401 Unauthorized")
    
    return response.status_code == 401


def test_with_invalid_jwt():
    """Test endpoint with invalid JWT - should return 401"""
    print("\n" + "="*60)
    print("TEST 2: Request with invalid JWT (should return 401)")
    print("="*60)
    
    url = f"{S13_BASE_URL}/api/v1/conversations"
    headers = {
        "Authorization": "Bearer invalid.jwt.token"
    }
    response = requests.get(url, headers=headers)
    
    print(f"URL: {url}")
    print(f"JWT: invalid.jwt.token")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 401:
        print("✅ Test passed - Correctly rejected invalid JWT")
    else:
        print("❌ Test failed - Expected 401 Unauthorized")
    
    return response.status_code == 401


def test_with_valid_jwt(jwt_token):
    """Test endpoint with valid JWT - should return 200"""
    print("\n" + "="*60)
    print("TEST 3: Request with valid JWT (should return 200)")
    print("="*60)
    
    url = f"{S13_BASE_URL}/api/v1/conversations"
    headers = {
        "Authorization": f"Bearer {jwt_token}"
    }
    response = requests.get(url, headers=headers)
    
    print(f"URL: {url}")
    print(f"JWT: {jwt_token[:50]}...")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✅ Test passed - Request authenticated successfully")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("❌ Test failed - Expected 200 OK")
    
    return response.status_code == 200


def test_jwks_cache_health():
    """Test JWKS cache health endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Check JWKS cache health")
    print("="*60)
    
    url = f"{S13_BASE_URL}/health/jwt"
    response = requests.get(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'healthy':
            print("✅ JWT service is healthy")
            cache = data.get('jwks_cache', {})
            print(f"   - Cached keys: {cache.get('cached_keys', 0)}")
            print(f"   - Key IDs: {cache.get('key_ids', [])}")
            print(f"   - Last fetch: {cache.get('last_fetch', 'N/A')}")
            print(f"   - TTL: {cache.get('ttl_seconds', 0)} seconds")
            return True
        else:
            print(f"❌ JWT service is unhealthy: {data.get('error')}")
            return False
    else:
        print("❌ Failed to check JWT health")
        return False


def test_send_message_with_jwt(jwt_token, conversation_id="test-conversation-1"):
    """Test sending a message with JWT"""
    print("\n" + "="*60)
    print("TEST 5: Send message with valid JWT")
    print("="*60)
    
    url = f"{S13_BASE_URL}/api/v1/conversations/{conversation_id}/messages"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    data = {
        "content": "Test message from JWT authenticated user"
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code in [200, 201]:
        print("✅ Test passed - Message sent with authenticated user info")
    else:
        print(f"❌ Test failed - Expected 200/201, got {response.status_code}")
    
    return response.status_code in [200, 201]


def check_services():
    """Check if required services are running"""
    print("\n" + "="*60)
    print("CHECKING SERVICES")
    print("="*60)
    
    services_ok = True
    
    # Check S13 service
    try:
        response = requests.get(f"{S13_BASE_URL}/health/jwt", timeout=5)
        print(f"✅ S13 service is running at {S13_BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"❌ S13 service is not running at {S13_BASE_URL}")
        print("   Please start the service with: ./start_s13.sh")
        services_ok = False
    except Exception as e:
        print(f"⚠️  Error checking S13 service: {e}")
    
    # Check Identity Service
    try:
        response = requests.get(f"{IDENTITY_SERVICE_URL}/.well-known/jwks.json", timeout=5)
        if response.status_code == 200:
            print(f"✅ Identity Service is running at {IDENTITY_SERVICE_URL}")
            jwks = response.json()
            print(f"   - Available keys: {jwks.get('kid', 'N/A')}")
        else:
            print(f"⚠️  Identity Service returned {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Identity Service is not running at {IDENTITY_SERVICE_URL}")
        print("   Please ensure Identity Service is running and JWKS endpoint is accessible")
        services_ok = False
    except Exception as e:
        print(f"⚠️  Error checking Identity Service: {e}")
    
    return services_ok


def main():
    """Main test runner"""
    print("="*60)
    print("S13 JWT Authentication Test Suite")
    print("="*60)
    
    # Check services
    if not check_services():
        print("\n❌ Required services are not running. Please start them first.")
        return 1
    
    # Run tests that don't require JWT
    test_without_jwt()
    test_with_invalid_jwt()
    test_jwks_cache_health()
    
    # Tests that require a valid JWT
    print("\n" + "="*60)
    print("TESTS REQUIRING VALID JWT")
    print("="*60)
    print("\nTo test with a valid JWT, you need to:")
    print("1. Obtain a JWT from the Identity Service (S06 or S10)")
    print("2. Run this script with the JWT as an argument:")
    print(f"   python {sys.argv[0]} <your-jwt-token>")
    
    if len(sys.argv) > 1:
        jwt_token = sys.argv[1]
        print(f"\n✅ JWT token provided: {jwt_token[:50]}...")
        
        test_with_valid_jwt(jwt_token)
        test_send_message_with_jwt(jwt_token)
    else:
        print("\n⚠️  No JWT token provided - skipping authenticated tests")
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
