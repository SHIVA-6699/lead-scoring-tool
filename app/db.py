import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "leads.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    domain TEXT PRIMARY KEY,
    company_name TEXT,
    score INTEGER NOT NULL,
    bucket TEXT NOT NULL,
    reasons TEXT NOT NULL,
    signals TEXT NOT NULL,
    reachable INTEGER NOT NULL,
    scraped_at TEXT NOT NULL
);
"""


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA)


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_cached_lead(domain: str, max_age_hours: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM leads WHERE domain = ?", (domain,)).fetchone()
    if row is None:
        return None

    scraped_at = datetime.fromisoformat(row["scraped_at"])
    age_hours = (datetime.now(UTC) - scraped_at).total_seconds() / 3600
    if age_hours > max_age_hours:
        return None

    return _row_to_dict(row)


def save_lead(result: dict) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO leads (domain, company_name, score, bucket, reasons, signals, reachable, scraped_at)
            VALUES (:domain, :company_name, :score, :bucket, :reasons, :signals, :reachable, :scraped_at)
            ON CONFLICT(domain) DO UPDATE SET
                company_name = excluded.company_name,
                score = excluded.score,
                bucket = excluded.bucket,
                reasons = excluded.reasons,
                signals = excluded.signals,
                reachable = excluded.reachable,
                scraped_at = excluded.scraped_at
            """,
            {
                "domain": result["domain"],
                "company_name": result["company_name"],
                "score": result["score"],
                "bucket": result["bucket"],
                "reasons": json.dumps(result["reasons"]),
                "signals": json.dumps(result["signals"]),
                "reachable": int(result["reachable"]),
                "scraped_at": result["scraped_at"],
            },
        )


def list_leads() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY score DESC").fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "domain": row["domain"],
        "company_name": row["company_name"],
        "score": row["score"],
        "bucket": row["bucket"],
        "reasons": json.loads(row["reasons"]),
        "signals": json.loads(row["signals"]),
        "reachable": bool(row["reachable"]),
        "scraped_at": row["scraped_at"],
        "cached": False,
    }
