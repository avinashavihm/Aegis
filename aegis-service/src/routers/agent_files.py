"""
Agent file management endpoints.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from uuid import UUID

from src.dependencies import get_current_user_id
from src.services.file_service import file_service
from src.schemas import AgentFileResponse

router = APIRouter(prefix="/agents", tags=["agent-files"])


@router.post("/{agent_id}/files", response_model=AgentFileResponse)
async def upload_agent_file(
    agent_id: UUID,
    upload: UploadFile = File(...),
    current_user_id: UUID = Depends(get_current_user_id)
):
    record = file_service.upload_file(str(current_user_id), str(agent_id), upload)
    return record


@router.get("/{agent_id}/files", response_model=list[AgentFileResponse])
async def list_agent_files(
    agent_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    return file_service.list_files(str(current_user_id), str(agent_id))


@router.get("/{agent_id}/files/{file_id}", response_model=AgentFileResponse)
async def get_agent_file(
    agent_id: UUID,
    file_id: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    record = file_service.get_file(str(current_user_id), file_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if str(record.get("agent_id")) != str(agent_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File not owned by agent")
    return record


@router.delete("/{agent_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_file(
    agent_id: UUID,
    file_id: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    record = file_service.get_file(str(current_user_id), file_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if str(record.get("agent_id")) != str(agent_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File not owned by agent")
    deleted = file_service.delete_file(str(current_user_id), file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to delete")
