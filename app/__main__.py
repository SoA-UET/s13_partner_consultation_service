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
from .services.JWTVerificationService import (
    init_jwt_service,
    shutdown_jwt_service,
    get_jwt_service
)
from .controllers.v1.partner_consultations import partner_consultations_bp
from .controllers.v1.partner_socketio import create_socketio_controller
import logging
import atexit
import signal
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def cleanup():
    """Cleanup function called on shutdown"""
    logger.info("[S13] Shutting down services...")
    shutdown_jwt_service()
    logger.info("[S13] Cleanup complete")


def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info(f"[S13] Received signal {sig} - shutting down...")
    cleanup()
    sys.exit(0)


def main():
    """Main entry point"""
    logger.info("[S13] Starting Partner Consultation Service...")
    
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create Flask app
    app = create_app()
    
    # Initialize JWT verification service
    try:
        logger.info("[S13] Initializing JWT verification service...")
        init_jwt_service()
        logger.info("[S13] JWT verification service initialized")
        
        # Add health check endpoint to show JWKS cache status
        @app.route('/health/jwt')
        def jwt_health():
            try:
                jwt_service = get_jwt_service()
                stats = jwt_service.get_cache_stats()
                return {
                    'status': 'healthy',
                    'jwks_cache': stats
                }, 200
            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'error': str(e)
                }, 500
                
    except Exception as e:
        logger.error(f"[S13] Failed to initialize JWT service: {e}", exc_info=True)
        logger.warning("[S13] Continuing without JWT authentication...")
    
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
    logger.info("[S13] Starting A10a consumer threads...")
    a10a_consumer.start()
    
    # Get host and port from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    # Start Flask server with Socket.IO
    logger.info(f"[S13] Starting Flask server on {host}:{port}...")
    socketio.run(app, host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
