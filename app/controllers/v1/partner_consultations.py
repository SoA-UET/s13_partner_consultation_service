from flask import Blueprint, request, jsonify
from flask_restx import Api, Resource, fields, Namespace
from ...services.PartnerConversationService import PartnerConversationService
from ...services.A10bPublisherService import A10bPublisherService
from ...utils.db import serialize_mongo_doc
from ..common.auth import require_jwt
from datetime import datetime
import os


# Create blueprint
partner_consultations_bp = Blueprint('partner_consultations', __name__)
api = Api(partner_consultations_bp, version='1.0', 
          title='Partner Consultation API',
          description='H31 API for Partner Consultation Service',
          doc='/docs')

# Create namespace
ns = Namespace('api/v1', description='Partner consultation operations')
api.add_namespace(ns, path='/api/v1')

# Initialize services
conversation_service = PartnerConversationService()
a10b_publisher = A10bPublisherService()


# Models for Swagger documentation
conversation_list_model = ns.model('ConversationList', {
    'id': fields.String(description='Conversation ID'),
    'title': fields.String(description='Conversation title'),
})

conversation_detail_model = ns.model('ConversationDetail', {
    'id': fields.String(description='Conversation ID'),
    'title': fields.String(description='Conversation title'),
    'customer_id': fields.String(description='Customer ID'),
    'status': fields.String(description='Conversation status'),
    'partner_id': fields.String(description='Partner ID'),
    'customer_satisfaction': fields.Integer(description='Customer satisfaction (1-5)'),
    'summary': fields.String(description='Conversation summary'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Update timestamp'),
})

message_model = ns.model('Message', {
    'id': fields.String(description='Message ID'),
    'conversation_id': fields.String(description='Conversation ID'),
    'sender_type': fields.String(description='Sender type: CUSTOMER, AI_AGENT, HUMAN_AGENT'),
    'sender_id': fields.String(description='Sender ID (for HUMAN_AGENT only)'),
    'sender_name': fields.String(description='Sender name (for HUMAN_AGENT only)'),
    'content': fields.String(description='Message content'),
    'emotion': fields.String(description='Emotion: Positive, Neutral, Negative'),
    'created_at': fields.String(description='Creation timestamp'),
})

message_input_model = ns.model('MessageInput', {
    'content': fields.String(required=True, description='Message content'),
})


@ns.route('/conversations')
class ConversationListResource(Resource):
    @ns.doc('list_conversations')
    @ns.marshal_list_with(conversation_list_model, envelope='content')
    @require_jwt()
    def get(self):
        """Get all past conversations (requires JWT authentication)"""
        conversations = conversation_service.get_all_conversations()
        return [serialize_mongo_doc(conv) for conv in conversations]


@ns.route('/conversations/<string:conversation_id>')
class ConversationDetailResource(Resource):
    @ns.doc('get_conversation')
    @ns.marshal_with(conversation_detail_model, envelope='content')
    @require_jwt()
    def get(self, conversation_id):
        """Get details of a conversation (requires JWT authentication)"""
        conversation = conversation_service.get_conversation_by_id(conversation_id)
        if not conversation:
            return {'error': 'Conversation not found'}, 404
        return serialize_mongo_doc(conversation)


@ns.route('/conversations/<string:conversation_id>/messages')
class ConversationMessagesResource(Resource):
    @ns.doc('get_messages')
    @ns.marshal_list_with(message_model, envelope='content')
    @require_jwt()
    def get(self, conversation_id):
        """Retrieve full message history of a conversation (requires JWT authentication)"""
        # Get pagination parameters
        page_number = int(request.args.get('pageNumber', 0))
        page_size = int(request.args.get('pageSize', 50))
        search = request.args.get('search', None)
        
        messages = conversation_service.get_messages_by_conversation_id(
            conversation_id, page_number, page_size, search
        )
        return [serialize_mongo_doc(msg) for msg in messages]
    
    @ns.doc('send_message')
    @ns.expect(message_input_model)
    @ns.marshal_with(message_model, envelope='content')
    @require_jwt()
    def post(self, conversation_id):
        """Send a text message from consultant (human agent) to customer (requires JWT authentication)"""
        # Extract sender_id and sender_name from JWT (attached to request by require_jwt decorator)
        sender_id = request.jwt_user_id
        sender_name = request.jwt_full_name
        
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return {'error': 'Content is required'}, 400
        
        # Create message in database
        message = conversation_service.create_message(
            conversation_id=conversation_id,
            sender_type="HUMAN_AGENT",
            content=content,
            sender_id=sender_id,
            sender_name=sender_name
        )
        
        # Publish to Core via A10b
        a10b_publisher.publish_new_message(
            conversation_id=conversation_id,
            message_id=str(message['_id']),
            content=content,
            created_at=message['created_at'].isoformat()
        )
        
        return serialize_mongo_doc(message)
