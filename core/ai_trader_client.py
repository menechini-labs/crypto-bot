"""AI-Trader (ai4trade.ai) platform client.

Integrates crypto-bot with AI-Trader marketplace:
- Register/login agents
- Fetch signal feed as blended scoring input
- Publish signals when guard approves
- Heartbeat polling for notifications
- Copy trading following
- Challenge participation
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from core.credential_store import CredentialStore

logger = logging.getLogger(__name__)

BASE_URL = "https://ai4trade.ai/api"
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    ".ai-trader-credentials.json",
)

# Lazy-initialized credential store singleton for this module
_cred_store_instance: CredentialStore | None = None


def _get_cred_store() -> CredentialStore:
    global _cred_store_instance
    if _cred_store_instance is None:
        _cred_store_instance = CredentialStore()
    return _cred_store_instance


@dataclass
class AiTraderConfig:
    """Configuration for AI-Trader integration."""

    token: str = ""
    agent_id: int = 0
    name: str = "CryptoBot-BR"
    email: str = ""
    password: str = ""
    enabled: bool = False
    publish_threshold: float = 0.65  # min blended score to publish signal
    feed_poll_seconds: int = 300  # how often to pull signal feed
    heartbeat_seconds: int = 30  # heartbeat poll interval
    max_signals_per_feed: int = 20


@dataclass
class AiTraderSignal:
    """A signal from the AI-Trader feed."""

    id: int
    agent_id: int
    agent_name: str
    type: str  # position, trade, strategy, discussion
    symbol: str
    side: Optional[str]  # long, short for positions
    entry_price: Optional[float]
    quantity: Optional[float]
    content: str
    reply_count: int
    participant_count: int
    last_reply_at: str
    is_following_author: bool = False
    timestamp: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "AiTraderSignal":
        return cls(
            id=d.get("id", 0),
            agent_id=d.get("agent_id", 0),
            agent_name=d.get("agent_name", "unknown"),
            type=d.get("type", "discussion"),
            symbol=d.get("symbol", ""),
            side=d.get("side"),
            entry_price=d.get("entry_price"),
            quantity=d.get("quantity"),
            content=d.get("content", ""),
            reply_count=d.get("reply_count", 0),
            participant_count=d.get("participant_count", 0),
            last_reply_at=d.get("last_reply_at", ""),
            is_following_author=d.get("is_following_author", False),
            timestamp=d.get("timestamp", 0),
        )


@dataclass
class AiTraderHeartbeat:
    """Heartbeat response from AI-Trader."""

    agent_id: int
    server_time: str
    recommended_poll_interval_seconds: int = 30
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    message_count: int = 0
    unread_count: int = 0
    remaining_unread_count: int = 0
    has_more_messages: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "AiTraderHeartbeat":
        return cls(
            agent_id=d.get("agent_id", 0),
            server_time=d.get("server_time", ""),
            recommended_poll_interval_seconds=d.get(
                "recommended_poll_interval_seconds", 30
            ),
            messages=d.get("messages", []),
            tasks=d.get("tasks", []),
            message_count=d.get("message_count", 0),
            unread_count=d.get("unread_count", 0),
            remaining_unread_count=d.get("remaining_unread_count", 0),
            has_more_messages=d.get("has_more_messages", False),
        )


def load_credentials() -> dict:
    """Load saved credentials from disk.
    
    Prefers encrypted credential store if available.
    Falls back to plaintext JSON for backward compat (migration path).
    """
    cred_store = _get_cred_store()
    if cred_store.exists():
        try:
            return {k: cred_store.get(k) for k in cred_store.keys()}
        except Exception as e:
            logger.warning("Failed to load from encrypted store: %s", e)
            # fall through to plaintext fallback
    
    if not os.path.exists(CREDENTIALS_PATH):
        return {}
    try:
        with open(CREDENTIALS_PATH) as f:
            data = json.load(f)
        # Migrate to encrypted store on first plaintext read
        try:
            cred_store.migrate_from_plaintext(CREDENTIALS_PATH)
            logger.info("Migrated plaintext credentials to encrypted store")
        except Exception as e:
            logger.warning("Credential migration failed (will retry): %s", e)
        return data
    except Exception as e:
        logger.warning("Failed to load AI-Trader credentials: %s", e)
        return {}


def save_credentials(data: dict) -> None:
    """Save credentials to encrypted store.
    
    Falls back to plaintext JSON if encrypted store unavailable (backward compat).
    """
    cred_store = _get_cred_store()
    try:
        for k, v in data.items():
            cred_store.set(k, str(v))
        logger.info("AI-Trader credentials saved to encrypted store")
    except Exception as e:
        logger.warning("Failed to save to encrypted store, falling back: %s", e)
        with open(CREDENTIALS_PATH, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("AI-Trader credentials saved to %s", CREDENTIALS_PATH)


class AiTraderClient:
    """HTTP client for AI-Trader platform API."""

    def __init__(self, config: Optional[AiTraderConfig] = None):
        self.config = config or AiTraderConfig()
        creds = load_credentials()
        if not self.config.token:
            self.config.token = creds.get("token", "")
        if not self.config.agent_id:
            self.config.agent_id = creds.get("agent_id", 0)
        if not self.config.email:
            self.config.email = creds.get("email", "")
        if not self.config.password:
            self.config.password = creds.get("password", "")

        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=15.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def _headers(self) -> dict:
        if self.config.token:
            return {"Authorization": f"Bearer {self.config.token}"}
        return {}

    # ── Registration / Auth ──────────────────────────────────────────

    def register(
        self, name: str, email: str, password: str
    ) -> dict:
        """Register a new agent on AI-Trader."""
        resp = self._client.post(
            "/claw/agents/selfRegister",
            json={"name": name, "email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.config.token = data["token"]
        self.config.agent_id = data["agent_id"]
        self.config.name = data.get("name", name)
        save_credentials({
            "platform": "ai4trade.ai",
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "email": email,
            "password": password,
            "token": self.config.token,
        })
        self.config.enabled = True
        return data

    def login(self, email: str, password: str) -> dict:
        """Login existing agent."""
        resp = self._client.post(
            "/claw/agents/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.config.token = data["token"]
        self.config.agent_id = data.get("agent_id", self.config.agent_id)
        save_credentials({
            "platform": "ai4trade.ai",
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "email": email,
            "password": password,
            "token": self.config.token,
        })
        self.config.enabled = True
        return data

    def get_me(self) -> dict:
        """Get current agent info."""
        resp = self._client.get(
            "/claw/agents/me", headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def exchange_points(self, amount: int) -> dict:
        """Exchange points for cash (1 point = 1000 USD)."""
        resp = self._client.post(
            "/agents/points/exchange",
            headers=self._headers(),
            json={"amount": amount},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Signal Feed ──────────────────────────────────────────────────

    def get_feed(
        self,
        limit: int = 20,
        message_type: Optional[str] = None,
        symbol: Optional[str] = None,
        keyword: Optional[str] = None,
        sort: str = "new",
    ) -> List[AiTraderSignal]:
        """Fetch signal feed from AI-Trader."""
        params: dict = {"limit": limit, "sort": sort}
        if message_type:
            params["message_type"] = message_type
        if symbol:
            params["symbol"] = symbol
        if keyword:
            params["keyword"] = keyword

        resp = self._client.get(
            "/signals/feed",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        signals = data.get("signals", [])
        return [AiTraderSignal.from_dict(s) for s in signals]

    def get_signals_grouped(self, limit: int = 20) -> dict:
        """Get signals grouped by agent (two-level UI)."""
        resp = self._client.get(
            "/signals/grouped",
            params={"limit": limit},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ── Publish Signals ──────────────────────────────────────────────

    def publish_realtime(
        self,
        market: str,
        action: str,
        symbol: str,
        price: float,
        quantity: float,
        content: str = "",
        executed_at: str = "now",
        outcome: Optional[str] = None,
    ) -> dict:
        """Publish a real-time trading signal.

        market: crypto, us-stock, polymarket
        action: buy, sell, short, cover
        executed_at: ISO 8601 or "now" (auto-price)
        """
        body: dict = {
            "market": market,
            "action": action,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "content": content,
            "executed_at": executed_at,
        }
        if outcome:
            body["outcome"] = outcome

        resp = self._client.post(
            "/signals/realtime",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def publish_strategy(
        self,
        market: str,
        title: str,
        content: str,
        symbols: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Publish a strategy analysis."""
        body: dict = {
            "market": market,
            "title": title,
            "content": content,
            "symbols": symbols or [],
            "tags": tags or [],
        }
        resp = self._client.post(
            "/signals/strategy",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def publish_discussion(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Publish a discussion post."""
        body: dict = {
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        resp = self._client.post(
            "/signals/discussion",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def reply_to_signal(
        self, signal_id: int, user_name: str, content: str
    ) -> dict:
        """Reply to a discussion/strategy."""
        resp = self._client.post(
            "/signals/reply",
            headers=self._headers(),
            json={
                "signal_id": signal_id,
                "user_name": user_name or self.config.name,
                "content": content,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Copy Trading ─────────────────────────────────────────────────

    def follow_trader(self, leader_id: int) -> dict:
        """Follow a signal provider."""
        resp = self._client.post(
            "/signals/follow",
            headers=self._headers(),
            json={"leader_id": leader_id},
        )
        resp.raise_for_status()
        return resp.json()

    def unfollow_trader(self, leader_id: int) -> dict:
        """Unfollow a signal provider."""
        resp = self._client.post(
            "/signals/unfollow",
            headers=self._headers(),
            json={"leader_id": leader_id},
        )
        resp.raise_for_status()
        return resp.json()

    def get_following(self) -> dict:
        """Get list of traders I follow."""
        resp = self._client.get(
            "/signals/following", headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> dict:
        """Get current positions (self + copied)."""
        resp = self._client.get(
            "/positions", headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    # ── Heartbeat ────────────────────────────────────────────────────

    def heartbeat(self) -> AiTraderHeartbeat:
        """Poll heartbeat for notifications and tasks."""
        resp = self._client.post(
            "/claw/agents/heartbeat",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return AiTraderHeartbeat.from_dict(resp.json())

    # ── Challenges ───────────────────────────────────────────────────

    def list_challenges(
        self,
        status: str = "active",
        market: str = "crypto",
        limit: int = 20,
    ) -> dict:
        """List available challenges."""
        resp = self._client.get(
            "/challenges",
            params={"status": status, "market": market, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    def join_challenge(self, challenge_key: str) -> dict:
        """Join a challenge competition."""
        resp = self._client.post(
            f"/challenges/{challenge_key}/join",
            headers=self._headers(),
            json={},
        )
        resp.raise_for_status()
        return resp.json()

    def get_challenge_detail(self, challenge_key: str) -> dict:
        """Get challenge details, rules, timing."""
        resp = self._client.get(
            f"/challenges/{challenge_key}",
        )
        resp.raise_for_status()
        return resp.json()

    def get_challenge_portfolio(self, challenge_key: str) -> dict:
        """Get my challenge-only portfolio (individual challenge)."""
        resp = self._client.get(
            f"/challenges/{challenge_key}/portfolio",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ── Team Challenges ──────────────────────────────────────────────

    def list_teams(self, challenge_key: str) -> dict:
        """List teams in a challenge."""
        resp = self._client.get(f"/challenges/{challenge_key}/teams")
        resp.raise_for_status()
        return resp.json()

    def create_team(
        self, challenge_key: str, team_key: str, name: str, role: str = "lead"
    ) -> dict:
        """Create a team in a challenge."""
        resp = self._client.post(
            f"/challenges/{challenge_key}/teams",
            headers=self._headers(),
            json={"team_key": team_key, "name": name, "role": role},
        )
        resp.raise_for_status()
        return resp.json()

    def join_team(self, challenge_key: str, team_id: int, role: str = "risk") -> dict:
        """Join an existing team."""
        resp = self._client.post(
            f"/challenges/{challenge_key}/teams/{team_id}/join",
            headers=self._headers(),
            json={"role": role},
        )
        resp.raise_for_status()
        return resp.json()

    def get_team_portfolio(self, challenge_key: str, team_id: int) -> dict:
        """Get team portfolio."""
        resp = self._client.get(
            f"/challenges/{challenge_key}/teams/{team_id}/portfolio",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def submit_team_submission(
        self,
        challenge_key: str,
        team_id: int,
        submission_type: str,
        content: str,
        prediction_json: Optional[dict] = None,
    ) -> dict:
        """Submit team thesis / proposal / review."""
        body: dict = {
            "submission_type": submission_type,
            "content": content,
        }
        if prediction_json:
            body["prediction_json"] = prediction_json
        resp = self._client.post(
            f"/challenges/{challenge_key}/teams/{team_id}/submissions",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def list_team_submissions(self, challenge_key: str, team_id: int) -> dict:
        """List team submissions."""
        resp = self._client.get(
            f"/challenges/{challenge_key}/teams/{team_id}/submissions",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def vote_on_submission(
        self,
        challenge_key: str,
        submission_id: int,
        vote: str,
        content: str = "",
    ) -> dict:
        """Vote on a team submission."""
        resp = self._client.post(
            f"/challenges/{challenge_key}/submissions/{submission_id}/vote",
            headers=self._headers(),
            json={"vote": vote, "content": content},
        )
        resp.raise_for_status()
        return resp.json()

    def submit_team_trade(
        self,
        challenge_key: str,
        team_id: int,
        side: str,
        symbol: str,
        price: float,
        quantity: float,
        content: str = "",
        accepted_proposal_id: Optional[int] = None,
    ) -> dict:
        """Submit a team trade (must reference accepted proposal)."""
        body: dict = {
            "side": side,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "content": content,
        }
        if accepted_proposal_id:
            body["accepted_proposal_id"] = accepted_proposal_id
        resp = self._client.post(
            f"/challenges/{challenge_key}/teams/{team_id}/trade",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    def get_challenge_leaderboard(self, challenge_key: str) -> dict:
        """Get challenge leaderboard."""
        resp = self._client.get(
            f"/challenges/{challenge_key}/leaderboard",
        )
        resp.raise_for_status()
        return resp.json()

    def submit_challenge_trade(
        self,
        challenge_key: str,
        side: str,
        symbol: str,
        price: float,
        quantity: float,
        content: str = "",
    ) -> dict:
        """Submit a trade to an active challenge."""
        resp = self._client.post(
            f"/challenges/{challenge_key}/trade",
            headers=self._headers(),
            json={
                "side": side,
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "content": content,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Marketplace ──────────────────────────────────────────────────

    def list_marketplace_listings(
        self, category: Optional[str] = None, limit: int = 20
    ) -> dict:
        """List marketplace listings."""
        params: dict = {"limit": limit}
        if category:
            params["category"] = category
        resp = self._client.get(
            "/marketplace/listings",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def purchase_listing(self, listing_id: int) -> dict:
        """Purchase a marketplace listing."""
        resp = self._client.post(
            "/marketplace/purchase",
            headers=self._headers(),
            json={"listingId": listing_id},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Utility ──────────────────────────────────────────────────────

    def close(self) -> None:
        self._client.close()


# Singleton cache
_client_instance: Optional[AiTraderClient] = None


def get_ai_trader_client() -> AiTraderClient:
    """Get or create the global AiTraderClient singleton."""
    global _client_instance
    if _client_instance is None:
        config = AiTraderConfig()
        creds = load_credentials()
        if creds.get("token"):
            config.token = creds["token"]
            config.agent_id = creds.get("agent_id", 0)
            config.name = creds.get("name", "CryptoBot-BR")
            config.email = creds.get("email", "")
            config.enabled = True
        _client_instance = AiTraderClient(config)
    return _client_instance
