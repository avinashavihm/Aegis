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
    Policies are linked by ID or name.
    """
    name = data.get("name")
    description = data.get("description")
    policy_ids = data.get("policy_ids", []) # List of policy IDs
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required"
        )
    
    # Enforce slug-like naming: lowercase, alphanumeric, hyphens only
    import re
    if not re.match(r'^[a-z0-9-]+$', name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name must contain only lowercase letters, numbers, and hyphens (no spaces)"
        )
            
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check for duplicate name
                cur.execute(
                "SELECT id FROM roles WHERE name = %s",
                    (name,)
                )
                
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role with this name already exists"
                )
            
            # Create role
            cur.execute(
                """INSERT INTO roles (name, description) 
                   VALUES (%s, %s) 
                   RETURNING id, name, description, created_at""",
                (name, description)
            )
            role_data = cur.fetchone()
            role_id = role_data['id']
            
            # Link policies
            if policy_ids:
                values = [(role_id, pid) for pid in policy_ids]
                cur.executemany(
                    "INSERT INTO role_policies (role_id, policy_id) VALUES (%s, %s)",
                    values
                )
            
            conn.commit()
            
    return dict(role_data)

@router.get("")
async def list_roles(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List all roles.
    """
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
                cur.execute(
                """SELECT id, name, description, created_at 
                       FROM roles 
                       ORDER BY name"""
                )
            roles = cur.fetchall()
            
            # Fetch policies for each role
            result = []
            for role in roles:
                role_dict = dict(role)
                
                # Get attached policies
                cur.execute(
                    """SELECT p.id, p.name, p.description
                       FROM policies p
                       JOIN role_policies rp ON p.id = rp.policy_id
                       WHERE rp.role_id = %s
                       ORDER BY p.name""",
                    (role_dict['id'],)
                )
                policies = cur.fetchall()
                role_dict['policies'] = [dict(p) for p in policies]
                result.append(role_dict)
            
    return result

@router.get("/{role_identifier}")
async def get_role(
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get role details by ID or name, including policies."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try to parse as UUID first
            try:
                UUID(role_identifier)
                # It's a valid UUID, search by ID
                cur.execute(
                    "SELECT id, name, description, created_at FROM roles WHERE id = %s",
                    (role_identifier,)
                )
            except ValueError:
                # Not a UUID, search by name
                cur.execute(
                    "SELECT id, name, description, created_at FROM roles WHERE name = %s",
                    (role_identifier,)
                )
            
            role_data = cur.fetchone()
            
            if not role_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found"
                )
            
            # Fetch attached policies
            cur.execute(
                """
                SELECT p.id, p.name, p.description, p.content
                FROM role_policies rp
                JOIN policies p ON rp.policy_id = p.id
                WHERE rp.role_id = %s
                """,
                (role_data['id'],)
            )
            policies = cur.fetchall()
            
            result = dict(role_data)
            result['policies'] = [dict(p) for p in policies]
            return result

@router.put("/{role_identifier}")
async def update_role(
    role_identifier: str,
    data: dict = Body(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update role description or policies."""
    description = data.get("description")
    policy_ids = data.get("policy_ids")
    
    # Determine if identifier is UUID or name
    try:
        UUID(role_identifier)
        where_clause = "id = %s"
        identifier = role_identifier
    except ValueError:
        where_clause = "name = %s"
        identifier = role_identifier
        
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Get Role ID first
            cur.execute(f"SELECT id FROM roles WHERE {where_clause}", (identifier,))
            role = cur.fetchone()
            if not role:
                raise HTTPException(status_code=404, detail="Role not found")
            role_id = role['id']

            if description is not None:
                cur.execute(
                    "UPDATE roles SET description = %s WHERE id = %s",
                    (description, role_id)
                )
            
            if policy_ids is not None:
                # Replace all policies
                cur.execute("DELETE FROM role_policies WHERE role_id = %s", (role_id,))
                if policy_ids:
                    values = [(role_id, pid) for pid in policy_ids]
                    cur.executemany(
                        "INSERT INTO role_policies (role_id, policy_id) VALUES (%s, %s)",
                        values
                    )
            
            conn.commit()
            
            # Fetch updated role
            cur.execute("SELECT id, name, description, created_at FROM roles WHERE id = %s", (role_id,))
            updated_role = cur.fetchone()
            
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
                identifier = role_identifier
            except ValueError:
                where_clause = "name = %s"
                identifier = role_identifier
                
            # Check if role is in use
            # Need to get ID first if name was used
            cur.execute(f"SELECT id FROM roles WHERE {where_clause}", (identifier,))
            role = cur.fetchone()
            if not role:
                raise HTTPException(status_code=404, detail="Role not found")
            role_id = role['id']
            
            cur.execute("SELECT 1 FROM team_members WHERE role_id = %s LIMIT 1", (role_id,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete role that is assigned to members"
                )
                
            cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
            conn.commit()
