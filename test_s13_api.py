#!/usr/bin/env python3
"""
Example script to test S13 Partner Consultation Service APIs

This script demonstrates how to interact with the S13 service.
Run after starting the service with: uv run -m app
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
# TODO: Replace with actual JWT token
AUTH_TOKEN = "your-jwt-token-here"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


def test_list_conversations():
    """Test GET /api/v1/conversations"""
    print("\n=== Test: List Conversations ===")
    response = requests.get(f"{BASE_URL}/api/v1/conversations", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('content', []))} conversations")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
    return response


def test_get_conversation(conversation_id):
    """Test GET /api/v1/conversations/{id}"""
    print(f"\n=== Test: Get Conversation {conversation_id} ===")
    response = requests.get(
        f"{BASE_URL}/api/v1/conversations/{conversation_id}", 
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
    return response


def test_get_messages(conversation_id):
    """Test GET /api/v1/conversations/{id}/messages"""
    print(f"\n=== Test: Get Messages for {conversation_id} ===")
    response = requests.get(
        f"{BASE_URL}/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        params={"pageNumber": 0, "pageSize": 10}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('content', []))} messages")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
    return response


def test_send_message(conversation_id, content):
    """Test POST /api/v1/conversations/{id}/messages"""
    print(f"\n=== Test: Send Message to {conversation_id} ===")
    payload = {"content": content}
    response = requests.post(
        f"{BASE_URL}/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.text}")
    return response


def main():
    print("=" * 60)
    print("S13 Partner Consultation Service - API Test")
    print("=" * 60)
    
    # Test listing conversations
    test_list_conversations()
    
    # If you have a specific conversation ID to test, uncomment and modify:
    # conversation_id = "676081d3f8e123456789abcd"
    # test_get_conversation(conversation_id)
    # test_get_messages(conversation_id)
    # test_send_message(conversation_id, "Hello from human agent!")
    
    print("\n" + "=" * 60)
    print("Note: Replace AUTH_TOKEN with a valid JWT to test properly")
    print("=" * 60)


if __name__ == "__main__":
    main()
