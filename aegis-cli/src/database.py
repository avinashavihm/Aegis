import psycopg2
import os
from src.config import get_auth_token
from typing import Optional

# Default to localhost/docker settings
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agentic_ops")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password123")

def get_db_connection():
    """
    Establishes a connection to the database and sets the RLS context
    if a user is logged in.
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    # Set RLS context if user is authenticated
    user_id = get_auth_token()
    if user_id:
        with conn.cursor() as cur:
            # We use set_config to set the session variable for RLS policies
            # 'is_local' is true, meaning it applies to the transaction/session
            cur.execute("SELECT set_config('app.current_user_id', %s, false)", (user_id,))
    
    return conn
