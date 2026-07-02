"""Central configuration for the ingestion layer."""
from __future__ import annotations

import os
from pathlib import Path

# --- Tracked universe -------------------------------------------------------
# CoinGecko coin ids. Keep this list small enough to stay well inside the
# free-tier rate limit (1 API call per coin per run).
COINS: list[str] = [
    "bitcoin",
    "ethereum",
    "solana",
    "ripple",
    "cardano",
    "dogecoin",
    "polkadot",
    "chainlink",
    "litecoin",
    "avalanche-2",
]

VS_CURRENCY = "usd"

# --- Incremental-load settings ----------------------------------------------
# First run backfills this many days of hourly data. CoinGecko returns hourly
# granularity for ranges up to 90 days on the free tier.
BACKFILL_DAYS = 90
# Never request a window larger than this (keeps hourly granularity).
MAX_WINDOW_DAYS = 90

# --- Paths --------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_PRICES_DIR = REPO_ROOT / "data" / "raw" / "prices"
RAW_COINS_DIR = REPO_ROOT / "data" / "raw" / "coins"
STATE_PATH = REPO_ROOT / "data" / "state" / "ingestion_state.json"
WAREHOUSE_PATH = REPO_ROOT / "data" / "warehouse" / "crypto.duckdb"
MARTS_EXPORT_DIR = REPO_ROOT / "data" / "marts"

# --- API ----------------------------------------------------------------------
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
# Optional. A free Demo key (https://www.coingecko.com/en/api) raises limits
# to 100 calls/min. Without a key the public limit is lower but sufficient.
API_KEY = os.getenv("COINGECKO_API_KEY", "")
# Seconds to sleep between API calls (polite pacing for keyless use).
REQUEST_PACING_SECONDS = 3.0 if not API_KEY else 0.6
