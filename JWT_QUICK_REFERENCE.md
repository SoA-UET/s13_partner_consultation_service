# JWT Authentication - Quick Reference

## Overview

The S13 Partner Consultation Service now has **full JWT authentication** implemented according to the VERIFY.md specification.

## Quick Start

### 1. Configure Identity Service URL

Edit your `.env` file:

```bash
IDENTITY_SERVICE_URL=http://localhost:5010
JWKS_TTL_IN_MINUTES=10
JWT_CLOCK_SKEW_SECONDS=60
```

### 2. Start the Service

```bash
./start_s13.sh
```

The service will automatically:
- Fetch JWKS from Identity Service on startup
- Start background JWKS refresh thread (every 10 minutes)
- Protect all HTTP REST endpoints with JWT authentication

### 3. Make Authenticated Requests

All HTTP REST API endpoints now require JWT authentication:

```bash
# Get conversations (requires JWT)
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:5013/api/v1/conversations

# Get conversation details (requires JWT)
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:5013/api/v1/conversations/conv-123

# Get messages (requires JWT)
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:5013/api/v1/conversations/conv-123/messages

# Send message (requires JWT)
curl -X POST \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"content": "Hello customer"}' \
     http://localhost:5013/api/v1/conversations/conv-123/messages
```

### 4. Test JWT Authentication

```bash
# Test without JWT (should return 401)
python test_jwt_auth.py

# Test with valid JWT (should return 200)
python test_jwt_auth.py <your-jwt-token>
```

### 5. Monitor JWKS Cache

```bash
curl http://localhost:5013/health/jwt
```

Response:
```json
{
  "status": "healthy",
  "jwks_cache": {
    "cached_keys": 1,
    "key_ids": ["uuid-of-key"],
    "last_fetch": "2025-12-18T10:30:00Z",
    "ttl_seconds": 600
  }
}
```

## How It Works

1. **Client** sends request with `Authorization: Bearer <JWT>` header
2. **@require_jwt() decorator** extracts and verifies JWT:
   - Parse header (check alg=RS256, extract kid)
   - Resolve public key from cache (NO refresh on missing key)
   - Verify signature using RS256
   - Validate claims (exp, iat, sub, full_name, email, permissions)
3. **User info** is attached to Flask request:
   - `request.jwt_user_id` - User ID
   - `request.jwt_full_name` - User's name
   - `request.jwt_email` - User's email
   - `request.jwt_permissions` - List of permissions
4. **Route handler** accesses authenticated user info

## Key Features

✅ **JWKS Fetching**: Automatic fetch from Identity Service  
✅ **TTL-based Caching**: Efficient 10-minute cache with background refresh  
✅ **RS256 Verification**: Industry-standard RSA signature verification  
✅ **Claim Validation**: Comprehensive validation of all required claims  
✅ **DoS Prevention**: Strict no-refresh-on-failure policy  
✅ **Permission Support**: Fine-grained authorization (ready for future use)  
✅ **Thread-Safe**: Concurrent request handling  
✅ **Graceful Degradation**: Continues with cached keys if refresh fails  

## Protected Endpoints

All HTTP REST endpoints are now protected:

- ✅ `GET /api/v1/conversations`
- ✅ `GET /api/v1/conversations/{id}`
- ✅ `GET /api/v1/conversations/{id}/messages`
- ✅ `POST /api/v1/conversations/{id}/messages`

Socket.IO endpoints are **not authenticated** (as specified in H31).

## User Info in Routes

In your route handlers, access authenticated user info:

```python
@app.route('/api/v1/conversations/<conversation_id>/messages', methods=['POST'])
@require_jwt()
def send_message(conversation_id):
    # User info attached by decorator
    sender_id = request.jwt_user_id
    sender_name = request.jwt_full_name
    sender_email = request.jwt_email
    permissions = request.jwt_permissions
    
    # Use authenticated user info
    message = create_message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_name=sender_name,
        content=request.json['content']
    )
    
    return jsonify(message)
```

## Permission-Based Authorization (Future)

The system supports permission-based authorization:

```python
# Require specific permissions
@require_jwt(['conversations.read', 'conversations.write'])
def handle_conversation():
    # Only users with BOTH permissions can access
    ...

# Check permissions in route handler
@require_jwt()
def handle_resource():
    if check_permission('admin.delete'):
        # Can delete
        ...
    elif check_permission('resource.write'):
        # Can write only
        ...
```

## Error Responses

### 401 Unauthorized

Returned when JWT is missing, invalid, or expired:

```json
{
  "error": "Unauthorized",
  "message": "JWT verification failed: <reason>"
}
```

### 403 Forbidden

Returned when user lacks required permissions:

```json
{
  "error": "Forbidden",
  "message": "Missing required permissions: <permission_list>"
}
```

## Troubleshooting

### "Failed to fetch JWKS on startup"

**Solution**: Ensure Identity Service is running and accessible at `IDENTITY_SERVICE_URL`

### "Unknown key ID: <kid>"

**Solution**: Wait for JWKS TTL to expire (keys will be refreshed automatically)

### "JWT has expired"

**Solution**: Obtain a new JWT from Identity Service

## Files Created

1. **app/services/JWTVerificationService.py** - Core JWT verification service
2. **app/controllers/common/auth.py** - Flask authentication decorators
3. **JWT_IMPLEMENTATION.md** - Comprehensive documentation
4. **test_jwt_auth.py** - Test script for JWT authentication

## Files Modified

1. **app/__main__.py** - Initialize JWT service on startup
2. **app/controllers/v1/partner_consultations.py** - Apply JWT authentication to routes
3. **.env.example** - Add JWT configuration variables
4. **IMPLEMENTATION_SUMMARY.md** - Mark JWT authentication as implemented

## Compliance

This implementation **strictly conforms** to [docs/auth/VERIFY.md](docs/auth/VERIFY.md):

- ✅ JWKS fetching from Identity Service
- ✅ TTL-based cache refresh (default: 10 minutes)
- ✅ NO refresh on verification failure (DoS prevention)
- ✅ RS256 signature verification only
- ✅ Comprehensive claim validation (exp, iat, sub, full_name, email, permissions)
- ✅ Thread-safe operations
- ✅ Graceful degradation on JWKS fetch failure

## References

- [JWT_IMPLEMENTATION.md](JWT_IMPLEMENTATION.md) - Detailed implementation guide
- [docs/auth/VERIFY.md](docs/auth/VERIFY.md) - JWT verification specification
- [test_jwt_auth.py](test_jwt_auth.py) - Test script and examples
