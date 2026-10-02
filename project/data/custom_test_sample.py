"""
Enterprise Authentication & Token Management Service
Used for testing ZipPrompt context compression on custom input.
"""

import hmac
import hashlib
import time
import uuid

class UserSecurityContext:
    def __init__(self, user_id: str, email: str, role: str = "member"):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.is_two_factor_enabled = False
        self.failed_attempts = 0
        self.lockout_until = 0

    def record_failed_attempt(self):
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            self.lockout_until = time.time() + 900  # 15 minutes lockout

    def is_locked_out(self) -> bool:
        return time.time() < self.lockout_until

class OAuth2TokenEngine:
    def __init__(self, secret_key: str = "SUPER_SECRET_HMAC_KEY"):
        self.secret_key = secret_key
        self.active_refresh_tokens = {}

    def generate_jwt_access_token(self, user_id: str, scope: str = "read") -> str:
        """Generates a signed HMAC-SHA256 access token expiring in 15 minutes."""
        header = "alg=HS256"
        payload = f"sub={user_id}&scope={scope}&exp={int(time.time()) + 900}"
        signature = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"access_{payload}.{signature}"

    def generate_refresh_token(self, user_id: str) -> str:
        """Generates a long-lived UUID refresh token expiring in 7 days."""
        token_id = str(uuid.uuid4())
        self.active_refresh_tokens[token_id] = {
            "user_id": user_id,
            "expires_at": time.time() + 604800
        }
        return token_id

    def validate_access_token(self, token: str) -> bool:
        """Validates signed token format and expiration."""
        if not token.startswith("access_"):
            return False
        parts = token[7:].split(".")
        if len(parts) != 2:
            return False
        payload, signature = parts[0], parts[1]
        expected_sig = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected_sig)

class TwoFactorAuthenticator:
    def __init__(self):
        self.totp_secrets = {}

    def enable_totp(self, user_id: str) -> str:
        secret = hashlib.sha256(f"{user_id}_{time.time()}".encode()).hexdigest()[:16]
        self.totp_secrets[user_id] = secret
        return secret

    def verify_totp_code(self, user_id: str, code: str) -> bool:
        if user_id not in self.totp_secrets:
            return False
        # Simplified TOTP verification mock
        expected = str(int(hashlib.md5(self.totp_secrets[user_id].encode()).hexdigest(), 16) % 1000000).zfill(6)
        return code == expected
