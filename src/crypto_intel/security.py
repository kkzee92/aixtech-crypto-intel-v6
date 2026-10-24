"""Cyber and data-security controls for the information system.

This is a research control plane, not a certified security product.
Version 0.6 expands secret patterns (Telegram, Discord, more formats),
adds a zero-trust action policy engine, and strengthens anomaly detection
with sequence awareness and sealed lineage.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

# Minimal stubs
from enum import Enum

class ExecutionMode(Enum):
    PAPER = "paper"
    LIVE = "live"
    HALTED = "halted"

@dataclass
class AuditEvent:
    sequence: int
    action: str
    detail: str
    previous_hash: str
    digest: str

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token|private[_-]?key|mnemonic|seed[_-]?phrase|passphrase)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b[0-9a-fA-F]{64}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"),
    re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{87,88}\b"),
    re.compile(r"\b(?:abandon|ability|able|about|above|absent|absorb|abstract|absurd|abuse)\b(?:\s+\w+){11,23}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\b(?:ya29\.|1//)[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),  # Telegram bot token approx
    re.compile(r"\b(?:discord|bot)[_-]?token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
)

WALLET_PATTERN = re.compile(r"\b0x[a-fA-F0-9]{40}\b")

@dataclass(frozen=True)
class DataClassification:
    field: str
    level: str
    retention: str

CLASSIFICATION = (
    DataClassification("symbol", "public", "research retention"),
    DataClassification("ohlcv", "public-market", "research retention"),
    DataClassification("exchange_api_key", "secret", "never stored"),
    DataClassification("wallet_address", "sensitive-identifier", "do not fixture"),
    DataClassification("account_email", "personal", "do not collect"),
    DataClassification("private_key", "secret", "never stored, never logged"),
    DataClassification("funding_rate", "public-market", "research retention"),
    DataClassification("seed_phrase", "secret", "never stored"),
    DataClassification("session_token", "secret", "never stored"),
    DataClassification("hardware_seed", "secret", "never stored"),
    DataClassification("jwt_token", "secret", "never stored"),
    DataClassification("github_token", "secret", "never stored"),
    DataClassification("telegram_token", "secret", "never stored"),
    DataClassification("discord_token", "secret", "never stored"),
)

ALLOWED_ACTIONS = {"scan", "brief", "posture", "demo", "audit", "attest"}  # zero-trust policy

def redact(text: str) -> str:
    cleaned = text
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return WALLET_PATTERN.sub("[WALLET]", cleaned)

def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS) or bool(WALLET_PATTERN.search(text))

def assert_paper_only(mode: ExecutionMode) -> None:
    if mode is not ExecutionMode.PAPER:
        raise PermissionError("live execution is disabled; this system is paper-only")

def check_policy(action: str) -> None:
    """Zero-trust action allowlist."""
    if action not in ALLOWED_ACTIONS:
        raise PermissionError(f"action {action} not permitted under zero-trust policy")

def hash_event(previous_hash: str, sequence: int, action: str, detail: str) -> str:
    material = f"{previous_hash}|{sequence}|{action}|{detail}".encode()
    return hashlib.sha256(material).hexdigest()

def integrity_digest(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()

class AuditLog:
    """Append-only hash chain with simulated lineage, rate anomaly, and sequence awareness."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._previous = "GENESIS"
        self._last_action = ""
        self._consecutive = 0
        self._action_times: list[float] = []
        self._recent_actions: list[str] = []

    def append(self, action: str, detail: str, lineage: str = "synthetic-fixture", sealed: bool = False) -> AuditEvent:
        check_policy(action)
        safe_detail = redact(detail)
        if sealed:
            safe_detail = f"sealed:{integrity_digest(safe_detail)}"
        now = datetime.now(timezone.utc).timestamp()
        self._action_times.append(now)
        self._action_times = [t for t in self._action_times if now - t < 60]
        rate = len(self._action_times)
        anomaly = "rate_ok"
        if rate > 20:
            anomaly = "rate_high"
        self._recent_actions.append(action)
        if len(self._recent_actions) > 5:
            self._recent_actions.pop(0)
        if len(set(self._recent_actions)) == 1 and len(self._recent_actions) == 5:
            anomaly += "_seq_repeat"
        if action == self._last_action:
            self._consecutive += 1
        else:
            self._consecutive = 1
            self._last_action = action
        stamped = f"{safe_detail} | ts={datetime.now(timezone.utc).isoformat(timespec='seconds')} | lineage={lineage} | consec={self._consecutive} | rate60s={rate} | anomaly={anomaly}"
        sequence = len(self.events) + 1
        digest = hash_event(self._previous, sequence, action, stamped)
        event = AuditEvent(sequence, action, stamped, self._previous, digest)
        self.events.append(event)
        self._previous = digest
        return event

    def verify(self) -> bool:
        previous = "GENESIS"
        for event in self.events:
            expected = hash_event(previous, event.sequence, event.action, event.detail)
            if event.previous_hash != previous or event.digest != expected:
                return False
            previous = event.digest
        return True
