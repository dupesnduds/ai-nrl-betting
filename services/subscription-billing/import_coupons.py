import sqlite3
import os
from datetime import datetime

from purchase_service import storage

DB_PATH = os.getenv("PURCHASE_DB_PATH", "purchase_data.db")
COUPON_FILE = os.path.join(os.path.dirname(__file__), "..", ".coupon")

def import_coupons():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with open(COUPON_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                print(f"Skipping invalid line: {line}")
                continue
            code, tier, expires_at = parts
            # Check if coupon already exists
            c.execute("SELECT code FROM coupons WHERE code = ?", (code,))
            if c.fetchone():
                print(f"Coupon {code} already exists, skipping")
                continue
            # Insert new coupon
            try:
                datetime.fromisoformat(expires_at)  # Validate date
                c.execute(
                    "INSERT INTO coupons (code, tier, expires_at, redeemed) VALUES (?, ?, ?, 0)",
                    (code, tier, expires_at)
                )
                print(f"Imported coupon: {code}")
            except Exception as e:
                print(f"Error importing {code}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    storage.init_db()
    import_coupons()
