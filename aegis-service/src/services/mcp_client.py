"""
MCP Integration - manage and interact with Model Context Protocol servers.
This module provides a thin abstraction for registering MCP servers and
fetching their tool metadata. Execution of MCP tools can be integrated in
AgentRunner by mapping them to callable wrappers.
"""

import json
import subprocess
import threading
from typing import Dict, Any, List, Optional

import requests

from src.config import settings
from src.database import get_db_connection


class MCPClient:
    """
    Lightweight MCP client supporting stdio and HTTP/SSE transports.
    Currently provides metadata fetch; execution is wired via AgentRunner.
    """

    def __init__(self):
        self.processes = {}

    # ---------- Registry helpers ----------
    def register_server(self, user_id: str, server: Dict[str, Any]) -> Dict[str, Any]:
        """Persist an MCP server configuration and return record."""
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mcp_servers (
                        id, name, description, server_type, transport_type,
                        endpoint_url, command, args, env_vars, config, status, owner_id
                    ) VALUES (
                        uuid_generate_v4(), %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING *
                    """,
                    (
                        server.get("name"),
                        server.get("description"),
                        server.get("server_type", "external"),
                        server.get("transport_type", "stdio"),
                        server.get("endpoint_url"),
                        server.get("command"),
                        json.dumps(server.get("args", [])),
                        json.dumps(server.get("env_vars", {})),
                        json.dumps(server.get("config", {})),
                        server.get("status", "inactive"),
                        user_id,
                    ),
                )
                result = cur.fetchone()
                conn.commit()
                return dict(result)

    def list_servers(self, user_id: str) -> List[Dict[str, Any]]:
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, description, server_type, transport_type,
                           endpoint_url, status, created_at, updated_at
                    FROM mcp_servers
                    ORDER BY created_at DESC
                    """
                )
                return [dict(r) for r in cur.fetchall()]

    def get_server(self, user_id: str, server_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM mcp_servers WHERE id = %s
                    """,
                    (server_id,),
                )
                res = cur.fetchone()
                return dict(res) if res else None

    # ---------- Tool metadata ----------
    def list_tools_from_server(self, server: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch tool metadata from a server. HTTP supported; stdio returns placeholder."""
        transport = server.get("transport_type", "stdio")
        if transport in ("http", "sse") and server.get("endpoint_url"):
            try:
                resp = requests.get(f"{server['endpoint_url'].rstrip('/')}/tools", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return data.get("tools", []) if isinstance(data, dict) else []
            except Exception:
                return []
        # For stdio/custom transports, return empty; AgentRunner can spin processes on demand
        return []

    # ---------- Process handling for stdio servers (stub) ----------
    def start_stdio_server(self, server: Dict[str, Any]) -> Optional[subprocess.Popen]:
        command = server.get("command")
        if not command:
            return None
        args = server.get("args") or []
        env = {**settings.env_vars, **(server.get("env_vars") or {})} if hasattr(settings, "env_vars") else None
        proc = subprocess.Popen(
            [command, *args],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.processes[str(server.get("id"))] = proc
        return proc

    def stop_server(self, server_id: str):
        proc = self.processes.get(server_id)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        if server_id in self.processes:
            del self.processes[server_id]


# Singleton instance
mcp_client = MCPClient()
