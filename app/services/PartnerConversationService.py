from ..utils.db import get_mongo_db, str_to_objectid
from bson import ObjectId
from datetime import datetime
from typing import Optional


class PartnerConversationService:
    """Service for managing conversations and messages in Partner system (S13)"""
    
    def __init__(self):
        self.db = get_mongo_db()
        self.conversations = self.db['conversations']
        self.messages = self.db['messages']
    
    # Conversation operations
    
    def create_conversation(self, conversation_id: str, title: str, customer_id: str, 
                          partner_id: str, customer_satisfaction: int, summary: str):
        """Create a new conversation with the given ID from Core"""
        now = datetime.now()
        conversation_doc = {
            "_id": str_to_objectid(conversation_id),
            "title": title,
            "customer_id": customer_id,
            "status": "HUMAN_AGENT_TEXTING",
            "partner_id": partner_id,
            "customer_satisfaction": customer_satisfaction,
            "summary": summary,
            "created_at": now,
            "updated_at": now,
        }
        self.conversations.insert_one(conversation_doc)
        return conversation_doc
    
    def get_conversation_by_id(self, conversation_id: str):
        """Get conversation by ID"""
        object_id = str_to_objectid(conversation_id)
        if not object_id:
            return None
        return self.conversations.find_one({"_id": object_id})
    
    def get_all_conversations(self):
        """Get all conversations (for listing)"""
        return list(self.conversations.find({}, {"_id": 1, "title": 1}).sort("updated_at", -1))
    
    def update_conversation_status(self, conversation_id: str, status: str):
        """Update conversation status"""
        object_id = str_to_objectid(conversation_id)
        if not object_id:
            return None
        
        self.conversations.update_one(
            {"_id": object_id},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
        return self.get_conversation_by_id(conversation_id)
    
    # Message operations
    
    def create_message(self, conversation_id: str, sender_type: str, content: str,
                      sender_id: Optional[str] = None, sender_name: Optional[str] = None,
                      emotion: str = "Neutral", message_id: Optional[str] = None):
        """Create a new message"""
        now = datetime.now()
        message_doc = {
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "content": content,
            "emotion": emotion,
            "created_at": now,
        }
        
        if message_id:
            message_doc["_id"] = str_to_objectid(message_id)
        
        if sender_id:
            message_doc["sender_id"] = sender_id
        
        if sender_name:
            message_doc["sender_name"] = sender_name
        
        result = self.messages.insert_one(message_doc)
        message_doc["_id"] = result.inserted_id
        
        # Update conversation's updated_at timestamp
        conv_object_id = str_to_objectid(conversation_id)
        if conv_object_id:
            self.conversations.update_one(
                {"_id": conv_object_id},
                {"$set": {"updated_at": now}}
            )
        
        return message_doc
    
    def get_messages_by_conversation_id(self, conversation_id: str, 
                                       page_number: int = 0, 
                                       page_size: int = 50,
                                       search: Optional[str] = None):
        """Get all messages for a conversation with pagination"""
        filters = {"conversation_id": conversation_id}
        
        if search:
            filters["content"] = {"$regex": search, "$options": "i"}
        
        skip = page_number * page_size
        messages = list(
            self.messages.find(filters)
            .sort("created_at", 1)
            .skip(skip)
            .limit(page_size)
        )
        return messages
