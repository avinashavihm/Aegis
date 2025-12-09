"""
Tools router - dynamic registry-backed tool listing and custom tool management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Optional

from src.dependencies import get_current_user_id
from src.schemas import (
    AvailableToolResponse,
    AvailableToolsResponse,
    CustomToolCreate,
    CustomToolResponse,
)
from src.services.tool_registry import tool_registry
from src.services.custom_tools import custom_tool_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=AvailableToolsResponse)
async def list_tools(
    category: Optional[str] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    List all available tools (built-in, custom, MCP).
    """
    # Ensure custom tools are loaded for the user
    custom_tool_service.load_all_custom_tools(str(current_user_id))

    tool_dicts = tool_registry.list_all_as_dict()
    tools = []
    categories = set()

    for t in tool_dicts:
        if not t:
            continue
        categories.add(t.get("category"))
        if category and t.get("category") != category:
            continue
        tools.append(
            AvailableToolResponse(
                name=t.get("name"),
                description=t.get("description"),
                parameters=t.get("parameters") or [],
                category=t.get("category"),
                source=t.get("source"),
                metadata=t.get("metadata") or {},
            )
        )

    return AvailableToolsResponse(
        tools=tools,
        categories=sorted(list(categories)),
    )


@router.get("/{tool_name}", response_model=AvailableToolResponse)
async def get_tool(
    tool_name: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get details about a specific tool."""
    custom_tool_service.load_all_custom_tools(str(current_user_id))
    tool_dict = tool_registry.to_dict(tool_name)
    if not tool_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found",
        )
    return AvailableToolResponse(
        name=tool_dict.get("name"),
        description=tool_dict.get("description"),
        parameters=tool_dict.get("parameters") or [],
        category=tool_dict.get("category"),
        source=tool_dict.get("source"),
        metadata=tool_dict.get("metadata") or {},
    )


@router.get("/custom/list", response_model=list[CustomToolResponse])
async def list_custom_tools(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List custom tools for the current user."""
    return custom_tool_service.list_tools(str(current_user_id))


@router.post("/custom", response_model=CustomToolResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_tool(
    tool: CustomToolCreate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Register a new custom tool."""
    created = custom_tool_service.create_tool(str(current_user_id), tool)
    return created


@router.delete("/custom/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_tool(
    tool_id: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a custom tool."""
    ok = custom_tool_service.delete_tool(str(current_user_id), tool_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )
