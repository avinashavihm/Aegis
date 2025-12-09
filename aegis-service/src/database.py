import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from src.config import settings


@contextmanager
def get_db_connection(user_id: str = None):
    """
    Database connection with RLS context.
    If user_id is provided, sets app.current_user_id for RLS policies.
    """
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        cursor_factory=RealDictCursor
    )
    
    try:
        # Set RLS context if user is authenticated
        if user_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT set_config('app.current_user_id', %s, false)",
                    (str(user_id),)
                )
        
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
