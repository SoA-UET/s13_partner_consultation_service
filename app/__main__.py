#!/usr/bin/env python3
"""
Telcenter Partner - Partner Consultation Service (S13)
Main entry point
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv
import os
import threading

from .services.PartnerConversationService import PartnerConversationService
from .services.A10bPublisherService import A10bPublisherService
from .services.A10aConsumerService import A10aConsumerService
from .controllers.v1.partner_consultations import partner_consultations_bp
from .controllers.v1.partner_socketio import create_socketio_controller


# Load environment variables
load_dotenv()


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(partner_consultations_bp)
    
    return app


def main():
    """Main entry point"""
    print("[S13] Starting Partner Consultation Service...")
    
    # Create Flask app
    app = create_app()
    
    # Create Socket.IO server
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Initialize Socket.IO controller
    socketio_controller = create_socketio_controller(socketio)
    
    # Initialize services
    conversation_service = PartnerConversationService()
    a10b_publisher = A10bPublisherService()
    
    # Create A10a consumer with Socket.IO reference
    a10a_consumer = A10aConsumerService(
        conversation_service=conversation_service,
        a10b_publisher=a10b_publisher,
        socketio_server=socketio
    )
    
    # Start A10a consumer in background threads
    print("[S13] Starting A10a consumer threads...")
    a10a_consumer.start()
    
    # Get host and port from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    # Start Flask server with Socket.IO
    print(f"[S13] Starting Flask server on {host}:{port}...")
    socketio.run(app, host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
