"""
File Attachment Service - store agent files in workspace and track metadata.
"""

import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import UploadFile

from src.config import settings
from src.database import get_db_connection


class FileService:
    """Handle file uploads and retrieval for agents."""

    def __init__(self):
        self.base_dir = os.path.join(settings.workspace_dir, "agents")
        os.makedirs(self.base_dir, exist_ok=True)

    def _agent_dir(self, agent_id: str) -> str:
        return os.path.join(self.base_dir, str(agent_id), "files")

    def upload_file(
        self,
        user_id: str,
        agent_id: str,
        file: UploadFile
    ) -> Dict[str, Any]:
        """Store file to workspace and record metadata."""
        agent_dir = self._agent_dir(agent_id)
        os.makedirs(agent_dir, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = os.path.join(agent_dir, f"{file_id}_{file.filename}")

        # Write content to disk
        content = file.file.read()
        if len(content) > 5 * 1024 * 1024:
            raise ValueError("File too large (max 5MB)")
        with open(file_path, "wb") as f:
            f.write(content)

        metadata = {
            "size": len(content),
            "content_type": file.content_type,
        }

        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_files (
                        id, agent_id, file_name, file_path, file_type, file_size,
                        content_type, metadata, owner_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        file_id,
                        agent_id,
                        file.filename,
                        file_path,
                        file.content_type,
                        len(content),
                        file.content_type,
                        metadata,
                        user_id,
                    ),
                )
                result = cur.fetchone()
                conn.commit()
                return dict(result)

    def list_files(self, user_id: str, agent_id: str) -> List[Dict[str, Any]]:
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, file_name, file_type, file_size, content_type,
                           uploaded_at, metadata
                    FROM agent_files
                    WHERE agent_id = %s
                    ORDER BY uploaded_at DESC
                    """,
                    (agent_id,),
                )
                return [dict(r) for r in cur.fetchall()]

    def get_file(self, user_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM agent_files WHERE id = %s
                    """,
                    (file_id,),
                )
                res = cur.fetchone()
                return dict(res) if res else None

    def delete_file(self, user_id: str, file_id: str) -> bool:
        file_record = self.get_file(user_id, file_id)
        if not file_record:
            return False

        # Remove from DB first
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agent_files WHERE id = %s RETURNING id", (file_id,))
                res = cur.fetchone()
                conn.commit()
                if not res:
                    return False

        # Remove from disk
        path = file_record.get("file_path")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

        return True


file_service = FileService()
