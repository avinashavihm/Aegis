"""
API Connectors for knowledge grounding
"""

import json
from typing import Dict, List, Any, Optional
import requests

from aegis.knowledge.connector_registry import (
    BaseConnector, ConnectorConfig, ConnectorType, 
    ConnectionStatus, ConnectorRegistry
)


class RESTAPIConnector(BaseConnector):
    """REST API connector"""
    
    connector_type = ConnectorType.API
    name = "REST API"
    description = "Connect to REST APIs"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_url = config.config.get("base_url", "")
        self.headers = config.config.get("headers", {})
        self.auth_type = config.config.get("auth_type", "none")
        self.api_key = config.credentials.get("api_key", "")
        self.api_key_header = config.config.get("api_key_header", "Authorization")
        self.timeout = config.config.get("timeout", 30)
        self._session: Optional[requests.Session] = None
    
    def connect(self) -> bool:
        try:
            self._session = requests.Session()
            
            # Set up authentication
            if self.auth_type == "api_key" and self.api_key:
                self._session.headers[self.api_key_header] = self.api_key
            elif self.auth_type == "bearer" and self.api_key:
                self._session.headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Add custom headers
            self._session.headers.update(self.headers)
            
            # Test connection
            if self.test_connection():
                self._set_connected()
                return True
            else:
                self._set_error("Connection test failed")
                return False
                
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        if self._session:
            self._session.close()
            self._session = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._session:
            raise Exception("Not connected")
        
        params = params or {}
        
        # Parse query format: METHOD:endpoint or just endpoint (defaults to GET)
        if ":" in query and query.split(":")[0].upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            method, endpoint = query.split(":", 1)
            method = method.upper()
        else:
            method = "GET"
            endpoint = query
        
        # Handle search queries
        if endpoint.startswith("search:"):
            search_term = endpoint[7:]
            endpoint = params.get("search_endpoint", "/search")
            params["q"] = search_term
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            if method == "GET":
                response = self._session.get(url, params=params, timeout=self.timeout)
            elif method == "POST":
                response = self._session.post(url, json=params, timeout=self.timeout)
            elif method == "PUT":
                response = self._session.put(url, json=params, timeout=self.timeout)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, timeout=self.timeout)
            elif method == "PATCH":
                response = self._session.patch(url, json=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except:
                return {"text": response.text, "status_code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        if not self._session:
            return False
        
        try:
            # Try to hit the base URL or a health endpoint
            health_endpoint = self.config.config.get("health_endpoint", "")
            url = f"{self.base_url.rstrip('/')}/{health_endpoint.lstrip('/')}" if health_endpoint else self.base_url
            
            response = self._session.get(url, timeout=10)
            return response.status_code < 500
        except:
            return False
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """Convenience method for GET requests"""
        return self.query(f"GET:{endpoint}", params)
    
    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Any:
        """Convenience method for POST requests"""
        return self.query(f"POST:{endpoint}", data)
    
    def put(self, endpoint: str, data: Dict[str, Any] = None) -> Any:
        """Convenience method for PUT requests"""
        return self.query(f"PUT:{endpoint}", data)
    
    def delete(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """Convenience method for DELETE requests"""
        return self.query(f"DELETE:{endpoint}", params)


class GraphQLConnector(BaseConnector):
    """GraphQL API connector"""
    
    connector_type = ConnectorType.API
    name = "GraphQL"
    description = "Connect to GraphQL APIs"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.endpoint = config.config.get("endpoint", "")
        self.headers = config.config.get("headers", {})
        self.api_key = config.credentials.get("api_key", "")
        self.auth_header = config.config.get("auth_header", "Authorization")
        self.timeout = config.config.get("timeout", 30)
        self._session: Optional[requests.Session] = None
    
    def connect(self) -> bool:
        try:
            self._session = requests.Session()
            
            # Set up authentication
            if self.api_key:
                self._session.headers[self.auth_header] = f"Bearer {self.api_key}"
            
            # Add custom headers
            self._session.headers.update(self.headers)
            self._session.headers["Content-Type"] = "application/json"
            
            self._set_connected()
            return True
            
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        if self._session:
            self._session.close()
            self._session = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._session:
            raise Exception("Not connected")
        
        params = params or {}
        
        # Handle search queries by converting to a search query
        if query.startswith("search:"):
            search_term = query[7:]
            search_query = params.get("search_query", """
                query Search($term: String!) {
                    search(query: $term) {
                        results {
                            id
                            title
                            content
                        }
                    }
                }
            """)
            query = search_query
            params = {"term": search_term}
        
        payload = {
            "query": query,
            "variables": params
        }
        
        try:
            response = self._session.post(self.endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            
            if "errors" in result:
                return {"error": result["errors"], "data": result.get("data")}
            
            return result.get("data", result)
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        if not self._session:
            return False
        
        try:
            # Send introspection query
            introspection = """
                query {
                    __schema {
                        types {
                            name
                        }
                    }
                }
            """
            result = self.query(introspection)
            return "error" not in result
        except:
            return False
    
    def execute_mutation(self, mutation: str, variables: Dict[str, Any] = None) -> Any:
        """Execute a GraphQL mutation"""
        return self.query(mutation, variables)
    
    def get_schema(self) -> Any:
        """Get the GraphQL schema"""
        introspection = """
            query {
                __schema {
                    types {
                        name
                        kind
                        fields {
                            name
                            type {
                                name
                            }
                        }
                    }
                }
            }
        """
        return self.query(introspection)


# Register connectors
ConnectorRegistry.register_type(RESTAPIConnector)
ConnectorRegistry.register_type(GraphQLConnector)

