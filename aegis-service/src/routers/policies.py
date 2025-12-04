from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Any
from uuid import UUID
from ..database import get_db_connection
from ..dependencies import get_current_user_id
import json

router = APIRouter(
    prefix="/policies",
    tags=["policies"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new policy."""
    name = policy.get("name")
    description = policy.get("description")
    content = policy.get("content")
    
    if not name or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name and content are required"
        )
    
    # Validate content is valid JSON if passed as string
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON content"
            )

    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO policies (name, description, content)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, description, content, created_at
                    """,
                    (name, description, json.dumps(content))
                )
                new_policy = cur.fetchone()
                conn.commit()
                return dict(new_policy)
            except HTTPException:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                error_msg = str(e)
                if "unique constraint" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Policy name already exists"
                    )
                if "row-level security" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=error_msg
                    )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )

@router.get("")
async def list_policies(current_user_id: UUID = Depends(get_current_user_id)):
    """List all policies."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, content, created_at FROM policies"
            )
            policies = cur.fetchall()
    
    return [dict(p) for p in policies]

@router.get("/{policy_identifier}")
async def get_policy(
    policy_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get policy by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            try:
                UUID(policy_identifier)
                cur.execute(
                    "SELECT id, name, description, content, created_at FROM policies WHERE id = %s",
                    (policy_identifier,)
                )
            except ValueError:
                cur.execute(
                    "SELECT id, name, description, content, created_at FROM policies WHERE name = %s",
                    (policy_identifier,)
                )
            
            policy = cur.fetchone()
            
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    return dict(policy)
        
@router.put("/{policy_identifier}")
async def update_policy(
    policy_identifier: str,
    policy_update: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update a policy."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve ID
            try:
                UUID(policy_identifier)
                policy_id = policy_identifier
            except ValueError:
                cur.execute("SELECT id FROM policies WHERE name = %s", (policy_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Policy not found")
                policy_id = result["id"]

            # Build update query
            updates = []
            values = []
            
            if "name" in policy_update:
                updates.append("name = %s")
                values.append(policy_update["name"])
            
            if "description" in policy_update:
                updates.append("description = %s")
                values.append(policy_update["description"])
                
            if "content" in policy_update:
                content = policy_update["content"]
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        raise HTTPException(status_code=400, detail="Invalid JSON content")
                updates.append("content = %s")
                values.append(json.dumps(content))

            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")

            values.append(policy_id)
            
            try:
                cur.execute(
                    f"""
                    UPDATE policies 
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING id, name, description, content, created_at
                    """,
                    tuple(values)
                )
                updated_policy = cur.fetchone()
                conn.commit()
                
                if not updated_policy:
                    raise HTTPException(status_code=404, detail="Policy not found")
                    
                return dict(updated_policy)
            except Exception as e:
                conn.rollback()
                if "unique constraint" in str(e):
                    raise HTTPException(status_code=409, detail="Policy name already exists")
                raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{policy_identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a policy."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Resolve ID
            try:
                UUID(policy_identifier)
                policy_id = policy_identifier
            except ValueError:
                cur.execute("SELECT id, name FROM policies WHERE name = %s", (policy_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Policy not found")
                policy_id = result["id"]
                policy_name = result["name"]
            else:
                cur.execute("SELECT name FROM policies WHERE id = %s", (policy_id,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Policy not found")
                policy_name = result["name"]

            # Check if policy is attached to any roles using SECURITY DEFINER function
            try:
                cur.execute(
                    "SELECT role_id, role_name FROM check_policy_attached_to_roles(%s::uuid)",
                    (policy_id,)
                )
                attached_roles_raw = cur.fetchall()
            except Exception as e:
                # If function doesn't exist or error, fall back to direct query
                cur.execute(
                    """SELECT r.id as role_id, r.name as role_name 
                       FROM roles r
                       JOIN role_policies rp ON r.id = rp.role_id
                       WHERE rp.policy_id = %s
                       LIMIT 5""",
                    (policy_id,)
                )
                attached_roles_raw = cur.fetchall()
            
            # Convert to dict format for consistency
            attached_roles = []
            if attached_roles_raw:
                for r in attached_roles_raw:
                    attached_roles.append({
                        "id": str(r.get("role_id", r.get("id", ""))),
                        "name": str(r.get("role_name", r.get("name", "")))
                    })
            
            if attached_roles:
                role_names = [r["name"] for r in attached_roles]
                if len(role_names) == 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot delete policy '{policy_name}' because it is attached to role '{role_names[0]}'. Please detach the policy from the role first."
                    )
                else:
                    role_list = ", ".join(role_names[:3])
                    if len(attached_roles) > 3:
                        role_list += f" and {len(attached_roles) - 3} more"
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot delete policy '{policy_name}' because it is attached to roles: {role_list}. Please detach the policy from all roles first."
                    )

            try:
                cur.execute("DELETE FROM policies WHERE id = %s RETURNING id", (policy_id,))
                deleted = cur.fetchone()
                conn.commit()
                
                if not deleted:
                    raise HTTPException(status_code=404, detail="Policy not found")
            except Exception as e:
                conn.rollback()
                error_msg = str(e)
                if "foreign key constraint" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete policy because it is attached to roles"
                    )
                if "row-level security" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=error_msg
                    )
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)
