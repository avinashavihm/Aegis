import httpx
from typing import Optional, Dict, Any
from src.config import get_api_url, get_auth_token


class APIClient:
    """HTTP client for Aegis API."""
    
    def __init__(self):
        self.base_url = get_api_url()
        self.timeout = 30.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with auth token if available."""
        headers = {"Content-Type": "application/json"}
        token = get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def request(
        self, 
        method: str, 
        endpoint: str, 
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request to API."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params
            )
            return response
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """GET request."""
        return self.request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, json: Dict[str, Any]) -> httpx.Response:
        """POST request."""
        return self.request("POST", endpoint, json=json)
    
    def put(self, endpoint: str, json: Dict[str, Any]) -> httpx.Response:
        """PUT request."""
        return self.request("PUT", endpoint, json=json)
    
    def delete(self, endpoint: str) -> httpx.Response:
        """DELETE request."""
        return self.request("DELETE", endpoint)


def get_api_client() -> APIClient:
    """Get API client instance."""
    return APIClient()
