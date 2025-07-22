# user_service/config.py
import os
from pathlib import Path

# Base directory of the user-service project
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Database Configuration ---
# Using a dedicated SQLite DB within the user-service project
USER_DB_NAME = "user_data.db"
USER_DB_PATH = BASE_DIR / "data" / USER_DB_NAME

# Ensure the data directory exists
USER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Firebase Configuration ---
# Path to the Firebase Admin SDK service account key JSON file
# IMPORTANT: This path needs to be set correctly, either directly here
# or preferably via an environment variable for security.
# Example using an environment variable:
# FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "/path/to/your/serviceAccountKey.json")
# For now, using a placeholder path. Update this before running.
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT_KEY_PATH",
    str(BASE_DIR / "config" / "firebase_service_account.json") # Placeholder location
)

# Ensure the config directory exists if using the placeholder path
if not os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH"):
    (BASE_DIR / "config").mkdir(exist_ok=True)

# --- API Configuration ---
API_PORT = 8007 # Default port for the User Service API
