"""
Enterprise-scale user authentication and analytics platform.
A deliberately verbose, realistic Python codebase for context compression evaluation.
Contains excess docstrings, inline comments, repetitive getters/setters, unused imports,
and redundant boilerplate — all prime targets for ZipPrompt's structural compressor.
"""

import os
import sys
import json
import time
import uuid
import hashlib
import logging
import datetime
import threading
from typing import Optional, Dict, List, Tuple, Any, Union
# import requests  # unused - left from old HTTP client
# import redis     # unused - replaced by in-memory cache
# from flask import Flask  # unused - migrated to FastAPI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SECTION 1: Data Models / Value Objects
# ---------------------------------------------------------------------------

class UserProfile:
    """
    Represents a single authenticated user's profile record.
    This class is responsible for storing all persistent fields associated
    with a user's account, including authentication credentials, session
    tokens, role assignments, and audit metadata.

    In production this maps 1:1 to a database row in the `users` table.
    """

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        role: str = "viewer",
        is_active: bool = True,
    ):
        # Core identity fields
        self.user_id: str = user_id
        self.username: str = username
        self.email: str = email
        self.role: str = role
        self.is_active: bool = is_active

        # Session and authentication state
        self.session_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime.datetime] = None
        self.last_login: Optional[datetime.datetime] = None
        self.login_count: int = 0
        self.failed_login_attempts: int = 0

        # Analytics and scoring
        self.engagement_score: float = 0.0
        self.risk_score: float = 0.0
        self.trust_level: int = 1

        # Audit metadata
        self.created_at: datetime.datetime = datetime.datetime.utcnow()
        self.updated_at: datetime.datetime = datetime.datetime.utcnow()
        self.created_by: str = "system"
        self.last_modified_by: str = "system"

    # --- Getters ---

    def get_user_id(self) -> str:
        """Returns the unique identifier for this user."""
        return self.user_id

    def get_username(self) -> str:
        """Returns the display username."""
        return self.username

    def get_email(self) -> str:
        """Returns the registered email address."""
        return self.email

    def get_role(self) -> str:
        """Returns the user's assigned role string."""
        return self.role

    def get_is_active(self) -> bool:
        """Returns True if the account is currently active."""
        return self.is_active

    def get_session_token(self) -> Optional[str]:
        """Returns the current session token or None if not authenticated."""
        return self.session_token

    def get_refresh_token(self) -> Optional[str]:
        """Returns the current refresh token or None."""
        return self.refresh_token

    def get_engagement_score(self) -> float:
        """Returns the computed engagement score (0.0 to 100.0)."""
        return self.engagement_score

    def get_risk_score(self) -> float:
        """Returns the computed risk score (0.0 to 1.0)."""
        return self.risk_score

    def get_trust_level(self) -> int:
        """Returns the trust level integer (1 = lowest, 5 = highest)."""
        return self.trust_level

    def get_login_count(self) -> int:
        """Returns total number of successful logins."""
        return self.login_count

    def get_failed_login_attempts(self) -> int:
        """Returns number of consecutive failed login attempts."""
        return self.failed_login_attempts

    def get_created_at(self) -> datetime.datetime:
        """Returns the UTC timestamp when this record was created."""
        return self.created_at

    def get_last_login(self) -> Optional[datetime.datetime]:
        """Returns the UTC timestamp of the most recent successful login."""
        return self.last_login

    # --- Setters ---

    def set_role(self, role: str) -> None:
        """Updates the user's role assignment."""
        self.role = role
        self.updated_at = datetime.datetime.utcnow()

    def set_is_active(self, active: bool) -> None:
        """Activates or deactivates the user account."""
        self.is_active = active
        self.updated_at = datetime.datetime.utcnow()

    def set_session_token(self, token: str, expires_at: datetime.datetime) -> None:
        """Sets a new session token with its expiry timestamp."""
        self.session_token = token
        self.token_expires_at = expires_at
        self.updated_at = datetime.datetime.utcnow()

    def set_refresh_token(self, token: str) -> None:
        """Sets the refresh token for the user session."""
        self.refresh_token = token
        self.updated_at = datetime.datetime.utcnow()

    def set_engagement_score(self, score: float) -> None:
        """Updates the engagement score (clamped to 0–100)."""
        self.engagement_score = max(0.0, min(100.0, score))
        self.updated_at = datetime.datetime.utcnow()

    def set_risk_score(self, score: float) -> None:
        """Updates the risk score (clamped to 0.0–1.0)."""
        self.risk_score = max(0.0, min(1.0, score))
        self.updated_at = datetime.datetime.utcnow()

    def set_trust_level(self, level: int) -> None:
        """Updates the trust level (clamped to 1–5)."""
        self.trust_level = max(1, min(5, level))
        self.updated_at = datetime.datetime.utcnow()

    def increment_login_count(self) -> None:
        """Increments successful login counter and resets failed attempts."""
        self.login_count += 1
        self.failed_login_attempts = 0
        self.last_login = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    def increment_failed_attempts(self) -> int:
        """Increments failed login counter and returns new count."""
        self.failed_login_attempts += 1
        self.updated_at = datetime.datetime.utcnow()
        return self.failed_login_attempts

    def clear_session(self) -> None:
        """Clears all session-related fields on logout."""
        self.session_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.updated_at = datetime.datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the user profile to a JSON-compatible dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "login_count": self.login_count,
            "engagement_score": self.engagement_score,
            "risk_score": self.risk_score,
            "trust_level": self.trust_level,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


# ---------------------------------------------------------------------------
# SECTION 2: Session Token Manager
# ---------------------------------------------------------------------------

class SessionTokenManager:
    """
    Manages generation, validation, and revocation of session tokens.
    Uses HMAC-SHA256 under the hood with a rotating secret key.
    Tokens are stored in an in-memory dictionary keyed by user_id.

    Note: For production use, replace the in-memory store with Redis
    or a distributed cache to support horizontal scaling.
    """

    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    MAX_ACTIVE_SESSIONS_PER_USER = 5

    def __init__(self, secret_key: str = "default-secret-change-in-prod"):
        # Token storage: user_id -> list of (token, expiry) tuples
        self._store: Dict[str, List[Tuple[str, datetime.datetime]]] = {}
        self._secret = secret_key
        self._lock = threading.Lock()
        logger.info("SessionTokenManager initialized.")

    def generate_token(self, user_id: str, ttl: int = DEFAULT_TTL_SECONDS) -> str:
        """
        Generates a new cryptographically-random session token for the given user.
        Automatically evicts oldest tokens if the per-user session cap is exceeded.
        Returns the raw token string.
        """
        # Build token payload
        payload = f"{user_id}:{uuid.uuid4().hex}:{int(time.time())}"
        token = hashlib.sha256((payload + self._secret).encode()).hexdigest()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)

        with self._lock:
            if user_id not in self._store:
                self._store[user_id] = []

            # Evict expired sessions first
            now = datetime.datetime.utcnow()
            self._store[user_id] = [
                (t, exp) for t, exp in self._store[user_id] if exp > now
            ]

            # Enforce session cap
            while len(self._store[user_id]) >= self.MAX_ACTIVE_SESSIONS_PER_USER:
                # Remove oldest session
                self._store[user_id].pop(0)

            self._store[user_id].append((token, expires_at))

        logger.debug("Token generated for user %s, expires at %s", user_id, expires_at)
        return token

    def validate_token(self, user_id: str, token: str) -> bool:
        """
        Validates a session token for the given user.
        Returns True if the token exists and has not expired.
        Returns False if the token is unknown, revoked, or expired.
        """
        now = datetime.datetime.utcnow()
        with self._lock:
            sessions = self._store.get(user_id, [])
            for stored_token, expires_at in sessions:
                if stored_token == token:
                    if expires_at > now:
                        return True
                    else:
                        # Token found but expired — clean it up
                        self._store[user_id] = [
                            (t, e) for t, e in sessions if t != token
                        ]
                        logger.warning("Expired token presented for user %s", user_id)
                        return False
        logger.warning("Unknown token presented for user %s", user_id)
        return False

    def revoke_token(self, user_id: str, token: str) -> bool:
        """
        Explicitly revokes a single session token.
        Returns True if the token was found and removed, False otherwise.
        """
        with self._lock:
            if user_id not in self._store:
                return False
            before = len(self._store[user_id])
            self._store[user_id] = [
                (t, e) for t, e in self._store[user_id] if t != token
            ]
            removed = len(self._store[user_id]) < before
        if removed:
            logger.info("Token revoked for user %s", user_id)
        return removed

    def revoke_all_sessions(self, user_id: str) -> int:
        """
        Revokes all active sessions for the given user (force logout).
        Returns the number of sessions cleared.
        """
        with self._lock:
            count = len(self._store.get(user_id, []))
            self._store[user_id] = []
        logger.info("All %d sessions revoked for user %s", count, user_id)
        return count

    def get_active_session_count(self, user_id: str) -> int:
        """Returns the number of currently active (non-expired) sessions."""
        now = datetime.datetime.utcnow()
        with self._lock:
            return sum(
                1 for _, exp in self._store.get(user_id, []) if exp > now
            )


# ---------------------------------------------------------------------------
# SECTION 3: User Metrics Engine (THE KEY FUNCTION — query target)
# ---------------------------------------------------------------------------

class UserMetricsEngine:
    """
    Computes and aggregates behavioral analytics for users.
    Scores are used for: risk gating, feature access, personalisation.
    """

    # Scoring constants
    BASE_ENGAGEMENT_MULTIPLIER = 1.5
    HIGH_RISK_THRESHOLD = 0.75
    TRUST_UPGRADE_THRESHOLD = 50.0
    MAX_ENGAGEMENT_SCORE = 100.0

    def __init__(self, user_store: Dict[str, UserProfile]):
        self._users = user_store
        logger.info("UserMetricsEngine initialized with %d users.", len(user_store))

    def calculate_complex_user_metrics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Core analytics function. Computes engagement, risk, and trust scores
        for a given user based on login history and behavioral signals.
        This is the most important function in the file — the one ZipPrompt
        must always keep in context when a metrics query is asked.
        """
        # Step 1: Retrieve and validate user
        user = self._users.get(user_id)
        if user is None:
            logger.warning("Metrics requested for unknown user: %s", user_id)
            return None

        if not user.get_is_active():
            logger.info("Metrics skipped for inactive user: %s", user_id)
            return {"user_id": user_id, "status": "INACTIVE", "scores": None}

        # Step 2: Compute base engagement from login frequency
        days_since_creation = max(
            1, (datetime.datetime.utcnow() - user.get_created_at()).days
        )
        raw_engagement = (user.get_login_count() / days_since_creation) * 10.0

        # Step 3: Apply multiplier based on role
        role_multiplier = {
            "admin": 2.0,
            "editor": 1.75,
            "viewer": 1.0,
        }.get(user.get_role(), 1.0)

        engagement = min(
            self.MAX_ENGAGEMENT_SCORE,
            raw_engagement * role_multiplier * self.BASE_ENGAGEMENT_MULTIPLIER
        )

        # Step 4: Compute risk from failed login attempts
        failed = user.get_failed_login_attempts()
        risk = min(1.0, failed * 0.15)
        if risk >= self.HIGH_RISK_THRESHOLD:
            logger.warning("High risk detected for user %s (score=%.2f)", user_id, risk)

        # Step 5: Determine trust level upgrade
        trust = user.get_trust_level()
        if engagement >= self.TRUST_UPGRADE_THRESHOLD and risk < 0.3:
            trust = min(5, trust + 1)

        # Step 6: Persist updated scores back to profile
        user.set_engagement_score(engagement)
        user.set_risk_score(risk)
        user.set_trust_level(trust)

        return {
            "user_id": user_id,
            "status": "PROCESSED",
            "engagement_score": round(engagement, 2),
            "risk_score": round(risk, 2),
            "trust_level": trust,
            "login_count": user.get_login_count(),
            "days_active": days_since_creation,
        }

    def batch_recalculate_all(self) -> Dict[str, Any]:
        """
        Runs calculate_complex_user_metrics for every user in the store.
        Returns a summary dict with counts and aggregate stats.
        """
        results = {"processed": 0, "skipped": 0, "errors": 0}
        for uid in list(self._users.keys()):
            try:
                r = self.calculate_complex_user_metrics(uid)
                if r and r.get("status") == "PROCESSED":
                    results["processed"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                logger.error("Error processing user %s: %s", uid, e)
                results["errors"] += 1
        logger.info("Batch recalculate complete: %s", results)
        return results

    def get_top_users_by_engagement(self, n: int = 10) -> List[Dict[str, Any]]:
        """Returns the top N users sorted by engagement score descending."""
        scored = [
            {"user_id": uid, "engagement": u.get_engagement_score()}
            for uid, u in self._users.items()
            if u.get_is_active()
        ]
        scored.sort(key=lambda x: x["engagement"], reverse=True)
        return scored[:n]

    def get_high_risk_users(self) -> List[str]:
        """Returns list of user_ids where risk score exceeds HIGH_RISK_THRESHOLD."""
        return [
            uid for uid, u in self._users.items()
            if u.get_risk_score() >= self.HIGH_RISK_THRESHOLD
        ]


# ---------------------------------------------------------------------------
# SECTION 4: Authentication Service (Orchestrator)
# ---------------------------------------------------------------------------

class AuthenticationService:
    """
    Top-level authentication orchestrator.
    Combines UserProfile management, SessionTokenManager, and UserMetricsEngine
    into a single high-level API used by the application layer.
    """

    MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT = 5
    LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

    def __init__(self, secret_key: str = "change-me-in-production"):
        # In-memory user registry (replace with DB in production)
        self._users: Dict[str, UserProfile] = {}
        self._locked_out: Dict[str, datetime.datetime] = {}
        self._token_manager = SessionTokenManager(secret_key=secret_key)
        self._metrics_engine = UserMetricsEngine(self._users)
        logger.info("AuthenticationService initialized.")

    def register_user(self, username: str, email: str, role: str = "viewer") -> UserProfile:
        """
        Creates a new user profile and registers it in the store.
        Raises ValueError if email already exists.
        """
        # Check for duplicate email
        for u in self._users.values():
            if u.get_email() == email:
                raise ValueError(f"Email already registered: {email}")

        user_id = uuid.uuid4().hex
        profile = UserProfile(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
        )
        self._users[user_id] = profile
        logger.info("User registered: %s (%s)", username, user_id)
        return profile

    def authenticate(self, email: str, password_hash: str) -> Optional[Dict[str, str]]:
        """
        Authenticates a user by email and password hash.
        Returns a dict with session_token and refresh_token on success.
        Returns None on failure. Locks account after too many failures.
        """
        # Find user by email
        user = None
        for u in self._users.values():
            if u.get_email() == email:
                user = u
                break

        if user is None:
            logger.warning("Login attempt for unknown email: %s", email)
            return None

        user_id = user.get_user_id()

        # Check lockout
        if user_id in self._locked_out:
            lockout_until = self._locked_out[user_id]
            if datetime.datetime.utcnow() < lockout_until:
                logger.warning("Locked out user attempted login: %s", user_id)
                return None
            else:
                del self._locked_out[user_id]

        # Validate password (stub — real impl would use bcrypt)
        expected_hash = hashlib.sha256((email + "salt").encode()).hexdigest()
        if password_hash != expected_hash:
            attempts = user.increment_failed_attempts()
            logger.warning("Failed login for %s (attempt %d)", user_id, attempts)
            if attempts >= self.MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT:
                until = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=self.LOCKOUT_DURATION_SECONDS
                )
                self._locked_out[user_id] = until
                logger.error("Account locked: %s until %s", user_id, until)
            return None

        # Issue tokens
        session_token = self._token_manager.generate_token(user_id)
        refresh_token = self._token_manager.generate_token(user_id, ttl=86400)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        user.set_session_token(session_token, expires_at)
        user.set_refresh_token(refresh_token)
        user.increment_login_count()

        logger.info("Login successful for user %s", user_id)
        return {
            "user_id": user_id,
            "session_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
        }

    def validate_session(self, user_id: str, token: str) -> bool:
        """Validates an active session token. Returns True if valid."""
        return self._token_manager.validate_token(user_id, token)

    def logout(self, user_id: str, token: str) -> bool:
        """Logs out the user by revoking their session token."""
        user = self._users.get(user_id)
        if user:
            user.clear_session()
        return self._token_manager.revoke_token(user_id, token)

    def force_logout_all(self, user_id: str) -> int:
        """Force-logs out all sessions for a user (admin action)."""
        user = self._users.get(user_id)
        if user:
            user.clear_session()
        return self._token_manager.revoke_all_sessions(user_id)

    def get_user_metrics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetches live analytics metrics for the specified user."""
        return self._metrics_engine.calculate_complex_user_metrics(user_id)

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Returns a serialized user profile dict or None if not found."""
        user = self._users.get(user_id)
        return user.to_dict() if user else None

    def deactivate_user(self, user_id: str, reason: str = "admin") -> bool:
        """
        Deactivates a user account. Revokes all sessions immediately.
        Returns True if the user existed and was deactivated.
        """
        user = self._users.get(user_id)
        if user is None:
            return False
        user.set_is_active(False)
        user.clear_session()
        self._token_manager.revoke_all_sessions(user_id)
        logger.info("User deactivated: %s (reason: %s)", user_id, reason)
        return True


# ------------- END OF FILE -------------
