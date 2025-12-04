"""
Cloud Service Connectors for knowledge grounding
"""

import os
import json
from typing import Dict, List, Any, Optional
from io import BytesIO

from aegis.knowledge.connector_registry import (
    BaseConnector, ConnectorConfig, ConnectorType, 
    ConnectionStatus, ConnectorRegistry
)


class S3Connector(BaseConnector):
    """Amazon S3 connector"""
    
    connector_type = ConnectorType.CLOUD
    name = "S3"
    description = "Connect to Amazon S3 buckets"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.bucket_name = config.config.get("bucket_name", "")
        self.region = config.config.get("region", "us-east-1")
        self.prefix = config.config.get("prefix", "")
        self.access_key = config.credentials.get("access_key", "")
        self.secret_key = config.credentials.get("secret_key", "")
        self._client = None
    
    def connect(self) -> bool:
        try:
            import boto3
            
            if self.access_key and self.secret_key:
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
            else:
                # Use default credentials
                self._client = boto3.client('s3', region_name=self.region)
            
            # Test connection
            self._client.head_bucket(Bucket=self.bucket_name)
            self._set_connected()
            return True
            
        except ImportError:
            self._set_error("boto3 not installed. Run: pip install boto3")
            return False
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        self._client = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._client:
            raise Exception("Not connected")
        
        params = params or {}
        
        # Parse query
        if ":" in query:
            action, target = query.split(":", 1)
            action = action.lower()
        else:
            action = "get"
            target = query
        
        if action == "list":
            return self._list_objects(target or self.prefix)
        elif action == "get":
            return self._get_object(target)
        elif action == "search":
            return self._search_objects(target)
        elif action == "info":
            return self._get_object_info(target)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in bucket"""
        full_prefix = f"{self.prefix}/{prefix}".strip("/")
        
        response = self._client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=full_prefix,
            MaxKeys=1000
        )
        
        objects = []
        for obj in response.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "storage_class": obj.get("StorageClass", "STANDARD")
            })
        
        return objects
    
    def _get_object(self, key: str) -> Any:
        """Get object contents"""
        full_key = f"{self.prefix}/{key}".strip("/")
        
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=full_key)
            content = response["Body"].read()
            
            # Try to decode as text
            try:
                text = content.decode('utf-8')
                
                # Try to parse as JSON
                if key.endswith('.json'):
                    return {"content": json.loads(text), "format": "json"}
                
                return {"content": text, "format": "text"}
            except:
                return {"content": f"Binary data ({len(content)} bytes)", "format": "binary"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _search_objects(self, term: str) -> List[Dict[str, Any]]:
        """Search for objects containing term in name"""
        objects = self._list_objects()
        
        results = []
        term_lower = term.lower()
        
        for obj in objects:
            if term_lower in obj["key"].lower():
                results.append(obj)
        
        return results
    
    def _get_object_info(self, key: str) -> Dict[str, Any]:
        """Get object metadata"""
        full_key = f"{self.prefix}/{key}".strip("/")
        
        try:
            response = self._client.head_object(Bucket=self.bucket_name, Key=full_key)
            return {
                "key": key,
                "size": response["ContentLength"],
                "content_type": response.get("ContentType", "unknown"),
                "last_modified": response["LastModified"].isoformat(),
                "metadata": response.get("Metadata", {})
            }
        except Exception as e:
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
            return True
        except:
            return False


class GCSConnector(BaseConnector):
    """Google Cloud Storage connector"""
    
    connector_type = ConnectorType.CLOUD
    name = "GCS"
    description = "Connect to Google Cloud Storage buckets"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.bucket_name = config.config.get("bucket_name", "")
        self.prefix = config.config.get("prefix", "")
        self.project = config.config.get("project", "")
        self.credentials_path = config.credentials.get("credentials_path", "")
        self._client = None
        self._bucket = None
    
    def connect(self) -> bool:
        try:
            from google.cloud import storage
            
            if self.credentials_path:
                self._client = storage.Client.from_service_account_json(self.credentials_path)
            else:
                self._client = storage.Client(project=self.project)
            
            self._bucket = self._client.bucket(self.bucket_name)
            
            # Test connection
            self._bucket.exists()
            self._set_connected()
            return True
            
        except ImportError:
            self._set_error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
            return False
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        self._client = None
        self._bucket = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._bucket:
            raise Exception("Not connected")
        
        params = params or {}
        
        # Parse query
        if ":" in query:
            action, target = query.split(":", 1)
            action = action.lower()
        else:
            action = "get"
            target = query
        
        if action == "list":
            return self._list_blobs(target or self.prefix)
        elif action == "get":
            return self._get_blob(target)
        elif action == "search":
            return self._search_blobs(target)
        elif action == "info":
            return self._get_blob_info(target)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _list_blobs(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List blobs in bucket"""
        full_prefix = f"{self.prefix}/{prefix}".strip("/")
        
        blobs = list(self._bucket.list_blobs(prefix=full_prefix, max_results=1000))
        
        return [
            {
                "name": blob.name,
                "size": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "content_type": blob.content_type
            }
            for blob in blobs
        ]
    
    def _get_blob(self, name: str) -> Any:
        """Get blob contents"""
        full_name = f"{self.prefix}/{name}".strip("/")
        
        try:
            blob = self._bucket.blob(full_name)
            content = blob.download_as_bytes()
            
            # Try to decode as text
            try:
                text = content.decode('utf-8')
                
                if name.endswith('.json'):
                    return {"content": json.loads(text), "format": "json"}
                
                return {"content": text, "format": "text"}
            except:
                return {"content": f"Binary data ({len(content)} bytes)", "format": "binary"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _search_blobs(self, term: str) -> List[Dict[str, Any]]:
        """Search for blobs containing term in name"""
        blobs = self._list_blobs()
        
        term_lower = term.lower()
        return [blob for blob in blobs if term_lower in blob["name"].lower()]
    
    def _get_blob_info(self, name: str) -> Dict[str, Any]:
        """Get blob metadata"""
        full_name = f"{self.prefix}/{name}".strip("/")
        
        try:
            blob = self._bucket.blob(full_name)
            blob.reload()
            
            return {
                "name": name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "metadata": blob.metadata or {}
            }
        except Exception as e:
            return {"error": str(e)}
    
    def test_connection(self) -> bool:
        if not self._bucket:
            return False
        try:
            return self._bucket.exists()
        except:
            return False


# Register connectors
ConnectorRegistry.register_type(S3Connector)
ConnectorRegistry.register_type(GCSConnector)

