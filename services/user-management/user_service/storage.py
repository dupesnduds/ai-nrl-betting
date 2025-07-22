# user_service/storage.py
import sqlite3
from datetime import datetime
from typing import Optional

from .config import USER_DB_PATH
from .models import UserCreate, User

DATABASE_URL = f"sqlite:///{USER_DB_PATH}" # Using file path directly for sqlite3

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(USER_DB_PATH)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def initialize_db():
    """Creates the users table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firebase_uid TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_tier TEXT,
            subscription_status TEXT,
            subscription_start_date TIMESTAMP,
            subscription_end_date TIMESTAMP
        )
    """)
    # Add index for faster lookups by firebase_uid
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_firebase_uid ON users (firebase_uid)")
    
    # If the table already exists, we need to check if the new columns exist and add them if not
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'subscription_tier' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT")
    if 'subscription_status' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT")
    if 'subscription_start_date' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP")
    if 'subscription_end_date' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP")

    # Create user_feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER,
            actual_winner TEXT,
            actual_margin INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, prediction_id) -- Ensure only one feedback entry per user per prediction
        )
    """)
    # Add indexes for feedback table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON user_feedback (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_prediction_id ON user_feedback (prediction_id)")

    conn.commit()
    conn.close()
    print(f"Database initialized/verified at {USER_DB_PATH}")

# Initialize the database on module load
initialize_db()

def get_user_by_firebase_uid(firebase_uid: str) -> Optional[User]:
    """Retrieves a user by their Firebase UID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, firebase_uid, email, created_at, 
               subscription_tier, subscription_status, 
               subscription_start_date, subscription_end_date
        FROM users 
        WHERE firebase_uid = ?
    """, (firebase_uid,))
    user_row = cursor.fetchone()
    conn.close()
    if user_row:
        return User(**dict(user_row))
    return None

def create_user(user_in: UserCreate) -> User:
    """Creates a new user record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (firebase_uid, email) VALUES (?, ?)",
            (user_in.firebase_uid, user_in.email)
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        # Handle case where user might already exist due to race condition (rare)
        existing_user = get_user_by_firebase_uid(user_in.firebase_uid)
        if existing_user:
            return existing_user
        else:
            # Re-raise if it's a different integrity error or user still not found
            raise
    finally:
        if conn:
            conn.close()

    # Fetch the newly created user to return the full User model
    new_user = get_user_by_id(user_id)
    if not new_user:
         # This should ideally not happen if insert was successful
        raise Exception("Failed to retrieve newly created user")
    return new_user


def get_user_by_id(user_id: int) -> Optional[User]:
    """Retrieves a user by their internal ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, firebase_uid, email, created_at, 
               subscription_tier, subscription_status, 
               subscription_start_date, subscription_end_date
        FROM users 
        WHERE id = ?
    """, (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    if user_row:
        return User(**dict(user_row))
    return None

# --- Feedback Storage Functions ---

def save_prediction_rating(user_id: int, prediction_id: str, rating: int):
    """Saves or updates a user's rating for a specific prediction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    try:
        cursor.execute("""
            INSERT INTO user_feedback (user_id, prediction_id, rating, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, prediction_id) DO UPDATE SET
                rating = excluded.rating,
                updated_at = excluded.updated_at
        """, (user_id, prediction_id, rating, now, now))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error saving rating: {e}")
        conn.rollback()
        raise # Re-raise the exception after logging/rolling back
    finally:
        conn.close()

def save_actual_result(user_id: int, prediction_id: str, actual_winner: str, actual_margin: int):
    """Saves or updates the actual result submitted by a user for a specific prediction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow()
    try:
        cursor.execute("""
            INSERT INTO user_feedback (user_id, prediction_id, actual_winner, actual_margin, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, prediction_id) DO UPDATE SET
                actual_winner = excluded.actual_winner,
                actual_margin = excluded.actual_margin,
                updated_at = excluded.updated_at
        """, (user_id, prediction_id, actual_winner, actual_margin, now, now))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error saving actual result: {e}")
        conn.rollback()
        raise # Re-raise the exception after logging/rolling back
    finally:
        conn.close()


def update_user_subscription(
    firebase_uid: str,
    subscription_tier: Optional[str] = None,
    subscription_status: Optional[str] = None,
    subscription_start_date: Optional[datetime] = None,
    subscription_end_date: Optional[datetime] = None
) -> Optional[User]:
    """
    Updates a user's subscription details based on their Firebase UID.
    Returns the updated User object, or None if user not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build dynamic update query
    fields = []
    values = []

    if subscription_tier is not None:
        fields.append("subscription_tier = ?")
        values.append(subscription_tier)
    if subscription_status is not None:
        fields.append("subscription_status = ?")
        values.append(subscription_status)
    if subscription_start_date is not None:
        fields.append("subscription_start_date = ?")
        values.append(subscription_start_date)
    if subscription_end_date is not None:
        fields.append("subscription_end_date = ?")
        values.append(subscription_end_date)

    if not fields:
        conn.close()
        return get_user_by_firebase_uid(firebase_uid)  # No update, return current user

    values.append(firebase_uid)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE firebase_uid = ?"

    cursor.execute(sql, tuple(values))
    conn.commit()
    conn.close()

    return get_user_by_firebase_uid(firebase_uid)

# Add other CRUD operations as needed (e.g., update_user, delete_user)
