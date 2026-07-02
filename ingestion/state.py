"""High-watermark state tracking for incremental loads.

The state file records, per coin, the unix timestamp of the newest record
successfully landed. Each run only requests data *after* that watermark,
which is what makes the pipeline incremental instead of full-refresh.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_state(path: Path) -> dict[str, int]:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_state(path: Path, state: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def get_watermark(state: dict[str, int], coin_id: str) -> int | None:
    """Return the last-loaded unix timestamp for a coin, or None if never loaded."""
    return state.get(coin_id)


def set_watermark(state: dict[str, int], coin_id: str, ts: int) -> None:
    """Advance the watermark. Never moves backwards."""
    current = state.get(coin_id, 0)
    state[coin_id] = max(current, ts)
