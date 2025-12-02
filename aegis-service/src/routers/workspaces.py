from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from uuid import UUID
from src.database import get_db_connection
from src.dependencies import get_current_user_id

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new workspace."""
    name = workspace.get("name")
    description = workspace.get("description")
    content = workspace.get("content", {})
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace name is required"
        )
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            try:
                import json
                cur.execute(
                    """
                    INSERT INTO workspaces (name, description, owner_id, content)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id, name, description, owner_id, content, created_at
                    """,
                    (name, description, str(current_user_id), json.dumps(content))
                )
                new_workspace = cur.fetchone()
                
                return dict(new_workspace)
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Workspace '{name}' already exists"
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )


@router.get("")
async def list_workspaces(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all workspaces accessible to the current user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    w.id,
                    w.name,
                    w.description,
                    w.owner_id,
                    w.content,
                    w.created_at,
                    w.updated_at,
                    u.username as owner_username
                FROM workspaces w
                LEFT JOIN users u ON w.owner_id = u.id
                ORDER BY w.created_at DESC
            """
            
            cur.execute(query)
            workspaces = cur.fetchall()
            
            return [dict(ws) for ws in workspaces]


@router.get("/{workspace_identifier}")
async def get_workspace(
    workspace_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get workspace details by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try UUID first, then name
            try:
                workspace_uuid = UUID(workspace_identifier)
                cur.execute(
                    """
                    SELECT 
                        w.id,
                        w.name,
                        w.description,
                        w.owner_id,
                        w.content,
                        w.created_at,
                        w.updated_at,
                        u.username as owner_username
                    FROM workspaces w
                    LEFT JOIN users u ON w.owner_id = u.id
                    WHERE w.id = %s
                    """,
                    (str(workspace_uuid),)
                )
            except ValueError:
                # Not a UUID, search by name
                cur.execute(
                    """
                    SELECT 
                        w.id,
                        w.name,
                        w.description,
                        w.owner_id,
                        w.content,
                        w.created_at,
                        w.updated_at,
                        u.username as owner_username
                    FROM workspaces w
                    LEFT JOIN users u ON w.owner_id = u.id
                    WHERE w.name = %s
                    """,
                    (workspace_identifier,)
                )
            
            workspace = cur.fetchone()
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
            
            return dict(workspace)


@router.put("/{workspace_identifier}")
async def update_workspace(
    workspace_identifier: str,
    workspace_update: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update workspace details."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve workspace identifier
            try:
                workspace_uuid = UUID(workspace_identifier)
                cur.execute("SELECT id, owner_id FROM workspaces WHERE id = %s", (str(workspace_uuid),))
            except ValueError:
                cur.execute("SELECT id, owner_id FROM workspaces WHERE name = %s", (workspace_identifier,))
            
            workspace = cur.fetchone()
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
            
            workspace_id = workspace['id']
            
            # Check if user is owner or admin
            if str(workspace['owner_id']) != str(current_user_id):
                # Check if admin
                cur.execute(
                    """SELECT EXISTS (
                        SELECT 1 FROM user_roles ur
                        JOIN roles r ON ur.role_id = r.id
                        WHERE ur.user_id = %s AND r.name = 'admin'
                    )""",
                    (str(current_user_id),)
                )
                is_admin = cur.fetchone()['exists']
                if not is_admin:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only workspace owner or admin can update workspace"
                    )
            
            # Build update query
            update_fields = []
            values = []
            
            if "name" in workspace_update:
                update_fields.append("name = %s")
                values.append(workspace_update["name"])
            if "description" in workspace_update:
                update_fields.append("description = %s")
                values.append(workspace_update.get("description"))
            if "settings" in workspace_update:
                update_fields.append("settings = %s")
                values.append(workspace_update["settings"])
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            values.append(str(workspace_id))
            
            cur.execute(
                f"""
                UPDATE workspaces 
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, name, description, owner_id, content, created_at, updated_at
                """,
                values
            )
            updated_workspace = cur.fetchone()
            
            return dict(updated_workspace)


@router.delete("/{workspace_identifier}")
async def delete_workspace(
    workspace_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a workspace."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve workspace identifier
            try:
                workspace_uuid = UUID(workspace_identifier)
                cur.execute("SELECT id, owner_id FROM workspaces WHERE id = %s", (str(workspace_uuid),))
            except ValueError:
                cur.execute("SELECT id, owner_id FROM workspaces WHERE name = %s", (workspace_identifier,))
            
            workspace = cur.fetchone()
            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
            
            # Check if user is owner or admin
            if str(workspace['owner_id']) != str(current_user_id):
                cur.execute(
                    """SELECT EXISTS (
                        SELECT 1 FROM user_roles ur
                        JOIN roles r ON ur.role_id = r.id
                        WHERE ur.user_id = %s AND r.name = 'admin'
                    )""",
                    (str(current_user_id),)
                )
                is_admin = cur.fetchone()['exists']
                if not is_admin:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only workspace owner or admin can delete workspace"
                    )
            
            cur.execute("DELETE FROM workspaces WHERE id = %s", (workspace['id'],))
            
            return {"message": "Workspace deleted successfully"}



