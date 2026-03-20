"""
Hermes Adapter data models.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal


HermesCapability = Literal["observe", "summarize"]


@dataclass
class HermesConnection:
    """Active connection to Zend gateway with delegated authority."""
    principal_id: str
    capabilities: list[HermesCapability]
    connected_at: str
    expires_at: str


@dataclass
class HermesSummary:
    """A Hermes-generated summary for the event spine."""
    summary_text: str
    generated_at: str
    authority_scope: list[HermesCapability]


@dataclass
class MinerSnapshot:
    """Cached miner status object with freshness timestamp."""
    status: str
    mode: str
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str


@dataclass
class AuthorityToken:
    """Decoded authority token from Zend gateway."""
    principal_id: str
    capabilities: list[HermesCapability]
    issued_at: str
    expires_at: str
    token_id: str
    used: bool = False


def make_summary_text(text: str, scope: list[HermesCapability]) -> HermesSummary:
    """Create a HermesSummary with current timestamp."""
    return HermesSummary(
        summary_text=text,
        generated_at=datetime.now(timezone.utc).isoformat(),
        authority_scope=scope,
    )