from fastapi import Depends, HTTPException, status
from src.auth import oauth2_scheme, decode_access_token
from src.database import get_db_connection
from uuid import UUID


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to get the current authenticated user.
    Validates JWT token and retrieves user from database.
    """
    token_data = decode_access_token(token)
    
    if token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    with get_db_connection(str(token_data.user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, full_name, created_at FROM users WHERE id = %s",
                (str(token_data.user_id),)
            )
            user_data = cur.fetchone()
    
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return dict(user_data)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    """
    Dependency to get just the current user ID.
    Useful for database operations that need RLS context.
    """
    token_data = decode_access_token(token)
    
    if token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return token_data.user_id
