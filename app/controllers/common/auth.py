"""
Authentication decorators for Flask routes.

Implements JWT verification middleware according to VERIFY.md specification.
"""

import logging
from functools import wraps
from typing import Callable, List, Optional
from flask import request, jsonify

from app.services.JWTVerificationService import (
    get_jwt_service,
    JWTVerificationError
)

logger = logging.getLogger(__name__)


def require_jwt(required_permissions: Optional[List[str]] = None):
    """
    Decorator to require JWT authentication on Flask routes.
    
    Verifies JWT from Authorization header and validates permissions if specified.
    
    Args:
        required_permissions: Optional list of required permissions.
                            If specified, the JWT must contain ALL of these permissions.
    
    Usage:
        @app.route('/api/v1/conversations')
        @require_jwt()
        def get_conversations():
            # Access user info from request
            user_id = request.jwt_user_id
            permissions = request.jwt_permissions
            ...
        
        @app.route('/api/v1/admin/users')
        @require_jwt(['admin.users.read'])
        def admin_get_users():
            ...
    
    Returns:
        - HTTP 401 if JWT is missing, invalid, or expired
        - HTTP 403 if required permissions are not present
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Step 1: Extract JWT from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.warning("Missing Authorization header")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Missing Authorization header'
                }), 401
            
            # Check Bearer scheme
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                logger.warning(f"Invalid Authorization header format: {auth_header}")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Invalid Authorization header format. Expected: Bearer <token>'
                }), 401
            
            token = parts[1]
            
            # Step 2: Verify JWT
            try:
                jwt_service = get_jwt_service()
                payload = jwt_service.verify_jwt(token)
            except JWTVerificationError as e:
                logger.warning(f"JWT verification failed: {e}")
                return jsonify({
                    'error': 'Unauthorized',
                    'message': f'JWT verification failed: {str(e)}'
                }), 401
            except Exception as e:
                logger.error(f"Unexpected error during JWT verification: {e}", exc_info=True)
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'JWT verification failed'
                }), 401
            
            # Step 3: Check required permissions
            user_permissions = payload.get('permissions', [])
            
            if required_permissions:
                missing_permissions = [
                    perm for perm in required_permissions
                    if perm not in user_permissions
                ]
                
                if missing_permissions:
                    logger.warning(
                        f"User {payload['sub']} missing required permissions: {missing_permissions}"
                    )
                    return jsonify({
                        'error': 'Forbidden',
                        'message': f'Missing required permissions: {", ".join(missing_permissions)}'
                    }), 403
            
            # Step 4: Attach user info to request
            # Make JWT payload available to route handlers
            request.jwt_payload = payload
            request.jwt_user_id = payload['sub']
            request.jwt_full_name = payload['full_name']
            request.jwt_email = payload['email']
            request.jwt_permissions = user_permissions
            
            logger.debug(
                f"Request authenticated - User: {payload['sub']}, "
                f"Permissions: {len(user_permissions)}"
            )
            
            # Call the original route handler
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def optional_jwt():
    """
    Decorator that makes JWT authentication optional.
    
    If a valid JWT is provided, user info is attached to the request.
    If no JWT or invalid JWT, the request continues without authentication.
    
    Usage:
        @app.route('/api/v1/public')
        @optional_jwt()
        def public_endpoint():
            if hasattr(request, 'jwt_user_id'):
                # Authenticated user
                return f"Hello, {request.jwt_full_name}"
            else:
                # Anonymous user
                return "Hello, guest"
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Try to extract and verify JWT
            auth_header = request.headers.get('Authorization')
            
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                    
                    try:
                        jwt_service = get_jwt_service()
                        payload = jwt_service.verify_jwt(token)
                        
                        # Attach user info to request
                        request.jwt_payload = payload
                        request.jwt_user_id = payload['sub']
                        request.jwt_full_name = payload['full_name']
                        request.jwt_email = payload['email']
                        request.jwt_permissions = payload.get('permissions', [])
                        
                        logger.debug(f"Optional JWT verified - User: {payload['sub']}")
                    except Exception as e:
                        # JWT verification failed - continue without auth
                        logger.debug(f"Optional JWT verification failed: {e}")
            
            # Call the original route handler (with or without JWT)
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def check_permission(permission: str) -> bool:
    """
    Check if the current authenticated user has a specific permission.
    
    Args:
        permission: Permission string to check
    
    Returns:
        True if user has the permission, False otherwise
    
    Usage:
        @app.route('/api/v1/resource')
        @require_jwt()
        def handle_resource():
            if check_permission('resource.write'):
                # User can write
                ...
            elif check_permission('resource.read'):
                # User can only read
                ...
    """
    if not hasattr(request, 'jwt_permissions'):
        return False
    
    return permission in request.jwt_permissions


def has_any_permission(permissions: List[str]) -> bool:
    """
    Check if the current authenticated user has any of the specified permissions.
    
    Args:
        permissions: List of permission strings
    
    Returns:
        True if user has at least one of the permissions, False otherwise
    """
    if not hasattr(request, 'jwt_permissions'):
        return False
    
    user_permissions = request.jwt_permissions
    return any(perm in user_permissions for perm in permissions)


def has_all_permissions(permissions: List[str]) -> bool:
    """
    Check if the current authenticated user has all of the specified permissions.
    
    Args:
        permissions: List of permission strings
    
    Returns:
        True if user has all of the permissions, False otherwise
    """
    if not hasattr(request, 'jwt_permissions'):
        return False
    
    user_permissions = request.jwt_permissions
    return all(perm in user_permissions for perm in permissions)
