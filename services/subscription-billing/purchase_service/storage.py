import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.getenv("PURCHASE_DB_PATH", "purchase_data.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firebase_uid TEXT,
        session_id TEXT,
        tier TEXT,
        expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        code TEXT PRIMARY KEY,
        tier TEXT,
        expires_at TEXT,
        redeemed INTEGER DEFAULT 0
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS one_time_codes (
        code TEXT PRIMARY KEY,
        expires_at TEXT,
        redeemed INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

init_db()

def grant_access(firebase_uid, tier, expires_at):
    conn = get_conn()
    conn.execute(
        "INSERT INTO purchases (firebase_uid, tier, expires_at) VALUES (?, ?, ?)",
        (firebase_uid, tier, expires_at)
    )
    conn.commit()
    conn.close()

def redeem_coupon(firebase_uid, coupon_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT tier, expires_at, redeemed FROM coupons WHERE code = ?", (coupon_code,))
    row = c.fetchone()
    if not row or row["redeemed"]:
        conn.close()
        return False, None, None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.close()
        return False, None, None
    # Mark coupon as redeemed
    c.execute("UPDATE coupons SET redeemed = 1 WHERE code = ?", (coupon_code,))
    conn.commit()
    conn.close()
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    grant_access(firebase_uid, row["tier"], expires_at)
    return True, row["tier"], expires_at

def redeem_one_time_code(session_id, one_time_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT expires_at, redeemed FROM one_time_codes WHERE code = ?", (one_time_code,))
    row = c.fetchone()
    if not row or row["redeemed"]:
        conn.close()
        return False, None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.close()
        return False, None
    # Mark code as redeemed
    c.execute("UPDATE one_time_codes SET redeemed = 1 WHERE code = ?", (one_time_code,))
    conn.execute(
        "INSERT INTO purchases (session_id, expires_at) VALUES (?, ?)",
        (session_id, row["expires_at"])
    )
    conn.commit()
    conn.close()
    return True, row["expires_at"]

def check_access(firebase_uid=None, session_id=None):
    conn = get_conn()
    c = conn.cursor()
    if firebase_uid:
        c.execute(
            "SELECT tier, expires_at FROM purchases WHERE firebase_uid = ? ORDER BY expires_at DESC LIMIT 1",
            (firebase_uid,)
        )
    elif session_id:
        c.execute(
            "SELECT tier, expires_at FROM purchases WHERE session_id = ? ORDER BY expires_at DESC LIMIT 1",
            (session_id,)
        )
    else:
        conn.close()
        return False, None, None
    row = c.fetchone()
    conn.close()
    if not row:
        return False, None, None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        return False, None, None
    return True, row["tier"], row["expires_at"]
