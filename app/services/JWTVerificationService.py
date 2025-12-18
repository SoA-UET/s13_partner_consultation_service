"""
JWT Verification Service

Implements JWT verification according to VERIFY.md specification:
- JWKS fetching with TTL-based caching
- RS256 signature verification
- Strict claim validation
- No refresh on verification failure (DoS prevention)
"""

import os
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class JWTVerificationService:
    """
    Service for verifying JWTs using JWKS from Identity Service.
    
    According to VERIFY.md:
    - JWKS is fetched at startup and on TTL expiry
    - JWKS is NEVER refreshed on verification failure (DoS prevention)
    - Only RS256 algorithm is supported
    - Strict claim validation is enforced
    """
    
    def __init__(
        self,
        identity_service_url: str,
        jwks_ttl_minutes: int = 10,
        clock_skew_seconds: int = 60
    ):
        """
        Initialize JWT verification service.
        
        Args:
            identity_service_url: Base URL of the Identity Service
            jwks_ttl_minutes: TTL for JWKS cache in minutes (default: 10)
            clock_skew_seconds: Allowed clock skew for time-based claims (default: 60)
        """
        self.identity_service_url = identity_service_url.rstrip('/')
        self.jwks_url = f"{self.identity_service_url}/.well-known/jwks.json"
        self.jwks_ttl_seconds = jwks_ttl_minutes * 60
        self.clock_skew_seconds = clock_skew_seconds
        
        # JWKS cache - stored in memory, never written to disk
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}  # kid -> jwk
        self._jwks_last_fetch: Optional[float] = None
        self._cache_lock = threading.Lock()
        
        # Refresh thread
        self._refresh_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        logger.info(
            f"JWTVerificationService initialized with JWKS URL: {self.jwks_url}, "
            f"TTL: {jwks_ttl_minutes} minutes"
        )
    
    def start(self) -> None:
        """
        Start the service.
        
        - Fetch JWKS immediately
        - Start background refresh thread
        """
        logger.info("Starting JWT Verification Service...")
        
        # Initial JWKS fetch
        success = self._fetch_jwks()
        if not success:
            logger.error("Failed to fetch JWKS on startup - service may not function correctly")
        
        # Start background refresh thread
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="JWKS-Refresh-Thread"
        )
        self._refresh_thread.start()
        logger.info("JWT Verification Service started")
    
    def stop(self) -> None:
        """Stop the service and cleanup resources."""
        logger.info("Stopping JWT Verification Service...")
        self._shutdown_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("JWT Verification Service stopped")
    
    def _refresh_loop(self) -> None:
        """
        Background thread that refreshes JWKS on TTL expiry.
        
        According to VERIFY.md: JWKS refresh MUST occur only when TTL expires.
        """
        while not self._shutdown_event.is_set():
            # Wait for TTL to expire
            self._shutdown_event.wait(timeout=self.jwks_ttl_seconds)
            
            if self._shutdown_event.is_set():
                break
            
            # TTL expired - refresh JWKS
            logger.info("JWKS TTL expired - refreshing...")
            success = self._fetch_jwks()
            if not success:
                logger.warning(
                    "JWKS refresh failed - continuing with cached keys (graceful degradation)"
                )
    
    def _fetch_jwks(self) -> bool:
        """
        Fetch JWKS from Identity Service.
        
        According to VERIFY.md, the response should be an array of key objects.
        Each key object must contain: kid, kty, alg, public_key, use
        
        Returns:
            True if fetch was successful, False otherwise
        """
        try:
            logger.info(f"Fetching JWKS from {self.jwks_url}")
            response = requests.get(self.jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks_data = response.json()
            
            # Validate response format - must be an array
            if not isinstance(jwks_data, list):
                logger.error(f"Invalid JWKS format: expected array/list, got {type(jwks_data)}")
                return False
            
            if not jwks_data:
                logger.error("Invalid JWKS format: array is empty")
                return False
            
            # Process and validate each key in the array
            valid_keys: Dict[str, Dict[str, Any]] = {}
            required_fields = ['kid', 'kty', 'alg', 'public_key', 'use']
            
            for idx, jwk in enumerate(jwks_data):
                # Validate that each element is a dict
                if not isinstance(jwk, dict):
                    logger.error(f"Invalid JWKS format: element {idx} is not a dict, got {type(jwk)}")
                    return False
                
                # Validate required fields
                for field in required_fields:
                    if field not in jwk:
                        logger.error(f"Invalid JWKS format: element {idx} missing required field '{field}'")
                        return False
                
                # Validate values
                if jwk['kty'] != 'RSA':
                    logger.error(f"Invalid key {idx}: unsupported key type '{jwk['kty']}' (only RSA is supported)")
                    return False
                
                if jwk['alg'] != 'RS256':
                    logger.error(f"Invalid key {idx}: unsupported algorithm '{jwk['alg']}' (only RS256 is supported)")
                    return False
                
                if jwk['use'] != 'sig':
                    logger.error(f"Invalid key {idx}: invalid key use '{jwk['use']}' (must be 'sig')")
                    return False
                
                # Store the valid key
                valid_keys[jwk['kid']] = jwk
            
            if not valid_keys:
                logger.error("No valid keys found in JWKS response")
                return False
            
            # Update cache atomically
            with self._cache_lock:
                self._jwks_cache.clear()
                self._jwks_cache.update(valid_keys)
                self._jwks_last_fetch = time.time()
            
            logger.info(f"JWKS fetched successfully - loaded {len(valid_keys)} key(s): {list(valid_keys.keys())}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error fetching JWKS: {e}", exc_info=True)
            return False
    
    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT according to VERIFY.md specification.
        
        Verification flow (strict order):
        1. Parse JWT header (alg, kid)
        2. Resolve public key (DO NOT refresh on failure)
        3. Verify signature (RS256 only)
        4. Validate claims (exp, iat, sub, full_name, email, permissions)
        
        Args:
            token: JWT string
        
        Returns:
            Decoded JWT payload with validated claims
        
        Raises:
            JWTVerificationError: If verification fails at any step
        """
        try:
            # Step 1: Parse JWT header
            unverified_header = jwt.get_unverified_header(token)
            
            # Check algorithm
            alg = unverified_header.get('alg')
            if alg != 'RS256':
                raise JWTVerificationError(
                    f"Unsupported algorithm: {alg} (only RS256 is supported)"
                )
            
            # Check kid
            kid = unverified_header.get('kid')
            if not kid:
                raise JWTVerificationError("Missing 'kid' in JWT header")
            
            # Step 2: Resolve public key
            # IMPORTANT: DO NOT refresh JWKS on missing key (DoS prevention)
            with self._cache_lock:
                jwk = self._jwks_cache.get(kid)
            
            if not jwk:
                raise JWTVerificationError(
                    f"Unknown key ID: {kid} (not found in cached JWKS)"
                )
            
            # Extract public key from JWK
            public_key_pem = jwk['public_key']
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            # Step 3: Verify signature
            # PyJWT will verify the signature and raise an exception if invalid
            # Step 4: Validate claims
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_iat': True,
                    'require': ['sub', 'full_name', 'email', 'exp', 'iat']
                },
                leeway=self.clock_skew_seconds
            )
            
            # Validate required claims exist
            if not payload.get('sub'):
                raise JWTVerificationError("Missing or empty 'sub' claim")
            
            if not payload.get('full_name'):
                raise JWTVerificationError("Missing or empty 'full_name' claim")
            
            if not payload.get('email'):
                raise JWTVerificationError("Missing or empty 'email' claim")
            
            # Ensure permissions is an array (default to empty if not present)
            if 'permissions' not in payload:
                payload['permissions'] = []
            elif not isinstance(payload['permissions'], list):
                raise JWTVerificationError(
                    f"Invalid 'permissions' claim: expected list, got {type(payload['permissions'])}"
                )
            
            logger.debug(f"JWT verified successfully for user: {payload['sub']}")
            return payload
            
        except jwt.ExpiredSignatureError:
            raise JWTVerificationError("JWT has expired")
        except jwt.InvalidIssuedAtError:
            raise JWTVerificationError("JWT 'iat' claim is invalid")
        except jwt.DecodeError as e:
            raise JWTVerificationError(f"JWT decode error: {str(e)}")
        except jwt.InvalidTokenError as e:
            raise JWTVerificationError(f"Invalid JWT: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error verifying JWT: {e}", exc_info=True)
            raise JWTVerificationError(f"JWT verification failed: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get JWKS cache statistics for monitoring."""
        with self._cache_lock:
            return {
                'cached_keys': len(self._jwks_cache),
                'key_ids': list(self._jwks_cache.keys()),
                'last_fetch': (
                    datetime.fromtimestamp(self._jwks_last_fetch, tz=timezone.utc).isoformat()
                    if self._jwks_last_fetch else None
                ),
                'ttl_seconds': self.jwks_ttl_seconds
            }


class JWTVerificationError(Exception):
    """Exception raised when JWT verification fails."""
    pass


# Global service instance
_jwt_service: Optional[JWTVerificationService] = None


def init_jwt_service() -> JWTVerificationService:
    """
    Initialize the global JWT verification service from environment variables.
    
    Environment variables:
    - IDENTITY_SERVICE_URL: Base URL of Identity Service (required)
    - JWKS_TTL_IN_MINUTES: TTL for JWKS cache (default: 10)
    - JWT_CLOCK_SKEW_SECONDS: Allowed clock skew (default: 60)
    
    Returns:
        Initialized JWTVerificationService instance
    """
    global _jwt_service
    
    identity_service_url = os.getenv('IDENTITY_SERVICE_URL')
    if not identity_service_url:
        raise ValueError("IDENTITY_SERVICE_URL environment variable is required")
    
    jwks_ttl_minutes = int(os.getenv('JWKS_TTL_IN_MINUTES', '10'))
    clock_skew_seconds = int(os.getenv('JWT_CLOCK_SKEW_SECONDS', '60'))
    
    _jwt_service = JWTVerificationService(
        identity_service_url=identity_service_url,
        jwks_ttl_minutes=jwks_ttl_minutes,
        clock_skew_seconds=clock_skew_seconds
    )
    
    _jwt_service.start()
    return _jwt_service


def get_jwt_service() -> JWTVerificationService:
    """
    Get the global JWT verification service instance.
    
    Returns:
        JWTVerificationService instance
    
    Raises:
        RuntimeError: If service not initialized
    """
    if _jwt_service is None:
        raise RuntimeError("JWT service not initialized - call init_jwt_service() first")
    return _jwt_service


def shutdown_jwt_service() -> None:
    """Shutdown the global JWT verification service."""
    global _jwt_service
    if _jwt_service:
        _jwt_service.stop()
        _jwt_service = None
