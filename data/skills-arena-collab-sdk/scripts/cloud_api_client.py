#!/usr/bin/env python3
"""
Skills Arena Cloud API Client - Production Implementation

Real HTTP/gRPC client for Skills Arena Cloud integration
with authentication, token management, and CLI interface.

Features:
1. HTTP API client with retry and circuit breaker
2. gRPC client for high-performance communication
3. JWT-based authentication and token refresh
4. Rate limiting and caching
5. CLI interface for OpenClaw agent simulation

Author: Skills Arena Team
Version: 3.0.0
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse
import aiohttp
import grpc
import numpy as np
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Constants ============

CLOUD_API_URL = "https://api.skills-arena.example.com"
GRPC_SERVER = "grpc.skills-arena.example.com:50051"
TOKEN_FILE = Path("~/.config/skills-arena/tokens.json")
CACHE_DIR = Path("./data/api_cache")
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RATE_LIMIT = 100  # requests per minute


# ============ Enums ============


class AuthProvider(Enum):
    """Authentication provider types."""

    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"


class APIEndpoint(Enum):
    """Skills Arena Cloud API endpoints."""

    # Authentication
    AUTH_TOKEN = "/api/v1/auth/token"
    AUTH_REFRESH = "/api/v1/auth/refresh"
    AUTH_REVOKE = "/api/v1/auth/revoke"

    # Skills
    SKILLS_LIST = "/api/v1/skills"
    SKILLS_DETAIL = "/api/v1/skills/{skill_id}"
    SKILLS_RECOMMEND = "/api/v1/skills/recommend"
    SKILLS_SEARCH = "/api/v1/skills/search"
    SKILLS_RATE = "/api/v1/skills/{skill_id}/rate"

    # Federated Learning
    FL_JOIN = "/api/v1/fl/join"
    FL_ROUNDS = "/api/v1/fl/rounds"
    FL_UPLOAD = "/api/v1/fl/upload"
    FL_AGGREGATE = "/api/v1/fl/aggregate"

    # Cross-Device Transfer
    TRANSFER_INIT = "/api/v1/transfer/init"
    TRANSFER_STATUS = "/api/v1/transfer/status"
    TRANSFER_COMPLETE = "/api/v1/transfer/complete"

    # Analytics
    ANALYTICS_USAGE = "/api/v1/analytics/usage"
    ANALYTICS_RECOMMENDATIONS = "/api/v1/analytics/recommendations"


# ============ Data Classes ============


@dataclass
class APIToken:
    """API authentication token."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime
    scope: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now() >= self.expires_at - timedelta(minutes=5)

    @property
    def time_until_expiry(self) -> float:
        """Get time until expiry in seconds."""
        return (self.expires_at - datetime.now()).total_seconds()


@dataclass
class APIKey:
    """API key credentials."""

    key_id: str
    secret: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CloudConfig:
    """Cloud API configuration."""

    api_url: str = CLOUD_API_URL
    grpc_server: str = GRPC_SERVER
    auth_provider: AuthProvider = AuthProvider.JWT
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    enable_cache: bool = True
    cache_ttl: int = 300  # seconds
    rate_limit: int = RATE_LIMIT


@dataclass
class RateLimitInfo:
    """Rate limit information from API response."""

    limit: int
    remaining: int
    reset_at: datetime
    limit_type: str = "global"

    @property
    def seconds_until_reset(self) -> float:
        return (self.reset_at - datetime.now()).total_seconds()


@dataclass
class APIResponse:
    """Generic API response wrapper."""

    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    status_code: int = 200
    rate_limit: Optional[RateLimitInfo] = None
    request_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SkillMetadata:
    """Skill metadata from cloud."""

    skill_id: str
    name: str
    description: str
    category: str
    tags: List[str]
    version: str
    author: str
    created_at: str
    updated_at: str
    rating: float = 0.0
    rating_count: int = 0
    usage_count: int = 0
    is_premium: bool = False
    requires_consent: bool = False


@dataclass
class FederatedRound:
    """Federated learning round info."""

    round_id: str
    status: str
    n_participants: int
    n_required: int
    started_at: str
    ends_at: str
    model_hash: str
    accuracy: Optional[float] = None


@dataclass
class TransferSession:
    """Cross-device transfer session."""

    session_id: str
    status: str
    source_device: str
    target_device: str
    model_size: int
    transferred_bytes: int
    created_at: str
    expires_at: str
    download_url: Optional[str] = None


# ============ Exceptions ============


class APIError(Exception):
    """Base API error."""

    def __init__(
        self, message: str, status_code: int = 500, response: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class AuthenticationError(APIError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class RateLimitError(APIError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class CircuitBreakerError(APIError):
    """Circuit breaker is open."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status_code=503)


# ============ Circuit Breaker ============


class CircuitBreaker:
    """Circuit breaker for API calls."""

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._check_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self._record_failure()
        else:
            await self._record_success()

    async def _check_state(self):
        async with self._lock:
            if self.state == self.STATE_OPEN:
                if self.last_failure_time:
                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self.state = self.STATE_HALF_OPEN
                    else:
                        raise CircuitBreakerError()

    async def _record_failure(self):
        async with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = self.STATE_OPEN
                self.last_failure_time = time.time()

    async def _record_success(self):
        async with self._lock:
            self.failure_count = 0
            self.state = self.STATE_CLOSED


# ============ Token Manager ============


class TokenManager:
    """Manages API tokens with automatic refresh."""

    def __init__(self, config: CloudConfig, api_key: Optional[APIKey] = None):
        self.config = config
        self.api_key = api_key
        self._token: Optional[APIToken] = None
        self._refresh_lock = asyncio.Lock()
        self._token_file = Path(os.path.expanduser(TOKEN_FILE))
        self._token_file.parent.mkdir(parents=True, exist_ok=True)

    @property
    def token(self) -> Optional[APIToken]:
        """Get current token."""
        return self._token

    @token.setter
    def token(self, value: APIToken):
        """Set token and save to file."""
        self._token = value
        self._save_token()

    def _save_token(self):
        """Save token to file."""
        if self._token:
            data = {
                "access_token": self._token.access_token,
                "refresh_token": self._token.refresh_token,
                "token_type": self._token.token_type,
                "expires_at": self._token.expires_at.isoformat(),
                "scope": self._token.scope,
            }
            with open(self._token_file, "w") as f:
                json.dump(data, f)

    def load_token(self) -> Optional[APIToken]:
        """Load token from file."""
        if not self._token_file.exists():
            return None

        try:
            with open(self._token_file, "r") as f:
                data = json.load(f)
            return APIToken(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data["token_type"],
                expires_at=datetime.fromisoformat(data["expires_at"]),
                scope=data.get("scope", ""),
            )
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            return None

    async def get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self._token is None:
            self._token = self.load_token()

        if self._token is None:
            raise AuthenticationError("No token available. Please authenticate first.")

        if self._token.is_expired:
            await self.refresh_access_token()

        return self._token.access_token

    async def refresh_access_token(self):
        """Refresh the access token."""
        if not self._token or not self._token.refresh_token:
            raise AuthenticationError("Cannot refresh token")

        async with self._refresh_lock:
            # Double-check after acquiring lock
            if self._token and not self._token.is_expired:
                return

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.api_url}{APIEndpoint.AUTH_REFRESH.value}",
                    json={"refresh_token": self._token.refresh_token},
                    timeout=self.config.timeout,
                ) as response:
                    if response.status == 401:
                        raise AuthenticationError("Refresh token expired")

                    data = await response.json()
                    self._token = APIToken(
                        access_token=data["access_token"],
                        refresh_token=data.get(
                            "refresh_token", self._token.refresh_token
                        ),
                        token_type=data["token_type"],
                        expires_at=datetime.now()
                        + timedelta(seconds=data["expires_in"]),
                        scope=data.get("scope", ""),
                    )
                    self._save_token()

    async def authenticate(self, credentials: Dict) -> APIToken:
        """Authenticate with API credentials."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.api_url}{APIEndpoint.AUTH_TOKEN.value}",
                json=credentials,
                timeout=self.config.timeout,
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise AuthenticationError(f"Authentication failed: {error}")

                data = await response.json()
                self._token = APIToken(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    token_type=data["token_type"],
                    expires_at=datetime.now() + timedelta(seconds=data["expires_in"]),
                    scope=data.get("scope", ""),
                )
                self._save_token()
                return self._token

    async def revoke(self):
        """Revoke current token."""
        if self._token:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.config.api_url}{APIEndpoint.AUTH_REVOKE.value}",
                    json={"token": self._token.access_token},
                    timeout=self.config.timeout,
                )
            self._token = None
            if self._token_file.exists():
                self._token_file.unlink()


# ============ Cache Manager ============


class APICache:
    """Simple file-based API cache."""

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl: int = 300):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Optional[Dict]:
        """Get cached response."""
        if not self.ttl:
            return None

        path = self._get_cache_path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Check expiry
            if "expires_at" in data:
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now() > expires_at:
                    path.unlink()
                    return None

            return data.get("response")
        except Exception:
            return None

    def set(self, key: str, response: Dict):
        """Cache a response."""
        if not self.ttl:
            return

        path = self._get_cache_path(key)
        data = {
            "response": response,
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=self.ttl)).isoformat(),
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def clear(self):
        """Clear all cached data."""
        for file in self.cache_dir.glob("*.json"):
            file.unlink()


# ============ HTTP API Client ============


class SkillsArenaCloudClient:
    """
    Production HTTP client for Skills Arena Cloud API.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker pattern
    - Token management with auto-refresh
    - Response caching
    - Rate limiting
    """

    def __init__(self, config: Optional[CloudConfig] = None):
        self.config = config or CloudConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._token_manager: Optional[TokenManager] = None
        self._cache = (
            APICache(ttl=self.config.cache_ttl) if self.config.enable_cache else None
        )
        self._circuit_breaker = CircuitBreaker()
        self._rate_limit_window = 0.0
        self._rate_limit_count = 0

    @property
    def token_manager(self) -> TokenManager:
        """Get token manager, creating if necessary."""
        if self._token_manager is None:
            self._token_manager = TokenManager(self.config)
        return self._token_manager

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers=await self._get_headers(),
            )
        return self._session

    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Client-Version": "3.0.0",
            "X-Client-Type": "openclaw-sdk",
        }

        if self._token_manager and self._token_manager.token:
            try:
                headers["Authorization"] = (
                    f"Bearer {await self._token_manager.get_valid_token()}"
                )
            except AuthenticationError:
                pass

        return headers

    async def _check_rate_limit(self):
        """Check and update rate limit."""
        now = time.time()
        window = 60.0  # 1 minute

        if now - self._rate_limit_window > window:
            self._rate_limit_window = now
            self._rate_limit_count = 0

        if self._rate_limit_count >= self.config.rate_limit:
            raise RateLimitError("Rate limit exceeded", retry_after=int(window))

        self._rate_limit_count += 1

    def _parse_rate_limit(self, headers: Dict) -> Optional[RateLimitInfo]:
        """Parse rate limit info from response headers."""
        try:
            limit = int(headers.get("X-RateLimit-Limit", 0))
            remaining = int(headers.get("X-RateLimit-Remaining", 0))
            reset_at_str = headers.get("X-RateLimit-Reset")
            reset_at = (
                datetime.fromisoformat(reset_at_str) if reset_at_str else datetime.now()
            )
            return RateLimitInfo(limit=limit, remaining=remaining, reset_at=reset_at)
        except (ValueError, TypeError):
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_auth: bool = True,
        cache_key: Optional[str] = None,
    ) -> APIResponse:
        """Make an API request with retry logic."""
        await self._check_rate_limit()

        # Check cache for GET requests
        if method.upper() == "GET" and cache_key and self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {endpoint}")
                return APIResponse(success=True, data=cached)

        url = f"{self.config.api_url}{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        async with CircuitBreaker():
            session = await self._get_session()

            try:
                async with session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=await self._get_headers(),
                ) as response:
                    rate_limit = self._parse_rate_limit(response.headers)

                    if response.status == 429:
                        raise RateLimitError(
                            "Rate limit exceeded",
                            retry_after=int(response.headers.get("Retry-After", 60)),
                        )

                    if response.status == 401:
                        # Try to refresh token and retry
                        if use_auth and self._token_manager:
                            try:
                                await self._token_manager.refresh_access_token()
                                return await self._request(
                                    method,
                                    endpoint,
                                    params,
                                    json_data,
                                    use_auth,
                                    cache_key,
                                )
                            except AuthenticationError:
                                pass
                        raise AuthenticationError()

                    if response.status >= 400:
                        error_text = await response.text()
                        raise APIError(
                            f"API error: {response.status}",
                            status_code=response.status,
                            response=error_text,
                        )

                    data = await response.json()

                    # Cache successful GET responses
                    if method.upper() == "GET" and self._cache and cache_key:
                        self._cache.set(cache_key, data)

                    return APIResponse(
                        success=True,
                        data=data,
                        status_code=response.status,
                        rate_limit=rate_limit,
                    )

            except aiohttp.ClientError as e:
                logger.error(f"HTTP request failed: {e}")
                raise

    # ============ Public API Methods ============

    async def authenticate(
        self, username: str, password: str, mfa_code: Optional[str] = None
    ) -> APIToken:
        """Authenticate with username/password."""
        credentials = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        if mfa_code:
            credentials["mfa_code"] = mfa_code
        return await self.token_manager.authenticate(credentials)

    async def authenticate_api_key(self, key_id: str, secret: str) -> APIToken:
        """Authenticate with API key."""
        credentials = {
            "grant_type": "api_key",
            "key_id": key_id,
            "secret": secret,
        }
        return await self.token_manager.authenticate(credentials)

    async def get_skills(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SkillMetadata]:
        """Get list of skills from the cloud."""
        params = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if tags:
            params["tags"] = ",".join(tags)

        cache_key = f"skills:{hash(json.dumps(params, sort_keys=True))}"
        response = await self._request(
            "GET",
            APIEndpoint.SKILLS_LIST.value,
            params=params,
            cache_key=cache_key,
        )

        skills = []
        for item in response.data.get("skills", []):
            skills.append(
                SkillMetadata(
                    skill_id=item["skill_id"],
                    name=item["name"],
                    description=item["description"],
                    category=item["category"],
                    tags=item.get("tags", []),
                    version=item["version"],
                    author=item["author"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    rating=item.get("rating", 0.0),
                    rating_count=item.get("rating_count", 0),
                    usage_count=item.get("usage_count", 0),
                    is_premium=item.get("is_premium", False),
                    requires_consent=item.get("requires_consent", False),
                )
            )
        return skills

    async def get_recommendations(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        exclude_skills: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SkillMetadata]:
        """Get personalized recommendations."""
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if category:
            params["category"] = category
        if exclude_skills:
            params["exclude"] = ",".join(exclude_skills)

        response = await self._request(
            "POST",
            APIEndpoint.SKILLS_RECOMMEND.value,
            json_data=params,
            use_auth=user_id is not None,
            cache_key=f"recommendations:{user_id}:{limit}",
        )

        skills = []
        for item in response.data.get("recommendations", []):
            skills.append(
                SkillMetadata(
                    skill_id=item["skill_id"],
                    name=item["name"],
                    description=item["description"],
                    category=item.get("category", "general"),
                    tags=item.get("tags", []),
                    version=item.get("version", "1.0"),
                    author=item.get("author", "unknown"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                )
            )
        return skills

    async def search_skills(
        self, query: str, limit: int = 20, filters: Optional[Dict] = None
    ) -> List[SkillMetadata]:
        """Search for skills."""
        params = {"q": query, "limit": limit}
        if filters:
            params.update(filters)

        response = await self._request(
            "GET",
            APIEndpoint.SKILLS_SEARCH.value,
            params=params,
            cache_key=f"search:{query}:{limit}",
        )

        skills = []
        for item in response.data.get("results", []):
            skills.append(
                SkillMetadata(
                    skill_id=item["skill_id"],
                    name=item["name"],
                    description=item["description"],
                    category=item.get("category", "general"),
                    tags=item.get("tags", []),
                    version=item.get("version", "1.0"),
                    author=item.get("author", "unknown"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                )
            )
        return skills

    async def rate_skill(self, skill_id: str, rating: int, user_id: str) -> bool:
        """Rate a skill."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        response = await self._request(
            "POST",
            APIEndpoint.SKILLS_RATE.value.format(skill_id=skill_id),
            json_data={"rating": rating, "user_id": user_id},
            use_auth=True,
        )
        return response.success

    # ============ Federated Learning API ============

    async def fl_join_round(self, round_id: str, device_info: Dict) -> bool:
        """Join a federated learning round."""
        response = await self._request(
            "POST",
            APIEndpoint.FL_JOIN.value,
            json_data={"round_id": round_id, "device_info": device_info},
            use_auth=True,
        )
        return response.success

    async def fl_get_rounds(self, active_only: bool = True) -> List[FederatedRound]:
        """Get available federated learning rounds."""
        params = {"active": active_only}
        response = await self._request(
            "GET", APIEndpoint.FL_ROUNDS.value, params=params, use_auth=True
        )

        rounds = []
        for item in response.data.get("rounds", []):
            rounds.append(
                FederatedRound(
                    round_id=item["round_id"],
                    status=item["status"],
                    n_participants=item["n_participants"],
                    n_required=item["n_required"],
                    started_at=item["started_at"],
                    ends_at=item["ends_at"],
                    model_hash=item["model_hash"],
                    accuracy=item.get("accuracy"),
                )
            )
        return rounds

    async def fl_upload_update(
        self, round_id: str, model_update: Dict, signature: str
    ) -> bool:
        """Upload model update for a federated learning round."""
        response = await self._request(
            "POST",
            APIEndpoint.FL_UPLOAD.value,
            json_data={
                "round_id": round_id,
                "model_update": model_update,
                "signature": signature,
            },
            use_auth=True,
        )
        return response.success

    # ============ Cross-Device Transfer API ============

    async def transfer_init(
        self, model_id: str, source_device: str, target_device: str
    ) -> TransferSession:
        """Initiate a cross-device transfer."""
        response = await self._request(
            "POST",
            APIEndpoint.TRANSFER_INIT.value,
            json_data={
                "model_id": model_id,
                "source_device": source_device,
                "target_device": target_device,
            },
            use_auth=True,
        )

        data = response.data
        return TransferSession(
            session_id=data["session_id"],
            status=data["status"],
            source_device=source_device,
            target_device=target_device,
            model_size=data["model_size"],
            transferred_bytes=0,
            created_at=data["created_at"],
            expires_at=data["expires_at"],
            download_url=data.get("download_url"),
        )

    async def transfer_get_status(self, session_id: str) -> TransferSession:
        """Get transfer session status."""
        response = await self._request(
            "GET",
            APIEndpoint.TRANSFER_STATUS.value.format(session_id=session_id),
            use_auth=True,
        )

        data = response.data
        return TransferSession(
            session_id=data["session_id"],
            status=data["status"],
            source_device=data["source_device"],
            target_device=data["target_device"],
            model_size=data["model_size"],
            transferred_bytes=data.get("transferred_bytes", 0),
            created_at=data["created_at"],
            expires_at=data["expires_at"],
            download_url=data.get("download_url"),
        )

    async def transfer_complete(self, session_id: str, checksum: str) -> bool:
        """Complete a transfer session."""
        response = await self._request(
            "POST",
            APIEndpoint.TRANSFER_COMPLETE.value.format(session_id=session_id),
            json_data={"checksum": checksum},
            use_auth=True,
        )
        return response.success

    # ============ Analytics API ============

    async def get_usage_analytics(
        self, skill_id: Optional[str] = None, days: int = 30
    ) -> Dict:
        """Get usage analytics."""
        params = {"days": days}
        if skill_id:
            params["skill_id"] = skill_id

        response = await self._request(
            "GET",
            APIEndpoint.ANALYTICS_USAGE.value,
            params=params,
            use_auth=True,
        )
        return response.data or {}

    async def close(self):
        """Close the client and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None


# ============ gRPC Client ============


class SkillsArenaGRPCClient:
    """
    gRPC client for high-performance Skills Arena API.

    This provides an alternative to HTTP for low-latency communication.
    Requires the skills_arena_pb2 and skills_arena_pb2_grpc modules.
    """

    def __init__(self, server: str = GRPC_SERVER):
        self.server = server
        self._channel = None
        self._stub = None

    def connect(self, credentials: Optional[grpc.ChannelCredentials] = None):
        """Connect to gRPC server."""
        if credentials:
            self._channel = grpc.aio.secure_channel(self.server, credentials)
        else:
            self._channel = grpc.aio.insecure_channel(self.server)

        # Import generated protobuf modules
        # from skills_arena_pb2 import SkillsArenaStub
        # self._stub = SkillsArenaStub(self._channel)

    async def close(self):
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()

    # Add gRPC-specific methods here as needed


# ============ CLI Interface ============


class SkillsArenaCLI:
    """
    Command-line interface for Skills Arena Cloud operations.

    Provides commands for:
    - Authentication
    - Skill discovery and search
    - Federated learning participation
    - Cross-device transfer
    - Analytics
    """

    def __init__(self):
        self.client = SkillsArenaCloudClient()
        self._authenticated = False

    def run(self):
        """Run the interactive CLI."""
        print("\n" + "=" * 60)
        print("Skills Arena Cloud CLI - Version 3.0.0")
        print("=" * 60)

        while True:
            command = input("\nskills-arena> ").strip()

            if command in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if not command:
                continue

            parts = command.split()
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                self._execute_command(cmd, args)
            except Exception as e:
                print(f"Error: {e}")

    def _execute_command(self, cmd: str, args: List[str]):
        """Execute a CLI command."""
        commands = {
            "auth": self._cmd_auth,
            "login": self._cmd_auth,
            "logout": self._cmd_logout,
            "skills": self._cmd_skills,
            "search": self._cmd_search,
            "recommend": self._cmd_recommend,
            "rate": self._cmd_rate,
            "fl": self._cmd_federated,
            "transfer": self._cmd_transfer,
            "analytics": self._cmd_analytics,
            "help": self._cmd_help,
            "?": self._cmd_help,
        }

        if cmd not in commands:
            print(f"Unknown command: {cmd}")
            self._cmd_help()
            return

        commands[cmd](args)

    def _cmd_auth(self, args: List[str]):
        """Authenticate with the server."""
        if not args:
            username = input("Username: ")
            password = input("Password: ")
        else:
            username, password = args[0], args[1] if len(args) > 1 else ""

        if not password:
            import getpass

            password = getpass.getpass("Password: ")

        try:
            token = asyncio.run(self.client.authenticate(username, password))
            self._authenticated = True
            print(f"✓ Authentication successful!")
            print(f"  Token type: {token.token_type}")
            print(f"  Expires in: {token.expires_in} seconds")
        except AuthenticationError as e:
            print(f"✗ Authentication failed: {e}")

    def _cmd_logout(self, args: List[str]):
        """Logout and revoke token."""
        asyncio.run(self.client.token_manager.revoke())
        self._authenticated = False
        print("✓ Logged out successfully")

    def _cmd_skills(self, args: List[str]):
        """List available skills."""
        category = args[0] if args else None
        limit = int(args[1]) if len(args) > 1 else 20

        skills = asyncio.run(self.client.get_skills(category=category, limit=limit))

        print(f"\nAvailable Skills ({len(skills)}):")
        print("-" * 60)
        for i, skill in enumerate(skills, 1):
            print(f"{i:2}. {skill.name}")
            print(f"    ID: {skill.skill_id}")
            print(f"    Category: {skill.category}")
            print(f"    Rating: {skill.rating:.1f} ({skill.rating_count} votes)")
            print(f"    Usage: {skill.usage_count}")
            print()

    def _cmd_search(self, args: List[str]):
        """Search for skills."""
        if not args:
            print("Usage: search <query>")
            return

        query = " ".join(args)
        skills = asyncio.run(self.client.search_skills(query))

        print(f"\nSearch Results for '{query}' ({len(skills)}):")
        print("-" * 60)
        for i, skill in enumerate(skills, 1):
            print(f"{i:2}. {skill.name}")
            print(f"    {skill.description[:100]}...")
            print()

    def _cmd_recommend(self, args: List[str]):
        """Get recommendations."""
        limit = int(args[0]) if args else 10

        if not self._authenticated:
            print("⚠ Not authenticated. Using guest recommendations.")

        recommendations = asyncio.run(self.client.get_recommendations(limit=limit))

        print(f"\nRecommendations ({len(recommendations)}):")
        print("-" * 60)
        for i, skill in enumerate(recommendations, 1):
            print(f"{i:2}. {skill.name}")
            print(f"    Category: {skill.category}")
            print()

    def _cmd_rate(self, args: List[str]):
        """Rate a skill."""
        if len(args) < 2:
            print("Usage: rate <skill_id> <rating>")
            return

        skill_id, rating = args[0], int(args[1])

        if not 1 <= rating <= 5:
            print("Rating must be between 1 and 5")
            return

        success = asyncio.run(self.client.rate_skill(skill_id, rating, "current_user"))
        if success:
            print(f"✓ Rated {skill_id}: {rating} stars")
        else:
            print("✗ Rating failed")

    def _cmd_federated(self, args: List[str]):
        """Federated learning commands."""
        if not args:
            print("Usage: fl <command>")
            print("Commands: list, join <round_id>, status")
            return

        subcmd = args[0]

        if subcmd == "list":
            rounds = asyncio.run(self.client.fl_get_rounds(active_only=True))
            print("\nActive Federated Learning Rounds:")
            print("-" * 60)
            for round_info in rounds:
                print(f"ID: {round_info.round_id}")
                print(f"Status: {round_info.status}")
                print(
                    f"Participants: {round_info.n_participants}/{round_info.n_required}"
                )
                print()

        elif subcmd == "join":
            if len(args) < 2:
                print("Usage: fl join <round_id>")
                return

            round_id = args[1]
            device_info = {"type": "desktop", "os": "windows"}
            success = asyncio.run(self.client.fl_join_round(round_id, device_info))

            if success:
                print(f"✓ Joined federated learning round: {round_id}")
            else:
                print("✗ Failed to join round")

        else:
            print(f"Unknown federated learning command: {subcmd}")

    def _cmd_transfer(self, args: List[str]):
        """Cross-device transfer commands."""
        if len(args) < 3:
            print("Usage: transfer <command> <model_id> <source> <target>")
            print("Commands: init, status <session_id>, complete <session_id>")
            return

        subcmd = args[0]

        if subcmd == "init":
            model_id, source, target = args[1], args[2], args[3]
            session = asyncio.run(self.client.transfer_init(model_id, source, target))
            print(f"✓ Transfer initiated")
            print(f"  Session ID: {session.session_id}")
            print(f"  Status: {session.status}")
            print(f"  Model size: {session.model_size} bytes")
            print(f"  Download URL: {session.download_url}")

        elif subcmd == "status":
            session_id = args[1]
            session = asyncio.run(self.client.transfer_get_status(session_id))
            print(f"Transfer Status:")
            print(f"  Session: {session.session_id}")
            print(f"  Status: {session.status}")
            print(f"  Transferred: {session.transferred_bytes}/{session.model_size}")

        elif subcmd == "complete":
            session_id = args[1]
            success = asyncio.run(self.client.transfer_complete(session_id, "checksum"))
            if success:
                print(f"✓ Transfer completed: {session_id}")
            else:
                print("✗ Transfer completion failed")

    def _cmd_analytics(self, args: List[str]):
        """Get analytics."""
        days = int(args[0]) if args else 30
        analytics = asyncio.run(self.client.get_usage_analytics(days=days))
        print(f"\nUsage Analytics (last {days} days):")
        print("-" * 60)
        print(json.dumps(analytics, indent=2))

    def _cmd_help(self, args: List[str] = None):
        """Show help."""
        print("\nAvailable Commands:")
        print("=" * 60)
        print("auth [username] [password]  - Authenticate with server")
        print("logout                       - Logout and revoke token")
        print("skills [category] [limit]    - List available skills")
        print("search <query>               - Search for skills")
        print("recommend [limit]            - Get personalized recommendations")
        print("rate <skill_id> <rating>     - Rate a skill (1-5)")
        print("fl list                      - List active federated learning rounds")
        print("fl join <round_id>           - Join a federated learning round")
        print("transfer init <model> <src> <tgt>  - Initiate cross-device transfer")
        print("transfer status <session_id> - Check transfer status")
        print("transfer complete <session>  - Complete a transfer")
        print("analytics [days]             - Get usage analytics")
        print("help, ?                      - Show this help")
        print("exit, quit, q                - Exit CLI")
        print()


# ============ OpenClaw Agent Simulator ============


class OpenClawAgentSimulator:
    """
    Simulates an OpenClaw agent interacting with Skills Arena Cloud.

    This is used for testing and demonstration purposes.
    """

    def __init__(self, agent_id: str, agent_type: str = "general"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.client = SkillsArenaCloudClient()
        self._authenticated = False
        self._skills_used: List[Dict] = []
        self._participation_history: List[Dict] = []

    async def authenticate(self, username: str, password: str):
        """Authenticate the agent."""
        await self.client.authenticate(username, password)
        self._authenticated = True
        print(f"[{self.agent_id}] Authenticated successfully")

    async def discover_skills(
        self, category: Optional[str] = None
    ) -> List[SkillMetadata]:
        """Discover available skills."""
        skills = await self.client.get_skills(category=category, limit=20)
        print(f"[{self.agent_id}] Discovered {len(skills)} skills")
        return skills

    async def get_recommendations(self, limit: int = 5) -> List[SkillMetadata]:
        """Get personalized recommendations."""
        if not self._authenticated:
            print(f"[{self.agent_id}] Not authenticated, using guest recommendations")
            return await self.client.get_recommendations(limit=limit)
        return await self.client.get_recommendations(user_id=self.agent_id, limit=limit)

    async def search_skills(self, query: str) -> List[SkillMetadata]:
        """Search for skills."""
        return await self.client.search_skills(query)

    async def use_skill(self, skill_id: str, duration: float = 0.5):
        """Simulate using a skill."""
        self._skills_used.append(
            {
                "skill_id": skill_id,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
            }
        )
        print(f"[{self.agent_id}] Used skill: {skill_id} ({duration:.2f}s)")

    async def rate_skill(self, skill_id: str, rating: int):
        """Rate a skill."""
        await self.client.rate_skill(skill_id, rating, self.agent_id)
        print(f"[{self.agent_id}] Rated {skill_id}: {rating} stars")

    async def join_federated_round(self, round_id: str, device_info: Dict):
        """Join a federated learning round."""
        success = await self.client.fl_join_round(round_id, device_info)
        if success:
            self._participation_history.append(
                {
                    "round_id": round_id,
                    "action": "join",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            print(f"[{self.agent_id}] Joined FL round: {round_id}")
        return success

    async def upload_model_update(
        self, round_id: str, model_update: Dict, signature: str
    ):
        """Upload model update."""
        success = await self.client.fl_upload_update(round_id, model_update, signature)
        if success:
            self._participation_history.append(
                {
                    "round_id": round_id,
                    "action": "upload",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            print(f"[{self.agent_id}] Uploaded model update for round: {round_id}")
        return success

    async def run_workflow(self, task: str, use_federated: bool = True) -> Dict:
        """
        Run a complete agent workflow.

        1. Discover skills
        2. Get recommendations
        3. Execute task using recommended skill
        4. Optionally join federated learning
        """
        print(f"\n[{self.agent_id}] Running workflow: {task}")

        # Step 1: Get recommendations
        recommendations = await self.get_recommendations(limit=3)
        if not recommendations:
            recommendations = await self.discover_skills()

        if not recommendations:
            print(f"[{self.agent_id}] No skills available")
            return {"status": "failed", "reason": "no_skills"}

        # Step 2: Select and use a skill
        selected_skill = recommendations[0]
        await self.use_skill(selected_skill.skill_id)

        # Step 3: Rate the skill
        await self.rate_skill(selected_skill.skill_id, 4)

        # Step 4: Optionally participate in federated learning
        if use_federated:
            rounds = await self.client.fl_get_rounds(active_only=True)
            if rounds:
                round_info = rounds[0]
                await self.join_federated_round(
                    round_info.round_id,
                    {"agent_type": self.agent_type, "model_version": "1.0"},
                )
                await self.upload_model_update(
                    round_info.round_id,
                    {"gradients": [0.1, 0.2, 0.3]},
                    "mock_signature",
                )

        return {
            "status": "completed",
            "task": task,
            "skill_used": selected_skill.skill_id,
            "skills_used_total": len(self._skills_used),
            "fl_participations": len(self._participation_history),
        }

    def get_summary(self) -> Dict:
        """Get agent summary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "authenticated": self._authenticated,
            "skills_used": len(self._skills_used),
            "fl_participations": len(self._participation_history),
            "total_usage_time": sum(s["duration"] for s in self._skills_used),
        }

    async def close(self):
        """Close the client."""
        await self.client.close()


# ============ Multi-Agent Simulation ============


async def run_multi_agent_simulation(
    agent_count: int = 5,
    tasks_per_agent: int = 3,
    use_federated: bool = True,
):
    """
    Run a multi-agent simulation.

    Creates multiple OpenClaw agents that interact with Skills Arena Cloud.
    """
    print("\n" + "=" * 60)
    print("Skills Arena Multi-Agent Simulation")
    print("=" * 60)

    agent_types = [
        "coding_assistant",
        "research_scholar",
        "writing_partner",
        "data_analyst",
        "generalist",
    ]

    agents = []
    for i in range(agent_count):
        agent_id = f"agent-{i + 1:02d}"
        agent_type = agent_types[i % len(agent_types)]
        agent = OpenClawAgentSimulator(agent_id, agent_type)
        agents.append(agent)

    # Run workflows for each agent
    results = []
    for i, agent in enumerate(agents):
        print(f"\n{'=' * 60}")
        print(f"Agent {i + 1}/{agent_count}: {agent.agent_id} ({agent.agent_type})")

        # Authenticate (using mock credentials)
        try:
            await agent.authenticate(f"user_{i + 1}", "password")
        except Exception as e:
            print(f"[{agent.agent_id}] Auth skipped: {e}")

        # Run tasks
        for j in range(tasks_per_agent):
            task = f"task-{j + 1}"
            result = await agent.run_workflow(task, use_federated=use_federated)
            results.append(result)

        # Print summary
        summary = agent.get_summary()
        print(f"\n[{agent.agent_id}] Summary:")
        print(f"  Skills used: {summary['skills_used']}")
        print(f"  FL participations: {summary['fl_participations']}")
        print(f"  Total usage time: {summary['total_usage_time']:.2f}s")

        await agent.close()

    # Overall statistics
    print(f"\n{'=' * 60}")
    print("Simulation Complete!")
    print(f"Total agents: {len(agents)}")
    print(f"Tasks per agent: {tasks_per_agent}")
    print(f"Total tasks completed: {len(results)}")
    print(
        f"Tasks with FL: {sum(1 for r in results if r.get('fl_participations', 0) > 0)}"
    )

    return results


# ============ Main ============


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Skills Arena Cloud CLI")
    parser.add_argument(
        "--mode",
        choices=["cli", "simulate", "api"],
        default="cli",
        help="Running mode",
    )
    parser.add_argument(
        "--agents", type=int, default=5, help="Number of agents for simulation"
    )
    parser.add_argument(
        "--tasks", type=int, default=3, help="Tasks per agent for simulation"
    )
    parser.add_argument("--url", help="API server URL")
    parser.add_argument("--api-key", help="API key for authentication")

    args = parser.parse_args()

    if args.url:
        config = CloudConfig(api_url=args.url.rstrip("/"))
        client = SkillsArenaCloudClient(config=config)
    else:
        client = SkillsArenaCloudClient()

    if args.mode == "cli":
        cli = SkillsArenaCLI()
        cli.client = client
        cli.run()

    elif args.mode == "simulate":
        await run_multi_agent_simulation(
            agent_count=args.agents, tasks_per_agent=args.tasks
        )

    elif args.mode == "api":
        # Run a quick API test
        print("\nTesting API connection...")

        # Try to get skills (may fail without auth)
        try:
            skills = await client.get_skills(limit=5)
            print(f"✓ Retrieved {len(skills)} skills from cloud")
        except APIError as e:
            print(f"⚠ API test (expected to fail without auth): {e}")

        await client.close()

    print("\n✓ Done!")


if __name__ == "__main__":
    asyncio.run(main())
