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
            except Exception as e:
                conn.rollback()
                if "unique constraint" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Policy name already exists"
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
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
                cur.execute("SELECT id FROM policies WHERE name = %s", (policy_identifier,))
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Policy not found")
                policy_id = result["id"]

            try:
                cur.execute("DELETE FROM policies WHERE id = %s RETURNING id", (policy_id,))
                deleted = cur.fetchone()
                conn.commit()
                
                if not deleted:
                    raise HTTPException(status_code=404, detail="Policy not found")
            except Exception as e:
                conn.rollback()
                if "foreign key constraint" in str(e):
                    raise HTTPException(
                        status_code=400, 
                        detail="Cannot delete policy because it is attached to roles"
                    )
                raise HTTPException(status_code=400, detail=str(e))
