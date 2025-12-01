from fastapi import APIRouter, HTTPException, status, Depends, Body
from src.database import get_db_connection
from src.dependencies import get_current_user, get_current_user_id
from uuid import UUID

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new workspace.
    The creator becomes the owner and admin automatically.
    """
    name = data.get("name")
    slug = data.get("slug")
    
    if not all([name, slug]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and slug are required"
        )
    
    with get_db_connection(str(current_user["id"])) as conn:
        with conn.cursor() as cur:
            # Check if slug is unique
            cur.execute("SELECT id FROM workspaces WHERE slug = %s", (slug,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Workspace slug already exists"
                )
            
            # Create workspace
            cur.execute(
                """INSERT INTO workspaces (name, slug, owner_id) 
                   VALUES (%s, %s, %s) 
                   RETURNING id, name, slug, owner_id, created_at""",
                (name, slug, str(current_user["id"]))
            )
            workspace_data = cur.fetchone()
            
            # Get Admin Role ID
            cur.execute("SELECT id FROM roles WHERE name = 'admin' AND workspace_id IS NULL")
            admin_role = cur.fetchone()
            
            if not admin_role:
                # Fallback if DB not seeded correctly, though it should be
                raise HTTPException(status_code=500, detail="System configuration error: admin role not found")

            # Add creator as admin member
            cur.execute(
                """INSERT INTO workspace_members (workspace_id, user_id, role_id) 
                   VALUES (%s, %s, %s)""",
                (str(workspace_data["id"]), str(current_user["id"]), str(admin_role["id"]))
            )
    
    return dict(workspace_data)


@router.get("")
async def list_workspaces(current_user_id: UUID = Depends(get_current_user_id)):
    """
    List all workspaces accessible to the user.
    RLS policies automatically filter based on membership.
    """
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, slug, owner_id, created_at FROM workspaces"
            )
            workspaces = cur.fetchall()
    
    return [dict(ws) for ws in workspaces]

@router.get("/{workspace_identifier}")
async def get_workspace(
    workspace_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get workspace by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try to parse as UUID first
            try:
                UUID(workspace_identifier)
                # It's a valid UUID, search by ID
                cur.execute(
                    "SELECT id, name, slug, owner_id, created_at FROM workspaces WHERE id = %s",
                    (workspace_identifier,)
                )
            except ValueError:
                # Not a UUID, search by name or slug
                cur.execute(
                    "SELECT id, name, slug, owner_id, created_at FROM workspaces WHERE name = %s OR slug = %s",
                    (workspace_identifier, workspace_identifier)
                )
            
            workspace_data = cur.fetchone()
            
    if not workspace_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
        
    return dict(workspace_data)


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: UUID,
    data: dict = Body(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update workspace details.
    Only owner or admin can update (enforced by RLS).
    """
    name = data.get("name")
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE workspaces SET name = %s 
                   WHERE id = %s 
                   RETURNING id, name, slug, owner_id, created_at""",
                (name, str(workspace_id))
            )
            updated_workspace = cur.fetchone()
    
    if not updated_workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace not found or permission denied"
        )
    
    return dict(updated_workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a workspace.
    Only the owner can delete (enforced by RLS).
    """
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workspaces WHERE id = %s", (str(workspace_id),))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Workspace not found or permission denied"
                )


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all members of a workspace with their role details."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT wm.workspace_id, wm.user_id, wm.joined_at,
                          r.id as role_id, r.name as role_name, r.description as role_description
                   FROM workspace_members wm
                   JOIN roles r ON wm.role_id = r.id
                   WHERE wm.workspace_id = %s""",
                (str(workspace_id),)
            )
            members = cur.fetchall()
    
    return [dict(member) for member in members]


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: UUID,
    data: dict = Body(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Add a member to the workspace.
    Only owner or admin can add members (enforced by RLS/Policy).
    """
    user_id = data.get("user_id")
    role_name = data.get("role", "viewer") # Default to viewer
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required"
        )
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE id = %s", (str(user_id),))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Resolve Role ID
            # Check for workspace-specific role first, then global
            cur.execute(
                """SELECT id FROM roles 
                   WHERE name = %s 
                   AND (workspace_id = %s OR workspace_id IS NULL)
                   ORDER BY workspace_id NULLS LAST
                   LIMIT 1""",
                (role_name, str(workspace_id))
            )
            role_data = cur.fetchone()
            
            if not role_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_name}' not found"
                )
            
            role_id = role_data["id"]
            
            # Add member (RLS will enforce permission)
            cur.execute(
                """INSERT INTO workspace_members (workspace_id, user_id, role_id) 
                   VALUES (%s, %s, %s) 
                   RETURNING workspace_id, user_id, role_id, joined_at""",
                (str(workspace_id), str(user_id), str(role_id))
            )
            member_data = cur.fetchone()
    
    if not member_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied to add members"
        )
    
    return dict(member_data)


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Remove a member from the workspace.
    Owner/admin can remove others, any member can remove themselves (enforced by RLS).
    """
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM workspace_members WHERE workspace_id = %s AND user_id = %s",
                (str(workspace_id), str(user_id))
            )
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Member not found or permission denied"
                )
