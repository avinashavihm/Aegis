"""
MCP server management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from src.dependencies import get_current_user_id
from src.schemas import MCPServerCreate, MCPServerResponse
from src.services.mcp_client import mcp_client
from src.database import get_db_connection

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_server(
    server: MCPServerCreate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    record = mcp_client.register_server(str(current_user_id), server.model_dump())
    return record


@router.get("/servers", response_model=List[MCPServerResponse])
async def list_servers(
    current_user_id: UUID = Depends(get_current_user_id)
):
    return mcp_client.list_servers(str(current_user_id))


@router.post("/agents/{agent_id}/{server_id}", status_code=status.HTTP_201_CREATED)
async def attach_server_to_agent(
    agent_id: UUID,
    server_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_mcp_servers (agent_id, mcp_server_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                RETURNING agent_id, mcp_server_id
                """,
                (str(agent_id), str(server_id)),
            )
            res = cur.fetchone()
            conn.commit()
            if not res:
                return {"status": "exists"}
            return {"status": "attached", "agent_id": agent_id, "server_id": server_id}


@router.delete("/agents/{agent_id}/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_server_from_agent(
    agent_id: UUID,
    server_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM agent_mcp_servers WHERE agent_id = %s AND mcp_server_id = %s RETURNING agent_id",
                (str(agent_id), str(server_id)),
            )
            res = cur.fetchone()
            conn.commit()
            if not res:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
