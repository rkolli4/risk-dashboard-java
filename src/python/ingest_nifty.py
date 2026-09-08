#!/usr/bin/env python3
"""Fetch a Nifty snapshot, persist it locally, and optionally write to Oracle."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SNAPSHOT_PATH = DATA_DIR / "market_snapshot.json"
DB_PATH = DATA_DIR / "prism.db"


def number(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric, got {value!r}") from exc


def fetch_quote(symbol: str = "^NSEI") -> tuple[float, float]:
    query = urllib.parse.urlencode({"symbols": symbol})
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "PRISM-prototype/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload["quoteResponse"]["result"][0]
    return float(result["regularMarketPrice"]), float(result.get("regularMarketChangePercent", 0.0))


def persist_sqlite(snapshot: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS market_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change_percent REAL NOT NULL,
                captured_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS risk_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                state TEXT NOT NULL,
                exposure REAL NOT NULL,
                utilization REAL NOT NULL,
                penalty REAL NOT NULL,
                message TEXT NOT NULL
            );
        """)
        connection.execute(
            "INSERT INTO market_snapshot(symbol, price, change_percent, captured_at) VALUES (?, ?, ?, ?)",
            (snapshot["symbol"], snapshot["price"], snapshot["change_percent"], snapshot["captured_at"]),
        )


def persist_oracle(snapshot: dict) -> None:
    dsn, user, password = (os.getenv(key) for key in ("ORACLE_DSN", "ORACLE_USER", "ORACLE_PASSWORD"))
    if not all((dsn, user, password)):
        return
    try:
        import oracledb  # type: ignore
        with oracledb.connect(user=user, password=password, dsn=dsn) as connection:
            connection.execute(
                "INSERT INTO market_snapshot(symbol, price, change_percent, captured_at) VALUES (:1, :2, :3, :4)",
                (snapshot["symbol"], snapshot["price"], snapshot["change_percent"], snapshot["captured_at"]),
            )
            connection.commit()
    except ImportError:
        print("Oracle credentials supplied, but python-oracledb is not installed; continuing with SQLite.", file=sys.stderr)
    except Exception as exc:
        print(f"Oracle write skipped: {exc}", file=sys.stderr)


def main() -> int:
    try:
        price, change_percent = fetch_quote()
        source = "yahoo"
    except Exception as exc:
        # A deterministic fallback keeps local demos usable when Yahoo is unavailable.
        print(f"Yahoo quote unavailable ({exc}); using a demo quote.", file=sys.stderr)
        price, change_percent, source = 22500.0, 0.0, "demo-fallback"

    snapshot = {
        "symbol": "^NSEI",
        "price": price,
        "change_percent": change_percent,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "total_deposit": number("TOTAL_DEPOSIT", 1_000_000),
        "min_liquid_networth": number("MIN_LIQUID_NETWORTH", 250_000),
        "initial_margin": number("INITIAL_MARGIN", 100_000),
        "extreme_loss_margin": number("EXTREME_LOSS_MARGIN", 50_000),
        "tm_limit": number("TM_LIMIT", 500_000),
        "position_qty": number("POSITION_QTY", 10),
        "position_limit": number("POSITION_LIMIT", 1_000_000),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    persist_sqlite(snapshot)
    persist_oracle(snapshot)
    print(f"Snapshot written: {SNAPSHOT_PATH} ({source}, {price:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
