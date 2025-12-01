from fastapi import APIRouter, HTTPException, status, Depends, Body
from src.database import get_db_connection
from src.dependencies import get_current_user_id
from uuid import UUID
import json

router = APIRouter(prefix="/roles", tags=["roles"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(
    data: dict = Body(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new role.
    If workspace_id is provided, creates a workspace-specific role.
    Otherwise, creates a global role (requires admin privileges - enforced by RLS/Policy).
    """
    name = data.get("name")
    description = data.get("description")
    workspace_id = data.get("workspace_id")
    policy = data.get("policy")
    
    if not all([name, policy]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and policy are required"
        )
    
    # Enforce slug-like naming: lowercase, alphanumeric, hyphens only
    import re
    if not re.match(r'^[a-z0-9-]+$', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name must contain only lowercase letters, numbers, and hyphens (no spaces)"
        )
    
    # Validate policy is valid JSON
    if isinstance(policy, str):
        try:
            policy = json.loads(policy)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON policy"
            )
            
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check for duplicate name in scope
            if workspace_id:
                cur.execute(
                    "SELECT id FROM roles WHERE name = %s AND workspace_id = %s",
                    (name, str(workspace_id))
                )
            else:
                cur.execute(
                    "SELECT id FROM roles WHERE name = %s AND workspace_id IS NULL",
                    (name,)
                )
                
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role with this name already exists in this scope"
                )
            
            # Create role
            cur.execute(
                """INSERT INTO roles (name, description, workspace_id, policy) 
                   VALUES (%s, %s, %s, %s) 
                   RETURNING id, name, description, workspace_id, policy, created_at""",
                (name, description, str(workspace_id) if workspace_id else None, json.dumps(policy))
            )
            role_data = cur.fetchone()
            
    if not role_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to create role"
        )
        
    return dict(role_data)

@router.get("")
async def list_roles(
    workspace_id: UUID = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List roles.
    If workspace_id is provided, lists global roles + roles for that workspace.
    Otherwise, lists only global roles.
    """
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            if workspace_id:
                cur.execute(
                    """SELECT id, name, description, workspace_id, policy, created_at 
                       FROM roles 
                       WHERE workspace_id IS NULL OR workspace_id = %s
                       ORDER BY workspace_id NULLS FIRST, name""",
                    (str(workspace_id),)
                )
            else:
                cur.execute(
                    """SELECT id, name, description, workspace_id, policy, created_at 
                       FROM roles 
                       WHERE workspace_id IS NULL
                       ORDER BY name"""
                )
            roles = cur.fetchall()
            
    return [dict(role) for role in roles]

@router.get("/{role_identifier}")
async def get_role(
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get role details by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try to parse as UUID first
            try:
                UUID(role_identifier)
                # It's a valid UUID, search by ID
                cur.execute(
                    "SELECT id, name, description, workspace_id, policy, created_at FROM roles WHERE id = %s",
                    (role_identifier,)
                )
            except ValueError:
                # Not a UUID, search by name (global roles only for simplicity)
                cur.execute(
                    "SELECT id, name, description, workspace_id, policy, created_at FROM roles WHERE name = %s AND workspace_id IS NULL",
                    (role_identifier,)
                )
            
            role_data = cur.fetchone()
            
    if not role_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
        
    return dict(role_data)

@router.put("/{role_identifier}")
async def update_role(
    role_identifier: str,
    data: dict = Body(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update role policy or description by ID or name."""
    description = data.get("description")
    policy = data.get("policy")
    
    update_fields = []
    values = []
    
    if description is not None:
        update_fields.append("description = %s")
        values.append(description)
        
    if policy is not None:
        if isinstance(policy, str):
            try:
                policy = json.loads(policy)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON policy")
        update_fields.append("policy = %s")
        values.append(json.dumps(policy))
        
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Determine if identifier is UUID or name
    try:
        UUID(role_identifier)
        where_clause = "id = %s"
    except ValueError:
        where_clause = "name = %s AND workspace_id IS NULL"
        
    values.append(role_identifier)
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE roles SET {', '.join(update_fields)} 
                   WHERE {where_clause}
                   RETURNING id, name, description, workspace_id, policy, created_at""",
                values
            )
            updated_role = cur.fetchone()
            
    if not updated_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not found or permission denied"
        )
        
    return dict(updated_role)

@router.delete("/{role_identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a role by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Determine if identifier is UUID or name
            try:
                UUID(role_identifier)
                where_clause = "id = %s"
                check_clause = "role_id = %s"
            except ValueError:
                # Name-based lookup - need to get ID first for the check
                cur.execute(
                    "SELECT id FROM roles WHERE name = %s AND workspace_id IS NULL",
                    (role_identifier,)
                )
                role_data = cur.fetchone()
                if not role_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Role not found"
                    )
                role_id = str(role_data["id"])
                where_clause = "name = %s AND workspace_id IS NULL"
                check_clause = "role_id = %s"
                
                # Check if role is in use
                cur.execute(f"SELECT 1 FROM workspace_members WHERE {check_clause} LIMIT 1", (role_id,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete role that is assigned to members"
                    )
            else:
                # UUID-based, check directly
                cur.execute(f"SELECT 1 FROM workspace_members WHERE role_id = %s LIMIT 1", (role_identifier,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete role that is assigned to members"
                    )
                
            cur.execute(f"DELETE FROM roles WHERE {where_clause}", (role_identifier,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Role not found or permission denied"
                )
