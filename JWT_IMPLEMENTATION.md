# JWT Authentication Implementation

This document describes the JWT authentication implementation for the S13 Partner Consultation Service, which strictly conforms to the specification in [docs/auth/VERIFY.md](docs/auth/VERIFY.md).

## Overview

The JWT authentication system provides secure authentication and authorization for all HTTP REST API endpoints. It implements:

- **JWKS-based verification**: Fetches public keys from the Identity Service
- **RS256 signature verification**: Industry-standard RSA-based JWT signing
- **TTL-based caching**: Efficient key caching with configurable refresh intervals
- **DoS prevention**: Strict no-refresh-on-failure policy
- **Claim validation**: Comprehensive validation of all required JWT claims
- **Permission-based authorization**: Fine-grained access control

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Identity Service (S06/S10)                  │
│  ┌────────────────────────────────────────────┐         │
│  │  /.well-known/jwks.json                    │         │
│  │  - Exposes public keys (JWKS)              │         │
│  │  - Multiple keys supported                 │         │
│  └────────────────────────────────────────────┘         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Fetch JWKS (on startup & TTL expiry)
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         S13 Partner Consultation Service                 │
│  ┌────────────────────────────────────────────┐         │
│  │  JWTVerificationService                    │         │
│  │  - JWKS cache (in-memory)                  │         │
│  │  - Background refresh thread               │         │
│  │  - RS256 verification                      │         │
│  │  - Claim validation                        │         │
│  └────────────────────────────────────────────┘         │
│                     │                                     │
│                     │ verify_jwt()                        │
│                     │                                     │
│  ┌────────────────────────────────────────────┐         │
│  │  @require_jwt() Decorator                  │         │
│  │  - Extract Authorization header            │         │
│  │  - Verify JWT signature                    │         │
│  │  - Check permissions                       │         │
│  │  - Attach user info to request             │         │
│  └────────────────────────────────────────────┘         │
│                     │                                     │
│                     │ Protected Routes                    │
│                     │                                     │
│  ┌────────────────────────────────────────────┐         │
│  │  HTTP REST API Endpoints (H31)             │         │
│  │  - GET /api/v1/conversations               │         │
│  │  - GET /api/v1/conversations/{id}          │         │
│  │  - GET /api/v1/conversations/{id}/messages │         │
│  │  - POST /api/v1/conversations/{id}/messages│         │
│  └────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. JWTVerificationService

**Location**: `app/services/JWTVerificationService.py`

Core service that handles all JWT verification operations.

**Key Features**:
- JWKS fetching from Identity Service
- In-memory key caching (never written to disk)
- Background refresh thread with TTL-based scheduling
- RS256 signature verification using cryptography library
- Comprehensive claim validation
- Thread-safe operations

**Configuration** (via environment variables):
```bash
IDENTITY_SERVICE_URL=http://localhost:5010   # Identity Service base URL
JWKS_TTL_IN_MINUTES=10                       # Cache TTL (default: 10 minutes)
JWT_CLOCK_SKEW_SECONDS=60                    # Clock skew tolerance (default: 60 seconds)
```

**Key Methods**:
- `start()`: Start service and begin JWKS refresh loop
- `stop()`: Gracefully shutdown service
- `verify_jwt(token)`: Verify JWT and return validated payload
- `get_cache_stats()`: Get cache statistics for monitoring

### 2. Authentication Decorators

**Location**: `app/controllers/common/auth.py`

Flask decorators for protecting routes with JWT authentication.

#### @require_jwt(required_permissions=None)

Require JWT authentication on a route. Optionally enforce specific permissions.

**Usage**:
```python
from app.controllers.common.auth import require_jwt

@app.route('/api/v1/conversations')
@require_jwt()
def get_conversations():
    # Access authenticated user info
    user_id = request.jwt_user_id
    user_name = request.jwt_full_name
    user_email = request.jwt_email
    permissions = request.jwt_permissions
    ...

@app.route('/api/v1/admin/users')
@require_jwt(['admin.users.read'])
def admin_get_users():
    # Only users with 'admin.users.read' permission can access
    ...
```

**Request Attributes Added**:
- `request.jwt_payload`: Full JWT payload
- `request.jwt_user_id`: User ID (sub claim)
- `request.jwt_full_name`: User's full name
- `request.jwt_email`: User's email
- `request.jwt_permissions`: List of permissions

**Responses**:
- `401 Unauthorized`: Missing, invalid, or expired JWT
- `403 Forbidden`: Missing required permissions

#### @optional_jwt()

Make JWT authentication optional. If provided, user info is attached to request.

**Usage**:
```python
@app.route('/api/v1/public')
@optional_jwt()
def public_endpoint():
    if hasattr(request, 'jwt_user_id'):
        return f"Hello, {request.jwt_full_name}"
    else:
        return "Hello, guest"
```

#### Helper Functions

- `check_permission(permission)`: Check if user has a specific permission
- `has_any_permission(permissions)`: Check if user has any of the permissions
- `has_all_permissions(permissions)`: Check if user has all of the permissions

### 3. Protected Endpoints

**Location**: `app/controllers/v1/partner_consultations.py`

All HTTP REST API endpoints are protected with `@require_jwt()`.

**Protected Endpoints**:
- `GET /api/v1/conversations` - List conversations
- `GET /api/v1/conversations/{id}` - Get conversation details
- `GET /api/v1/conversations/{id}/messages` - Get conversation messages
- `POST /api/v1/conversations/{id}/messages` - Send message

**Authentication Flow**:
1. Client sends request with `Authorization: Bearer <JWT>`
2. Decorator extracts and verifies JWT
3. User info is attached to Flask request object
4. Route handler accesses user info via `request.jwt_*` attributes

## Verification Flow (Strict Conformance to VERIFY.md)

The verification follows a strict 4-step process as specified in VERIFY.md:

### Step 1: Parse JWT Header
- Extract `alg` and `kid` from JWT header
- **Reject** if `alg` ≠ `RS256`
- **Reject** if `kid` is missing

### Step 2: Resolve Public Key
- Look up public key matching `kid` in cached JWKS
- **IMPORTANT**: DO NOT refresh JWKS on missing key (DoS prevention)
- **Reject** if key not found in cache

### Step 3: Verify Signature
- Verify JWT signature using RS256 algorithm
- Use resolved public key from cache
- **Reject** if signature verification fails

### Step 4: Validate Claims
Required claims:
- `exp`: Token expiration (must not be expired)
- `iat`: Issued-at timestamp (must be within clock skew)
- `sub`: User ID (must exist and not be empty)
- `full_name`: User's full name (must exist and not be empty)
- `email`: User's email (must exist and not be empty)
- `permissions`: Array of permissions (optional, defaults to `[]`)

**Reject** if any validation fails.

## JWKS Caching and Refresh

### Cache Rules (Strict Conformance)

**JWKS cache refresh MUST occur**:
- At service startup
- Only when TTL expires (default: 10 minutes)

**JWKS cache refresh MUST NOT occur**:
- On JWT verification failure
- On unknown `kid`
- On signature mismatch

**Rationale**: This strict no-refresh-on-failure policy prevents DoS attacks where an attacker sends many invalid JWTs to trigger repeated JWKS fetches.

### Background Refresh Thread

A dedicated background thread handles JWKS refresh:

```python
# Refresh loop pseudocode
while not shutdown:
    wait(TTL_SECONDS)
    if TTL_expired:
        fetch_jwks()  # Refresh keys
        if fetch_failed:
            log_warning("Using cached keys")  # Graceful degradation
```

### Graceful Degradation

If JWKS refresh fails:
- Continue using cached keys
- Log warning
- Only reject requests if verification fails with cached keys

## Testing

### 1. Test JWT Verification

```bash
# Example: Test with a valid JWT
curl -H "Authorization: Bearer <YOUR_JWT>" \
     http://localhost:5013/api/v1/conversations

# Example: Test without JWT (should return 401)
curl http://localhost:5013/api/v1/conversations

# Example: Test with invalid JWT (should return 401)
curl -H "Authorization: Bearer invalid.jwt.token" \
     http://localhost:5013/api/v1/conversations
```

### 2. Monitor JWKS Cache

Check JWKS cache status:

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

### 3. Test Permission-Based Authorization

```python
# In your route handler
@require_jwt(['conversations.read', 'conversations.write'])
def handle_conversation():
    # Only users with BOTH permissions can access
    ...
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Identity Service URL (required)
IDENTITY_SERVICE_URL=http://localhost:5010

# JWKS cache TTL in minutes (default: 10)
JWKS_TTL_IN_MINUTES=10

# JWT clock skew in seconds (default: 60)
JWT_CLOCK_SKEW_SECONDS=60
```

### Initialization

The JWT service is automatically initialized in `app/__main__.py`:

```python
# Initialize JWT verification service
init_jwt_service()  # Starts JWKS fetching and refresh thread

# Cleanup on shutdown
atexit.register(shutdown_jwt_service)
```

## Error Handling

### HTTP 401 Unauthorized

Returned when:
- Authorization header is missing
- JWT is malformed or invalid
- JWT signature verification fails
- JWT has expired
- Required claims are missing or invalid

**Response Format**:
```json
{
  "error": "Unauthorized",
  "message": "JWT verification failed: <reason>"
}
```

### HTTP 403 Forbidden

Returned when:
- JWT is valid but user lacks required permissions

**Response Format**:
```json
{
  "error": "Forbidden",
  "message": "Missing required permissions: <permission_list>"
}
```

## Security Considerations

1. **No Key Rotation DoS**: The strict no-refresh-on-failure policy prevents attackers from triggering JWKS refreshes

2. **Clock Skew Tolerance**: 60-second clock skew tolerance prevents issues with minor time differences

3. **RS256 Only**: Only RS256 algorithm is supported (no HS256, which has known vulnerabilities)

4. **In-Memory Cache**: JWKS is cached in memory only, never written to disk

5. **Thread Safety**: All cache operations are thread-safe using locks

6. **Graceful Degradation**: Service continues with cached keys if JWKS refresh fails

## Monitoring and Observability

### Health Check Endpoint

`GET /health/jwt` - Check JWT service health and cache status

### Logging

All JWT operations are logged:
- JWKS fetch attempts (success/failure)
- JWT verification failures (with reasons)
- Cache refresh operations
- Permission check failures

**Log Levels**:
- `INFO`: Successful operations, cache refreshes
- `WARNING`: JWKS fetch failures, verification failures
- `ERROR`: Unexpected errors, service initialization failures
- `DEBUG`: Detailed verification steps (disable in production)

## Troubleshooting

### Issue: "Failed to fetch JWKS on startup"

**Cause**: Identity Service is unreachable or not responding

**Solution**:
1. Check `IDENTITY_SERVICE_URL` in `.env`
2. Verify Identity Service is running
3. Check network connectivity
4. Verify JWKS endpoint returns valid JSON

### Issue: "Unknown key ID: <kid>"

**Cause**: JWT was signed with a key not in the cached JWKS

**Solution**:
1. Wait for JWKS TTL to expire (keys will be refreshed)
2. Verify Identity Service is returning all active keys
3. Check if JWT is from a different Identity Service

### Issue: "JWT has expired"

**Cause**: Token has exceeded its expiration time

**Solution**:
1. Obtain a new JWT from Identity Service
2. Check clock synchronization between services

### Issue: "Missing required permissions"

**Cause**: User's JWT doesn't contain required permissions

**Solution**:
1. Verify user has correct role in Identity Service
2. Check permission assignments for the role
3. Obtain a new JWT with updated permissions

## Dependencies

- `pyjwt`: JWT encoding/decoding
- `cryptography`: RSA key handling and signature verification
- `requests`: HTTP client for JWKS fetching

## References

- [docs/auth/VERIFY.md](docs/auth/VERIFY.md) - JWT Verification Specification
- [docs/auth/SIGN.md](docs/auth/SIGN.md) - JWT Signing Specification (for Identity Services)
- [RFC 7519](https://tools.ietf.org/html/rfc7519) - JWT Standard
- [RFC 7517](https://tools.ietf.org/html/rfc7517) - JWKS Standard
