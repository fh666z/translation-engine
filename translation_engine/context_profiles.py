"""Context profile models and storage abstractions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


@dataclass
class ContextProfile:
    """A reusable set of websites used to build a context index."""

    id: str
    websites: list[dict]
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ContextProfileStore(Protocol):
    """Storage interface for reusable context website profiles."""

    def save(self, profile: ContextProfile) -> ContextProfile: ...

    def get(self, profile_id: str) -> ContextProfile | None: ...

    def create(self, websites: list[dict]) -> ContextProfile: ...


class InMemoryContextProfileStore:
    """Simple process-local store for context profiles."""

    def __init__(self) -> None:
        self._profiles: dict[str, ContextProfile] = {}

    def save(self, profile: ContextProfile) -> ContextProfile:
        profile.updated_at = datetime.now(timezone.utc)
        self._profiles[profile.id] = profile
        return profile

    def get(self, profile_id: str) -> ContextProfile | None:
        return self._profiles.get(profile_id)

    def create(self, websites: list[dict]) -> ContextProfile:
        profile = ContextProfile(id=str(uuid4()), websites=websites)
        return self.save(profile)

