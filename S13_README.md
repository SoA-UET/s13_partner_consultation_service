# S13 Partner Consultation Service - Setup and Run Guide

## Overview

This is the Partner Consultation Service (S13) for the Telcenter Partner system. It handles forwarded consultations from Telcenter Core and enables human agents to communicate with customers via text and voice.

## Prerequisites

- Python 3.12+
- uv (Python package manager)
- MongoDB
- RabbitMQ

## Installation

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository and navigate to the project directory:
```bash
cd /home/lam/Desktop/UET/SoA/group/telcenter-base-service
```

3. Install dependencies:
```bash
uv sync
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and configure the following:

### Required Configuration

- **Flask Settings:**
  - `FLASK_HOST`: Host to bind Flask server (default: 0.0.0.0)
  - `FLASK_PORT`: Port for Flask server (default: 5000)
  - `SECRET_KEY`: Secret key for Flask sessions (change in production!)

- **MongoDB:**
  - `MONGODB_URI`: MongoDB connection string
  - `MONGODB_DB_NAME`: Database name (default: telcenter_partner)

- **RabbitMQ:**
  - `RABBITMQ_URL`: RabbitMQ connection URL
  - `A10A_REQUESTS_QUEUE`: Queue for receiving requests from Core
  - `A10A_RESPONSES_QUEUE`: Queue for sending responses to Core
  - `A10B_REQUESTS_QUEUE`: Queue for sending requests to Core
  - `A10B_RESPONSES_QUEUE`: Queue for receiving responses from Core

## Running the Service

### Development Mode

Run the service with:
```bash
uv run -m app
```

### Production Mode

For production deployment, consider using a process manager like systemd or supervisor:

```bash
# Using uv
uv run -m app
```

## Architecture

### Services

- **PartnerConversationService**: Manages conversations and messages in MongoDB
- **A10aConsumerService**: Consumes events from Core via RabbitMQ (A10a API)
- **A10bPublisherService**: Publishes events to Core via RabbitMQ (A10b API)

### Controllers

- **partner_consultations.py**: Flask REST API (H31 HTTP endpoints)
- **partner_socketio.py**: Socket.IO real-time communication (H31 WebSocket)

### APIs Implemented

#### HTTP REST API (H31)
- `GET /api/v1/conversations` - List all conversations
- `GET /api/v1/conversations/{id}` - Get conversation details
- `GET /api/v1/conversations/{id}/messages` - Get message history
- `POST /api/v1/conversations/{id}/messages` - Send a message

#### Socket.IO (H31)
- `consultation_request` - New consultation request notification
- `consultation_response` - Accept/reject consultation
- `new_message` - Real-time text messages
- `incoming_call` - Incoming voice call notification
- `call_pickup` - Human agent picks up call
- `call_end` - End voice call
- `audio_start`, `audio_chunk`, `audio_stop` - Real-time audio streaming

#### RabbitMQ (A10a/A10b)
- A10a: Receiving events from Core
- A10b: Sending events to Core

## Database Schema

### Collections

#### conversations
- `_id`: ObjectId (same as conversation_id from Core)
- `title`: string
- `customer_id`: string
- `status`: string (AI_AGENT_TEXTING, AI_AGENT_CALLING, FORWARDING, HUMAN_AGENT_TEXTING, HUMAN_AGENT_CALLING)
- `partner_id`: string
- `customer_satisfaction`: integer (1-5)
- `summary`: string
- `created_at`: datetime
- `updated_at`: datetime

#### messages
- `_id`: ObjectId
- `conversation_id`: string
- `sender_type`: string (CUSTOMER, AI_AGENT, HUMAN_AGENT)
- `sender_id`: string (optional, for HUMAN_AGENT only)
- `sender_name`: string (optional, for HUMAN_AGENT only)
- `content`: string
- `emotion`: string (Positive, Neutral, Negative)
- `created_at`: datetime

## Testing

### Check Service Health

```bash
# Check if Flask server is running
curl http://localhost:5000/api/v1/conversations

# Check Socket.IO connection
# Use a Socket.IO client to connect to http://localhost:5000
```

### Monitor RabbitMQ Queues

```bash
# List queues
rabbitmqctl list_queues

# Check specific queue
rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

## Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `sudo systemctl status mongod`
- Check connection string in `.env`
- Verify network access to MongoDB

### RabbitMQ Connection Issues
- Ensure RabbitMQ is running: `sudo systemctl status rabbitmq-server`
- Check connection URL in `.env`
- Verify queue names match between Core and Partner systems

### Port Already in Use
- Change `FLASK_PORT` in `.env`
- Or kill the process using the port: `lsof -ti:5000 | xargs kill -9`

## Development Notes

### Multithreading
- The service uses multithreading (not async/await) as specified
- RabbitMQ consumers run in background threads
- MessageQueueService handles thread-safe operations

### JWT Authentication
- JWT authentication is planned but not fully implemented
- The `require_auth` decorator is a placeholder
- Full implementation should follow the VERIFY.md specification

## License

[Your License Here]
