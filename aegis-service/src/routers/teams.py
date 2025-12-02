from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from uuid import UUID
from src.database import get_db_connection
from src.dependencies import get_current_user_id

router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    team: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new team."""
    name = team.get("name")
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name is required"
        )
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO teams (name, owner_id)
                    VALUES (%s, %s)
                    RETURNING id, name, owner_id, created_at
                    """,
                    (name, str(current_user_id))
                )
                new_team = cur.fetchone()
                
                # Add owner as a member with 'admin' role automatically
                # First get the admin role ID
                cur.execute("SELECT id FROM roles WHERE name = 'admin'")
                admin_role = cur.fetchone()
                
                if admin_role:
                    cur.execute(
                        """
                        INSERT INTO team_members (team_id, user_id, role_id)
                        VALUES (%s, %s, %s)
                        """,
                        (new_team['id'], str(current_user_id), admin_role['id'])
                    )
                
                conn.commit()
                return dict(new_team)
            except Exception as e:
                conn.rollback()
                if "unique constraint" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Team name already exists"
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

@router.get("")
async def list_teams(current_user_id: UUID = Depends(get_current_user_id)):
    """List all teams visible to the current user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, owner_id, created_at FROM teams"
            )
            teams = cur.fetchall()
            
            # Fetch roles for each team
            result = []
            for team in teams:
                team_dict = dict(team)
                
                # Get roles assigned to the team itself
                cur.execute(
                    """SELECT r.name
                       FROM team_roles tr
                       JOIN roles r ON tr.role_id = r.id
                       WHERE tr.team_id = %s
                       ORDER BY r.name""",
                    (team_dict['id'],)
                )
                team_roles = cur.fetchall()
                
                # Get members
                cur.execute(
                    """SELECT u.username
                       FROM team_members tm
                       JOIN users u ON tm.user_id = u.id
                       WHERE tm.team_id = %s
                       ORDER BY u.username""",
                    (team_dict['id'],)
                )
                members = cur.fetchall()
                
                team_dict['team_roles'] = [r['name'] for r in team_roles]
                team_dict['members'] = [m['username'] for m in members]
                
                result.append(team_dict)
    
    return result



@router.post("/{team_id}/roles/{role_identifier}")
async def assign_role_to_team(
    team_id: UUID,
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Assign a role directly to a team (inherited by all members)."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check if team exists
            cur.execute("SELECT id FROM teams WHERE id = %s", (str(team_id),))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Team not found")

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
                "SELECT 1 FROM team_roles WHERE team_id = %s AND role_id = %s",
                (str(team_id), role_id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Role already assigned to this team")
            
            # Assign role
            try:
                cur.execute(
                    "INSERT INTO team_roles (team_id, role_id) VALUES (%s, %s)",
                    (str(team_id), role_id)
                )
                conn.commit()
                return {"message": "Role assigned to team successfully"}
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/roles/{role_identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_team(
    team_id: UUID,
    role_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Remove a role from a team."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check if team exists
            cur.execute("SELECT id FROM teams WHERE id = %s", (str(team_id),))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Team not found")

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
                    "DELETE FROM team_roles WHERE team_id = %s AND role_id = %s RETURNING team_id",
                    (str(team_id), role_id)
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

@router.get("/{team_identifier}")
async def get_team(
    team_identifier: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get team by ID or name."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Try to parse as UUID first
            try:
                UUID(team_identifier)
                # It's a valid UUID, search by ID
                cur.execute(
                    "SELECT id, name, owner_id, created_at FROM teams WHERE id = %s",
                    (team_identifier,)
                )
            except ValueError:
                # Not a UUID, search by name
                cur.execute(
                    "SELECT id, name, owner_id, created_at FROM teams WHERE name = %s",
                    (team_identifier,)
                )
            
            team_data = cur.fetchone()
            
    if not team_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
        
    return dict(team_data)

@router.put("/{team_id}")
async def update_team(
    team_id: UUID,
    team_update: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update a team."""
    name = team_update.get("name")
    
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required"
        )

    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE teams 
                SET name = %s 
                WHERE id = %s
                RETURNING id, name, owner_id, created_at
                """,
                (name, str(team_id))
            )
            updated_team = cur.fetchone()
            conn.commit()
            
    if not updated_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or access denied"
        )
        
    return dict(updated_team)

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a team."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM teams WHERE id = %s RETURNING id",
                (str(team_id),)
            )
            deleted = cur.fetchone()
            conn.commit()
            
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found or access denied"
        )

# Member Management

@router.get("/{team_id}/members")
async def list_team_members(
    team_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List members of a team."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Check if team exists first
            cur.execute("SELECT name FROM teams WHERE id = %s", (str(team_id),))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Team not found")

            cur.execute(
                """
                SELECT tm.user_id, u.username, u.email, r.name as role_name, tm.joined_at
                FROM team_members tm
                JOIN users u ON tm.user_id = u.id
                LEFT JOIN roles r ON tm.role_id = r.id
                WHERE tm.team_id = %s
                """,
                (str(team_id),)
            )
            members = cur.fetchall()
            
    return [dict(m) for m in members]

@router.post("/{team_id}/members")
async def add_team_member(
    team_id: UUID,
    member_data: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Add a member to the team."""
    username = member_data.get("username")
    role_name = member_data.get("role", "viewer") # Default to viewer
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # 1. Get User ID
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # 2. Get Role ID
            cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            role = cur.fetchone()
            if not role:
                raise HTTPException(status_code=400, detail=f"Role '{role_name}' not found")

            # 3. Add Member
            try:
                cur.execute(
                    """
                    INSERT INTO team_members (team_id, user_id, role_id)
                    VALUES (%s, %s, %s)
                    RETURNING team_id, user_id, role_id, joined_at
                    """,
                    (str(team_id), user['id'], role['id'])
                )
                new_member = cur.fetchone()
                conn.commit()
                return dict(new_member)
            except Exception as e:
                conn.rollback()
                if "unique constraint" in str(e):
                    raise HTTPException(status_code=409, detail="User is already a member")
                raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Remove a member from the team."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM team_members WHERE team_id = %s AND user_id = %s RETURNING user_id",
                (str(team_id), str(user_id))
            )
            deleted = cur.fetchone()
            conn.commit()
            
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found or access denied"
        )
