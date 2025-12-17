from .MessageQueueService import MessageQueueService
from .PartnerConversationService import PartnerConversationService
import os
import threading


class A10bPublisherService:
    """Service for publishing events to Core via A10b API"""
    
    def __init__(self):
        self.mq_service = MessageQueueService()
        self.mq_lock = threading.Lock()
        
        # Queue names from environment or defaults
        self.a10b_requests_queue = os.getenv("A10B_REQUESTS_QUEUE", "telcenter_a10b_requests")
        self.a10b_responses_queue = os.getenv("A10B_RESPONSES_QUEUE", "telcenter_a10b_responses")
        
        # Declare queues
        self.mq_service.declare_queue(self.a10b_requests_queue)
        self.mq_service.declare_queue(self.a10b_responses_queue)
    
    def publish_consultation_response(self, conversation_id: str, status: str, request_id: str):
        """Publish consultation response to Core (A10b method)"""
        message = {
            "method": "consultation_response",
            "params": {
                "conversation_id": conversation_id,
                "status": status  # "accepted" or "rejected"
            },
            "id": request_id
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_call_pickup(self, conversation_id: str):
        """Publish call_pickup event to Core (A10b event)"""
        message = {
            "event": "call_pickup",
            "data": {
                "conversation_id": conversation_id
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_call_end(self, conversation_id: str):
        """Publish call_end event to Core (A10b event)"""
        message = {
            "event": "call_end",
            "data": {
                "conversation_id": conversation_id
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_audio_start(self, conversation_id: str):
        """Publish audio_start event to Core (A10b event)"""
        message = {
            "event": "audio_start",
            "data": {
                "conversation_id": conversation_id
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_audio_chunk(self, conversation_id: str, audio_data: str):
        """Publish audio_chunk event to Core (A10b event)
        
        Args:
            conversation_id: ID of the conversation
            audio_data: base64-encoded PCM audio data (640 bytes)
        """
        message = {
            "event": "audio_chunk",
            "data": {
                "conversation_id": conversation_id,
                "audio_data": audio_data
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_audio_stop(self, conversation_id: str):
        """Publish audio_stop event to Core (A10b event)"""
        message = {
            "event": "audio_stop",
            "data": {
                "conversation_id": conversation_id
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
    
    def publish_new_message(self, conversation_id: str, message_id: str, 
                          content: str, created_at: str):
        """Publish new_message event to Core (A10b event)"""
        message = {
            "event": "new_message",
            "data": {
                "conversation_id": conversation_id,
                "message": {
                    "id": message_id,
                    "content": content,
                    "created_at": created_at
                }
            }
        }
        with self.mq_lock:
            self.mq_service.publish_message(self.a10b_requests_queue, message)
