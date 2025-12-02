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
            
            # Fetch teams and roles for each user
            result = []
            for user in users:
                user_dict = dict(user)
                
                # Get teams and roles (through team membership)
                cur.execute(
                    """SELECT t.id as team_id, t.name as team_name, t.slug as team_slug, 
                              r.name as role_name
                       FROM team_members tm
                       JOIN teams t ON tm.team_id = t.id
                       JOIN roles r ON tm.role_id = r.id
                       WHERE tm.user_id = %s
                       ORDER BY t.name""",
                    (user_dict['id'],)
                )
                teams_data = cur.fetchall()
                user_dict['teams'] = [dict(t) for t in teams_data]
                
                # Get direct role assignments (not through teams)
                cur.execute(
                    """SELECT r.id, r.name, r.description
                       FROM user_roles ur
                       JOIN roles r ON ur.role_id = r.id
                       WHERE ur.user_id = %s
                       ORDER BY r.name""",
                    (user_dict['id'],)
                )
                direct_roles = cur.fetchall()
                user_dict['roles'] = [dict(r) for r in direct_roles]
                
                result.append(user_dict)
    
    return result

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
            
            # Fetch teams and roles
            cur.execute(
                """
                SELECT t.id, t.name, t.slug, r.name as role_name
                FROM team_members tm
                JOIN teams t ON tm.team_id = t.id
                LEFT JOIN roles r ON tm.role_id = r.id
                WHERE tm.user_id = %s
                """,
                (user_data['id'],)
            )
            teams = cur.fetchall()
            
            result = dict(user_data)
            result['teams'] = [dict(t) for t in teams]
            return result


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


@router.post("/{user_identifier}/roles/{role_identifier}")
async def assign_role_to_user(
    user_identifier: str,
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Assign a role directly to a user (not through team membership)."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve user ID
            try:
                UUID(user_identifier)
                user_id = user_identifier
            except ValueError:
                cur.execute("SELECT id FROM users WHERE username = %s", (user_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="User not found")
                user_id = result["id"]
            
            # Resolve role ID
            try:
                UUID(role_identifier)
                role_id = role_identifier
            except ValueError:
                cur.execute("SELECT id FROM roles WHERE name = %s", (role_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Role not found")
                role_id = result["id"]
            
            # Check if already assigned
            cur.execute(
                "SELECT 1 FROM user_roles WHERE user_id = %s AND role_id = %s",
                (user_id, role_id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Role already assigned to this user")
            
            # Assign role
            try:
                cur.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                    (user_id, role_id)
                )
                conn.commit()
                return {"message": "Role assigned successfully"}
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{user_identifier}/roles/{role_identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_identifier: str,
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Remove a directly assigned role from a user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve user ID
            try:
                UUID(user_identifier)
                user_id = user_identifier
            except ValueError:
                cur.execute("SELECT id FROM users WHERE username = %s", (user_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="User not found")
                user_id = result["id"]
            
            # Resolve role ID
            try:
                UUID(role_identifier)
                role_id = role_identifier
            except ValueError:
                cur.execute("SELECT id FROM roles WHERE name = %s", (role_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Role not found")
                role_id = result["id"]
            
            # Remove role assignment
            try:
                cur.execute(
                    "DELETE FROM user_roles WHERE user_id = %s AND role_id = %s RETURNING user_id",
                    (user_id, role_id)
                )
                deleted = cur.fetchone()
                conn.commit()
                
                if not deleted:
                    raise HTTPException(status_code=404, detail="Role assignment not found")
            except HTTPException:
                raise
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(e))
