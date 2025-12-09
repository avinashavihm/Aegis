import httpx
import time
from typing import Optional, Dict, Any, List, BinaryIO
from src.config import get_api_url, get_auth_token


class APIClient:
    """HTTP client for Aegis API with retry support."""
    
    def __init__(self, retries: int = 3, retry_delay: float = 1.0):
        self.base_url = get_api_url()
        self.timeout = 30.0
        self.retries = retries
        self.retry_delay = retry_delay
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Get headers with auth token if available."""
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        token = get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def request(
        self, 
        method: str, 
        endpoint: str, 
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ) -> httpx.Response:
        """Make HTTP request to API with optional retry."""
        url = f"{self.base_url}{endpoint}"
        # Don't set content-type for multipart uploads
        headers = self._get_headers(content_type=None if files else "application/json")
        
        attempts = self.retries if retry else 1
        last_error = None
        
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=json,
                        params=params,
                        data=data,
                        files=files
                    )
                    return response
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """GET request."""
        return self.request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, 
             data: Optional[Dict[str, Any]] = None, 
             files: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """POST request."""
        return self.request("POST", endpoint, json=json, data=data, files=files)
    
    def put(self, endpoint: str, json: Dict[str, Any]) -> httpx.Response:
        """PUT request."""
        return self.request("PUT", endpoint, json=json)
    
    def patch(self, endpoint: str, json: Dict[str, Any]) -> httpx.Response:
        """PATCH request."""
        return self.request("PATCH", endpoint, json=json)
    
    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """DELETE request."""
        return self.request("DELETE", endpoint, params=params)

    # ============= Agents API =============
    def list_agents(self, status: Optional[str] = None, tag: Optional[str] = None) -> httpx.Response:
        """List all agents."""
        params = {}
        if status:
            params["status_filter"] = status
        if tag:
            params["tag"] = tag
        return self.get("/agents", params=params or None)
    
    def get_agent(self, agent_id: str) -> httpx.Response:
        """Get agent by ID."""
        return self.get(f"/agents/{agent_id}")
    
    def create_agent(self, payload: Dict[str, Any]) -> httpx.Response:
        """Create a new agent."""
        return self.post("/agents", json=payload)
    
    def update_agent(self, agent_id: str, payload: Dict[str, Any]) -> httpx.Response:
        """Update an agent."""
        return self.put(f"/agents/{agent_id}", json=payload)
    
    def delete_agent(self, agent_id: str) -> httpx.Response:
        """Delete an agent."""
        return self.delete(f"/agents/{agent_id}")
    
    def run_agent(self, agent_id: str, input_message: str, 
                  context_variables: Optional[Dict[str, Any]] = None,
                  model_override: Optional[str] = None,
                  max_turns: Optional[int] = None) -> httpx.Response:
        """Execute an agent."""
        payload = {"input_message": input_message}
        if context_variables:
            payload["context_variables"] = context_variables
        if model_override:
            payload["model_override"] = model_override
        if max_turns:
            payload["max_turns"] = max_turns
        return self.post(f"/agents/{agent_id}/run", json=payload)
    
    def list_agent_runs(self, agent_id: str, status: Optional[str] = None, 
                        limit: int = 50) -> httpx.Response:
        """List runs for a specific agent."""
        params = {"limit": limit}
        if status:
            params["status_filter"] = status
        return self.get(f"/agents/{agent_id}/runs", params=params)

    # ============= Workflows API =============
    def list_workflows(self, status: Optional[str] = None, tag: Optional[str] = None) -> httpx.Response:
        """List all workflows."""
        params = {}
        if status:
            params["status_filter"] = status
        if tag:
            params["tag"] = tag
        return self.get("/workflows", params=params or None)
    
    def get_workflow(self, workflow_id: str) -> httpx.Response:
        """Get workflow by ID."""
        return self.get(f"/workflows/{workflow_id}")
    
    def create_workflow(self, payload: Dict[str, Any]) -> httpx.Response:
        """Create a new workflow."""
        return self.post("/workflows", json=payload)
    
    def update_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> httpx.Response:
        """Update a workflow."""
        return self.put(f"/workflows/{workflow_id}", json=payload)
    
    def delete_workflow(self, workflow_id: str) -> httpx.Response:
        """Delete a workflow."""
        return self.delete(f"/workflows/{workflow_id}")
    
    def run_workflow(self, workflow_id: str, input_message: str,
                     context_variables: Optional[Dict[str, Any]] = None,
                     model_override: Optional[str] = None,
                     max_turns: Optional[int] = None) -> httpx.Response:
        """Execute a workflow."""
        payload = {"input_message": input_message}
        if context_variables:
            payload["context_variables"] = context_variables
        if model_override:
            payload["model_override"] = model_override
        if max_turns:
            payload["max_turns"] = max_turns
        return self.post(f"/workflows/{workflow_id}/run", json=payload)
    
    def list_workflow_runs(self, workflow_id: str, status: Optional[str] = None,
                           limit: int = 50) -> httpx.Response:
        """List runs for a specific workflow."""
        params = {"limit": limit}
        if status:
            params["status_filter"] = status
        return self.get(f"/workflows/{workflow_id}/runs", params=params)

    # ============= Runs API =============
    def list_runs(self, run_type: Optional[str] = None, status: Optional[str] = None,
                  limit: int = 50) -> httpx.Response:
        """List all runs."""
        params = {"limit": limit}
        if run_type:
            params["run_type"] = run_type
        if status:
            params["status_filter"] = status
        return self.get("/runs", params=params)
    
    def get_run(self, run_id: str) -> httpx.Response:
        """Get run details by ID."""
        return self.get(f"/runs/{run_id}")
    
    def cancel_run(self, run_id: str) -> httpx.Response:
        """Cancel a running execution."""
        return self.post(f"/runs/{run_id}/cancel", json={})
    
    def delete_run(self, run_id: str) -> httpx.Response:
        """Delete a run record."""
        return self.delete(f"/runs/{run_id}")
    
    def get_run_stats(self, days: int = 30) -> httpx.Response:
        """Get run statistics."""
        return self.get("/runs/stats/summary", params={"days": days})

    # ============= Tools API =============
    def list_tools(self, category: Optional[str] = None) -> httpx.Response:
        """List all available tools."""
        params = {}
        if category:
            params["category"] = category
        return self.get("/tools", params=params or None)
    
    def get_tool(self, tool_name: str) -> httpx.Response:
        """Get tool details by name."""
        return self.get(f"/tools/{tool_name}")
    
    def list_custom_tools(self) -> httpx.Response:
        """List custom tools for current user."""
        return self.get("/tools/custom/list")
    
    def create_custom_tool(self, payload: Dict[str, Any]) -> httpx.Response:
        """Create a custom tool."""
        return self.post("/tools/custom", json=payload)
    
    def delete_custom_tool(self, tool_id: str) -> httpx.Response:
        """Delete a custom tool."""
        return self.delete(f"/tools/custom/{tool_id}")

    # ============= Agent Files API =============
    def list_agent_files(self, agent_id: Optional[str] = None) -> httpx.Response:
        """List agent files."""
        params = {}
        if agent_id:
            params["agent_id"] = agent_id
        return self.get("/agent-files", params=params or None)
    
    def get_agent_file(self, file_id: str) -> httpx.Response:
        """Get agent file metadata."""
        return self.get(f"/agent-files/{file_id}")
    
    def upload_agent_file(self, agent_id: str, file_path: str, 
                          purpose: str = "assistant") -> httpx.Response:
        """Upload a file for an agent."""
        import os
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            data = {"agent_id": agent_id, "purpose": purpose}
            return self.post("/agent-files/upload", data=data, files=files)
    
    def delete_agent_file(self, file_id: str) -> httpx.Response:
        """Delete an agent file."""
        return self.delete(f"/agent-files/{file_id}")


def get_api_client() -> APIClient:
    """Get API client instance."""
    return APIClient()
