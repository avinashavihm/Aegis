from fastapi import APIRouter, HTTPException, status, Depends, Body
from src.database import get_db_connection
from src.dependencies import get_current_user, get_current_user_id
from uuid import UUID

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(current_user_id: UUID = Depends(get_current_user_id)):
    """List all users (RLS policies will automatically filter based on permissions)."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, full_name, created_at FROM users"
            )
            users = cur.fetchall()
    
    return [dict(user) for user in users]

@router.get("/{user_identifier}")
async def get_user(
    user_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get user by ID or username."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try to parse as UUID first
            try:
                UUID(user_identifier)
                # It's a valid UUID, search by ID
                cur.execute(
                    "SELECT id, username, email, full_name, created_at FROM users WHERE id = %s",
                    (user_identifier,)
                )
            except ValueError:
                # Not a UUID, search by username
                cur.execute(
                    "SELECT id, username, email, full_name, created_at FROM users WHERE username = %s",
                    (user_identifier,)
                )
            
            user_data = cur.fetchone()
            
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return dict(user_data)


@router.put("/{user_id}")
async def update_user(
    user_id: UUID,
    user_update: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update user details (only self)."""
    # Check if user is updating their own profile
    if current_user["id"] != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    update_fields = []
    values = []
    
    email = user_update.get("email")
    full_name = user_update.get("full_name")
    password = user_update.get("password")
    
    if email:
        update_fields.append("email = %s")
        values.append(email)
    if full_name is not None:
        update_fields.append("full_name = %s")
        values.append(full_name)
    if password:
        from src.auth import hash_password
        update_fields.append("password_hash = %s")
        values.append(hash_password(password))
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    values.append(str(user_id))
    
    with get_db_connection(str(current_user["id"])) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE users SET {', '.join(update_fields)} 
                   WHERE id = %s 
                   RETURNING id, username, email, full_name, created_at""",
                values
            )
            updated_user = cur.fetchone()
    
    return dict(updated_user)
