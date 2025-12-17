from .MessageQueueService import MessageQueueService
from .PartnerConversationService import PartnerConversationService
from .A10bPublisherService import A10bPublisherService
import os
import threading


class A10aConsumerService:
    """Service for consuming events from Core via A10a API"""
    
    def __init__(self, conversation_service: PartnerConversationService, 
                 a10b_publisher: A10bPublisherService,
                 socketio_server=None):
        """
        Args:
            conversation_service: Service for managing conversations
            a10b_publisher: Service for publishing events to Core
            socketio_server: Socket.IO server instance for real-time communication
        """
        self.conversation_service = conversation_service
        self.a10b_publisher = a10b_publisher
        self.socketio_server = socketio_server
        
        self.mq_service = MessageQueueService()
        self.mq_lock = threading.Lock()
        
        # Queue names from environment or defaults
        self.a10a_requests_queue = os.getenv("A10A_REQUESTS_QUEUE", "telcenter_a10a_requests")
        self.a10a_responses_queue = os.getenv("A10A_RESPONSES_QUEUE", "telcenter_a10a_responses")
        
        # Declare queues
        self.mq_service.declare_queue(self.a10a_requests_queue)
        self.mq_service.declare_queue(self.a10a_responses_queue)
        
        self.threads = []
        self.num_threads = int(os.getenv("A10A_CONSUMER_THREADS", "4"))
    
    def start(self):
        """Start consuming messages from A10a queue"""
        self.threads = [
            threading.Thread(target=self._consume_in_background, daemon=True)
            for _ in range(self.num_threads)
        ]
        for t in self.threads:
            t.start()
    
    def wait(self):
        """Wait for all threads to complete"""
        for t in self.threads:
            t.join()
    
    def _consume_in_background(self):
        """Background consumer thread"""
        with self.mq_lock:
            mq = self.mq_service.clone()
        mq.declare_queue(self.a10a_requests_queue)
        mq.declare_queue(self.a10a_responses_queue)
        mq.register_callback(self.a10a_requests_queue, self._handle_message)
        mq.start_consuming()
    
    def _handle_message(self, message: dict):
        """Handle incoming message from A10a"""
        # Check if it's a method call or event
        if "method" in message:
            self._handle_method(message)
        elif "event" in message:
            self._handle_event(message)
    
    def _handle_method(self, message: dict):
        """Handle method calls from A10a"""
        method_name = message.get("method", "")
        message_id = message.get("id", "")
        
        result_status = "success"
        result_content = None
        
        try:
            if method_name == "consultation_request":
                result_content = self._handle_consultation_request(message.get("params", {}))
            else:
                raise ValueError(f"Unknown method: {method_name}")
        except Exception as e:
            result_status = "error"
            result_content = str(e)
        
        # Send response
        response = {
            "id": message_id,
            "result": {
                "status": result_status,
                "content": result_content
            }
        }
        self.mq_service.publish_message(self.a10a_responses_queue, response)
    
    def _handle_event(self, message: dict):
        """Handle events from A10a"""
        event_name = message.get("event", "")
        data = message.get("data", {})
        
        try:
            if event_name == "new_message":
                self._handle_new_message(data)
            elif event_name == "call_start":
                self._handle_call_start(data)
            elif event_name == "call_end":
                self._handle_call_end(data)
            elif event_name == "audio_start":
                self._handle_audio_start(data)
            elif event_name == "audio_chunk":
                self._handle_audio_chunk(data)
            elif event_name == "audio_stop":
                self._handle_audio_stop(data)
        except Exception as e:
            print(f"[A10aConsumer] Error handling event {event_name}: {e}")
    
    # Method handlers
    
    def _handle_consultation_request(self, params: dict):
        """Handle consultation_request method"""
        partner_id = params.get("partner_id", "")
        customer = params.get("customer", {})
        conversation = params.get("conversation", {})
        
        # Store conversation details temporarily (will be fully created when accepted)
        # Note: We don't create the conversation yet - only after acceptance
        
        # Notify human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('consultation_request', {
                "conversation_id": conversation.get("id"),
                "title": conversation.get("title"),
                "customer_satisfaction": conversation.get("customer_satisfaction"),
                "summary": conversation.get("summary")
            })
        
        return "OK"
    
    # Event handlers
    
    def _handle_new_message(self, data: dict):
        """Handle new_message event"""
        conversation_id = data.get("conversation_id", "")
        message = data.get("message", {})
        
        # Store message in database
        self.conversation_service.create_message(
            conversation_id=conversation_id,
            sender_type="CUSTOMER",
            content=message.get("content", ""),
            message_id=message.get("id"),
            emotion="Neutral"
        )
        
        # Notify human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('new_message', {
                "conversation_id": conversation_id,
                "timestamp": int(message.get("created_at", 0)),
                "sender_type": "CUSTOMER",
                "content": message.get("content", "")
            }, room=conversation_id)
    
    def _handle_call_start(self, data: dict):
        """Handle call_start event"""
        conversation_id = data.get("conversation_id", "")
        
        # Notify human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('incoming_call', {
                "conversation_id": conversation_id
            }, room=conversation_id)
    
    def _handle_call_end(self, data: dict):
        """Handle call_end event from customer"""
        conversation_id = data.get("conversation_id", "")
        
        # Update conversation status
        self.conversation_service.update_conversation_status(
            conversation_id, "HUMAN_AGENT_TEXTING"
        )
        
        # Notify human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('call_end', {
                "conversation_id": conversation_id
            }, room=conversation_id)
    
    def _handle_audio_start(self, data: dict):
        """Handle audio_start event"""
        conversation_id = data.get("conversation_id", "")
        
        # Forward to human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('audio_start', {
                "conversation_id": conversation_id
            }, room=conversation_id)
    
    def _handle_audio_chunk(self, data: dict):
        """Handle audio_chunk event"""
        conversation_id = data.get("conversation_id", "")
        audio_data = data.get("audio_data", "")
        
        # Forward to human agent via Socket.IO (as binary)
        # Note: The audio_data is base64 encoded in RabbitMQ, but will be
        # decoded and sent as binary via Socket.IO
        if self.socketio_server:
            import base64
            audio_bytes = base64.b64decode(audio_data)
            self.socketio_server.emit('audio_chunk', {
                "conversation_id": conversation_id,
                "timestamp": int(data.get("timestamp", 0)),
                "audio": audio_bytes
            }, room=conversation_id)
    
    def _handle_audio_stop(self, data: dict):
        """Handle audio_stop event"""
        conversation_id = data.get("conversation_id", "")
        
        # Forward to human agent via Socket.IO
        if self.socketio_server:
            self.socketio_server.emit('audio_stop', {
                "conversation_id": conversation_id
            }, room=conversation_id)
