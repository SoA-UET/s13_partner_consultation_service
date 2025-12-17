from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from ...services.PartnerConversationService import PartnerConversationService
from ...services.A10bPublisherService import A10bPublisherService
import base64
import time


class PartnerSocketIOController:
    """Socket.IO controller for H31 real-time communication"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.conversation_service = PartnerConversationService()
        self.a10b_publisher = A10bPublisherService()
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """Handle client connection"""
            # TODO: Verify JWT from auth parameter
            # For now, just accept connections
            if not auth or 'token' not in auth:
                print("[SocketIO] Connection rejected: No token provided")
                return False
            
            print(f"[SocketIO] Client connected")
            return True
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            print("[SocketIO] Client disconnected")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """Handle client joining a conversation room"""
            conversation_id = data.get('conversation_id')
            if conversation_id:
                join_room(conversation_id)
                print(f"[SocketIO] Client joined room: {conversation_id}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """Handle client leaving a conversation room"""
            conversation_id = data.get('conversation_id')
            if conversation_id:
                leave_room(conversation_id)
                print(f"[SocketIO] Client left room: {conversation_id}")
        
        @self.socketio.on('consultation_response')
        def handle_consultation_response(data):
            """Handle human agent accepting/rejecting consultation request"""
            conversation_id = data.get('conversation_id')
            accepted = data.get('accepted', False)
            
            if not conversation_id:
                return
            
            # Determine status
            status = "accepted" if accepted else "rejected"
            
            # If accepted, create conversation in database
            if accepted:
                # Get conversation details from the data if provided
                # Otherwise, create with minimal info
                title = data.get('title', 'Consultation')
                customer_id = data.get('customer_id', 'unknown')
                partner_id = data.get('partner_id', 'unknown')
                customer_satisfaction = data.get('customer_satisfaction', 3)
                summary = data.get('summary', '')
                
                try:
                    self.conversation_service.create_conversation(
                        conversation_id=conversation_id,
                        title=title,
                        customer_id=customer_id,
                        partner_id=partner_id,
                        customer_satisfaction=customer_satisfaction,
                        summary=summary
                    )
                    # Join the room for this conversation
                    join_room(conversation_id)
                except Exception as e:
                    print(f"[SocketIO] Error creating conversation: {e}")
            
            # Publish response to Core
            # Note: request_id should match the original consultation_request id
            # For now, use conversation_id as request_id
            self.a10b_publisher.publish_consultation_response(
                conversation_id=conversation_id,
                status=status,
                request_id=conversation_id
            )
            
            print(f"[SocketIO] Consultation response: {status} for {conversation_id}")
        
        @self.socketio.on('call_pickup')
        def handle_call_pickup(data):
            """Handle human agent picking up a call"""
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return
            
            # Update conversation status
            self.conversation_service.update_conversation_status(
                conversation_id, "HUMAN_AGENT_CALLING"
            )
            
            # Notify Core
            self.a10b_publisher.publish_call_pickup(conversation_id)
            
            print(f"[SocketIO] Call pickup: {conversation_id}")
        
        @self.socketio.on('call_end')
        def handle_call_end(data):
            """Handle human agent ending a call"""
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return
            
            # Update conversation status
            self.conversation_service.update_conversation_status(
                conversation_id, "HUMAN_AGENT_TEXTING"
            )
            
            # Notify Core
            self.a10b_publisher.publish_call_end(conversation_id)
            
            print(f"[SocketIO] Call end: {conversation_id}")
        
        @self.socketio.on('audio_start')
        def handle_audio_start(data):
            """Handle human agent starting audio stream"""
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return
            
            # Notify Core
            self.a10b_publisher.publish_audio_start(conversation_id)
            
            print(f"[SocketIO] Audio start: {conversation_id}")
        
        @self.socketio.on('audio_chunk')
        def handle_audio_chunk(data):
            """Handle human agent sending audio chunk"""
            conversation_id = data.get('conversation_id')
            audio = data.get('audio')  # This should be bytes
            
            if not conversation_id or not audio:
                return
            
            # Encode audio as base64 for RabbitMQ transmission
            audio_base64 = base64.b64encode(audio).decode('utf-8')
            
            # Forward to Core
            self.a10b_publisher.publish_audio_chunk(conversation_id, audio_base64)
        
        @self.socketio.on('audio_stop')
        def handle_audio_stop(data):
            """Handle human agent stopping audio stream"""
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return
            
            # Notify Core
            self.a10b_publisher.publish_audio_stop(conversation_id)
            
            print(f"[SocketIO] Audio stop: {conversation_id}")


def create_socketio_controller(socketio: SocketIO):
    """Factory function to create and initialize Socket.IO controller"""
    return PartnerSocketIOController(socketio)
