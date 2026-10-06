"""Vertical script packs — the VoiceDesk differentiator.

Each pack is a ready-made receptionist persona (greeting + system prompt +
FAQ knowledge + booking rules) tuned for a specific trade, so buyers get a
working AI receptionist in minutes instead of a blank prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalPack:
    key: str
    name: str
    greeting: str
    system_prompt: str
    business_hours: str = "09:00-17:00"
    services: list[str] = field(default_factory=list)
    faqs: dict[str, str] = field(default_factory=dict)


_PACKS: dict[str, VerticalPack] = {}


def register(pack: VerticalPack) -> VerticalPack:
    _PACKS[pack.key] = pack
    return pack


def get_pack(key: str) -> VerticalPack | None:
    return _PACKS.get(key)


def all_packs() -> list[VerticalPack]:
    return list(_PACKS.values())


def pack_keys() -> list[str]:
    return sorted(_PACKS)
