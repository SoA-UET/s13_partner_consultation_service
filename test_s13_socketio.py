#!/usr/bin/env python3
"""
Example Socket.IO client for S13 Partner Consultation Service

This demonstrates how a Partner Portal frontend would connect
to the S13 service using Socket.IO for real-time communication.

Install python-socketio first:
  uv pip install python-socketio[client]
"""

import socketio
import time
import base64

# Configuration
SERVER_URL = "http://localhost:5000"
# TODO: Replace with actual JWT token
AUTH_TOKEN = "your-jwt-token-here"


def create_client():
    """Create and configure Socket.IO client"""
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("[Connected] Successfully connected to S13 service")
        print("  Ready to receive real-time updates")
    
    @sio.event
    def disconnect():
        print("[Disconnected] Connection to S13 service closed")
    
    @sio.on('consultation_request')
    def on_consultation_request(data):
        """Receive new consultation request from Core"""
        print("\n[Event] New Consultation Request:")
        print(f"  Conversation ID: {data.get('conversation_id')}")
        print(f"  Title: {data.get('title')}")
        print(f"  Satisfaction: {data.get('customer_satisfaction')}/5")
        print(f"  Summary: {data.get('summary')}")
        print("")
        
        # Example: Auto-accept consultation (for testing)
        # In real application, human agent would decide
        # accept_consultation(sio, data.get('conversation_id'))
    
    @sio.on('new_message')
    def on_new_message(data):
        """Receive new message from customer"""
        print("\n[Event] New Message:")
        print(f"  Conversation: {data.get('conversation_id')}")
        print(f"  From: {data.get('sender_type')}")
        print(f"  Content: {data.get('content')}")
        print("")
    
    @sio.on('incoming_call')
    def on_incoming_call(data):
        """Receive incoming call notification"""
        print("\n[Event] Incoming Call:")
        print(f"  Conversation: {data.get('conversation_id')}")
        print("  🔔 Ring ring! Customer is calling...")
        print("")
        
        # Example: Auto-pickup (for testing)
        # In real application, human agent would click to answer
        # pickup_call(sio, data.get('conversation_id'))
    
    @sio.on('call_end')
    def on_call_end(data):
        """Receive call end notification"""
        print("\n[Event] Call Ended:")
        print(f"  Conversation: {data.get('conversation_id')}")
        print("")
    
    @sio.on('audio_start')
    def on_audio_start(data):
        """Receive audio stream start notification"""
        print(f"[Audio] Customer started speaking (conv: {data.get('conversation_id')})")
    
    @sio.on('audio_chunk')
    def on_audio_chunk(data):
        """Receive audio chunk from customer"""
        # In real application, play this audio chunk
        audio_data = data.get('audio')
        if audio_data:
            print(".", end="", flush=True)  # Progress indicator
    
    @sio.on('audio_stop')
    def on_audio_stop(data):
        """Receive audio stream stop notification"""
        print(f"\n[Audio] Customer stopped speaking (conv: {data.get('conversation_id')})")
    
    return sio


def accept_consultation(sio, conversation_id):
    """Accept a consultation request"""
    print(f"\n[Action] Accepting consultation: {conversation_id}")
    sio.emit('consultation_response', {
        'conversation_id': conversation_id,
        'accepted': True
    })
    
    # Join the conversation room
    sio.emit('join_room', {
        'conversation_id': conversation_id
    })


def reject_consultation(sio, conversation_id):
    """Reject a consultation request"""
    print(f"\n[Action] Rejecting consultation: {conversation_id}")
    sio.emit('consultation_response', {
        'conversation_id': conversation_id,
        'accepted': False
    })


def pickup_call(sio, conversation_id):
    """Pick up an incoming call"""
    print(f"\n[Action] Picking up call: {conversation_id}")
    sio.emit('call_pickup', {
        'conversation_id': conversation_id
    })


def end_call(sio, conversation_id):
    """End a call"""
    print(f"\n[Action] Ending call: {conversation_id}")
    sio.emit('call_end', {
        'conversation_id': conversation_id
    })


def send_audio_chunk(sio, conversation_id, audio_bytes):
    """Send audio chunk to customer"""
    # Audio should be exactly 640 bytes of PCM data
    sio.emit('audio_chunk', {
        'conversation_id': conversation_id,
        'timestamp': int(time.time() * 1000),
        'audio': audio_bytes  # Raw bytes, not base64
    })


def main():
    print("=" * 60)
    print("S13 Partner Consultation Service - Socket.IO Client")
    print("=" * 60)
    print("")
    
    # Create client
    sio = create_client()
    
    # Connect with JWT authentication
    try:
        print(f"Connecting to {SERVER_URL}...")
        sio.connect(SERVER_URL, auth={'token': AUTH_TOKEN})
        
        print("\nListening for events... Press Ctrl+C to exit")
        print("-" * 60)
        
        # Keep connection alive
        sio.wait()
        
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. S13 service is running (uv run -m app)")
        print("  2. AUTH_TOKEN is valid")
        print("  3. Server URL is correct")
    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
