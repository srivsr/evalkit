"""EvalKit SQLite persistence — from EVALKIT_MASTER_SPEC_v2.md Section 10."""
import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evaluations (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    reference_answer TEXT,
    config_json TEXT,
    request_json TEXT,
    result_json TEXT NOT NULL,
    verdict TEXT NOT NULL,
    root_cause_code TEXT,
    is_baseline INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES evaluations(run_id),
    context_id TEXT NOT NULL,
    text TEXT NOT NULL,
    source TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS regression_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id),
    run_id TEXT NOT NULL,
    baseline_run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    baseline_value REAL,
    current_value REAL,
    delta_pct REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    name TEXT,
    tier TEXT NOT NULL DEFAULT 'free',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    tier TEXT NOT NULL,
    payment_provider TEXT NOT NULL,
    payment_id TEXT,
    amount_usd REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'active',
    starts_at TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    provider TEXT NOT NULL,
    provider_order_id TEXT,
    provider_payment_id TEXT,
    tier TEXT NOT NULL,
    amount_usd REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'pending',
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evaluations_project ON evaluations(project_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_verdict ON evaluations(verdict);
CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);
CREATE INDEX IF NOT EXISTS idx_contexts_run ON contexts(run_id);
CREATE INDEX IF NOT EXISTS idx_regressions_project ON regression_events(project_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_order ON payment_transactions(provider_order_id);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    prefix TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at TEXT,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

CREATE TABLE IF NOT EXISTS judge_calibration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    judge_model TEXT NOT NULL,
    faithfulness REAL,
    answer_relevance REAL,
    agreement_pct REAL,
    judge_count INTEGER NOT NULL,
    escalated INTEGER NOT NULL DEFAULT 0,
    confidence_threshold REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_judge_calibration_project ON judge_calibration(project_id);
CREATE INDEX IF NOT EXISTS idx_judge_calibration_model ON judge_calibration(judge_model);
"""


async def init_db(db: aiosqlite.Connection) -> None:
    await db.executescript(SCHEMA_SQL)
    await db.commit()
    # Migration: add user_id column to projects if not exists
    try:
        await db.execute("ALTER TABLE projects ADD COLUMN user_id TEXT")
        await db.commit()
    except Exception as e:
        if "duplicate column" in str(e).lower():
            pass
        else:
            raise


async def get_connection(db_path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await init_db(db)
    return db


# --- Projects ---

async def create_project(db: aiosqlite.Connection, project_id: str, name: str) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
        (project_id, name, created_at),
    )
    await db.commit()
    return {"id": project_id, "name": name, "created_at": created_at}


async def get_project(db: aiosqlite.Connection, project_id: str) -> Optional[dict]:
    cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def list_projects(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# --- Evaluations ---

async def store_evaluation(
    db: aiosqlite.Connection,
    run_id: str,
    project_id: str,
    query: str,
    response: str,
    result_json: str,
    verdict: str,
    root_cause_code: str,
    reference_answer: Optional[str] = None,
    config_json: Optional[str] = None,
    request_json: Optional[str] = None,
    contexts: Optional[list[dict]] = None,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO evaluations
           (run_id, project_id, created_at, query, response, reference_answer,
            config_json, request_json, result_json, verdict, root_cause_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, project_id, created_at, query, response, reference_answer,
         config_json, request_json, result_json, verdict, root_cause_code),
    )
    if contexts:
        for ctx in contexts:
            await db.execute(
                """INSERT INTO contexts (run_id, context_id, text, source, metadata_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, ctx["id"], ctx["text"], ctx.get("source"),
                 json.dumps(ctx.get("metadata")) if ctx.get("metadata") else None),
            )
    await db.commit()


async def get_evaluation(db: aiosqlite.Connection, run_id: str) -> Optional[dict]:
    cursor = await db.execute("SELECT * FROM evaluations WHERE run_id = ?", (run_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def list_evaluations(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM evaluations WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_contexts_for_run(db: aiosqlite.Connection, run_id: str) -> list[dict]:
    cursor = await db.execute("SELECT * FROM contexts WHERE run_id = ?", (run_id,))
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# --- Baseline + Regression ---

async def mark_as_baseline(db: aiosqlite.Connection, run_id: str) -> bool:
    cursor = await db.execute("SELECT run_id, project_id FROM evaluations WHERE run_id = ?", (run_id,))
    row = await cursor.fetchone()
    if row is None:
        return False
    project_id = row["project_id"] if isinstance(row, dict) else row[1]
    await db.execute("UPDATE evaluations SET is_baseline = 0 WHERE project_id = ?", (project_id,))
    await db.execute("UPDATE evaluations SET is_baseline = 1 WHERE run_id = ?", (run_id,))
    await db.commit()
    return True


async def get_baseline(db: aiosqlite.Connection, project_id: str) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM evaluations WHERE project_id = ? AND is_baseline = 1 ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def store_regression_event(
    db: aiosqlite.Connection,
    project_id: str,
    run_id: str,
    baseline_run_id: str,
    metric_name: str,
    baseline_value: float,
    current_value: float,
    delta_pct: float,
) -> None:
    await db.execute(
        """INSERT INTO regression_events
           (project_id, run_id, baseline_run_id, metric_name, baseline_value, current_value, delta_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (project_id, run_id, baseline_run_id, metric_name, baseline_value, current_value, delta_pct),
    )
    await db.commit()


async def list_regressions(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM regression_events WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# --- Users ---

async def ensure_user(db: aiosqlite.Connection, user_id: str, email: str = None, name: str = None) -> dict:
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    now = datetime.now(timezone.utc).isoformat()
    display_name = name or (email.split("@")[0] if email else "User")
    await db.execute(
        "INSERT INTO users (id, email, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, email, display_name, now, now),
    )
    await db.commit()
    return {"id": user_id, "email": email, "name": display_name, "tier": "free",
            "created_at": now, "updated_at": now}


async def get_user(db: aiosqlite.Connection, user_id: str) -> Optional[dict]:
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_user_tier(db: aiosqlite.Connection, user_id: str, tier: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE users SET tier = ?, updated_at = ? WHERE id = ?",
        (tier, now, user_id),
    )
    await db.commit()


# --- Subscriptions ---

async def create_subscription(db: aiosqlite.Connection, user_id: str, tier: str, provider: str,
                               payment_id: str, amount: float, currency: str = "USD",
                               duration_days: int = 30) -> dict:
    now = datetime.now(timezone.utc)
    starts_at = now.isoformat()
    expires_at = (now + timedelta(days=duration_days)).isoformat()
    await db.execute(
        """INSERT INTO subscriptions
           (user_id, tier, payment_provider, payment_id, amount_usd, currency, status, starts_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (user_id, tier, provider, payment_id, amount, currency, starts_at, expires_at),
    )
    await update_user_tier(db, user_id, tier)
    await db.commit()
    return {"user_id": user_id, "tier": tier, "starts_at": starts_at, "expires_at": expires_at}


async def get_active_subscription(db: aiosqlite.Connection, user_id: str) -> Optional[dict]:
    cursor = await db.execute(
        """SELECT * FROM subscriptions
           WHERE user_id = ? AND status = 'active'
           AND (expires_at IS NULL OR expires_at > datetime('now'))
           ORDER BY created_at DESC LIMIT 1""",
        (user_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# --- Payment Transactions ---

async def create_payment_transaction(db: aiosqlite.Connection, user_id: str, provider: str,
                                      order_id: str, tier: str, amount: float,
                                      currency: str = "USD") -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, provider, provider_order_id, tier, amount_usd, currency, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (user_id, provider, order_id, tier, amount, currency, now, now),
    )
    await db.commit()
    return cursor.lastrowid


async def update_payment_status(db: aiosqlite.Connection, provider_order_id: str, status: str,
                                 provider_payment_id: str = None,
                                 metadata: str = None) -> Optional[dict]:
    now = datetime.now(timezone.utc).isoformat()
    if provider_payment_id:
        await db.execute(
            """UPDATE payment_transactions
               SET status = ?, provider_payment_id = ?, metadata_json = ?, updated_at = ?
               WHERE provider_order_id = ?""",
            (status, provider_payment_id, metadata, now, provider_order_id),
        )
    else:
        await db.execute(
            """UPDATE payment_transactions SET status = ?, metadata_json = ?, updated_at = ?
               WHERE provider_order_id = ?""",
            (status, metadata, now, provider_order_id),
        )
    await db.commit()
    cursor = await db.execute(
        "SELECT * FROM payment_transactions WHERE provider_order_id = ?",
        (provider_order_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_payment_by_order_id(db: aiosqlite.Connection, provider_order_id: str) -> Optional[dict]:
    cursor = await db.execute(
        "SELECT * FROM payment_transactions WHERE provider_order_id = ?",
        (provider_order_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# --- API Keys ---

def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def create_api_key(db: aiosqlite.Connection, user_id: str, name: str) -> dict:
    key_id = secrets.token_hex(8)
    raw_key = "ek_" + secrets.token_hex(32)
    prefix = raw_key[:11] + "..."
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO api_keys (id, user_id, key_hash, name, prefix, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (key_id, user_id, key_hash, name, prefix, now),
    )
    await db.commit()
    return {"id": key_id, "key": raw_key, "name": name, "prefix": prefix, "created_at": now}


async def list_api_keys(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT id, name, prefix, created_at, last_used_at, revoked_at FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def revoke_api_key(db: aiosqlite.Connection, key_id: str, user_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
        (now, key_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def validate_api_key(db: aiosqlite.Connection, raw_key: str) -> Optional[str]:
    key_hash = _hash_key(raw_key)
    cursor = await db.execute(
        "SELECT id, user_id FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL",
        (key_hash,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    row_dict = dict(row)
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row_dict["id"]))
    await db.commit()
    return row_dict["user_id"]


# --- Judge Calibration ---

async def store_judge_calibration(
    db: aiosqlite.Connection,
    run_id: str,
    project_id: str,
    judge_model: str,
    faithfulness: Optional[float],
    answer_relevance: Optional[float],
    agreement_pct: Optional[float],
    judge_count: int,
    escalated: bool = False,
    confidence_threshold: Optional[float] = None,
) -> None:
    await db.execute(
        """INSERT INTO judge_calibration
           (run_id, project_id, judge_model, faithfulness, answer_relevance,
            agreement_pct, judge_count, escalated, confidence_threshold)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, project_id, judge_model, faithfulness, answer_relevance,
         agreement_pct, judge_count, int(escalated), confidence_threshold),
    )
    await db.commit()


async def get_judge_calibration_stats(
    db: aiosqlite.Connection, project_id: str, judge_model: Optional[str] = None,
) -> dict:
    base_query = "SELECT * FROM judge_calibration WHERE project_id = ?"
    params: list = [project_id]
    if judge_model:
        base_query += " AND judge_model = ?"
        params.append(judge_model)

    cursor = await db.execute(base_query + " ORDER BY created_at DESC", params)
    rows = await cursor.fetchall()
    if not rows:
        return {"total_evals": 0, "avg_agreement": None, "escalation_rate": 0.0, "per_model": {}}

    records = [dict(r) for r in rows]
    total = len(records)
    escalated_count = sum(1 for r in records if r["escalated"])
    agreements = [r["agreement_pct"] for r in records if r["agreement_pct"] is not None]
    avg_agreement = sum(agreements) / len(agreements) if agreements else None

    per_model: dict[str, dict] = {}
    for r in records:
        m = r["judge_model"]
        if m not in per_model:
            per_model[m] = {"count": 0, "avg_faithfulness": 0.0, "avg_relevance": 0.0}
        per_model[m]["count"] += 1
        per_model[m]["avg_faithfulness"] += (r["faithfulness"] or 0.0)
        per_model[m]["avg_relevance"] += (r["answer_relevance"] or 0.0)

    for m, stats in per_model.items():
        c = stats["count"]
        stats["avg_faithfulness"] = round(stats["avg_faithfulness"] / c, 4) if c else 0.0
        stats["avg_relevance"] = round(stats["avg_relevance"] / c, 4) if c else 0.0

    return {
        "total_evals": total,
        "avg_agreement": round(avg_agreement, 1) if avg_agreement is not None else None,
        "escalation_rate": round(escalated_count / total, 4) if total else 0.0,
        "per_model": per_model,
    }
