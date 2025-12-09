"""
Tests for agents router
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime


class TestAgentsRouter:
    """Tests for /agents endpoints"""
    
    def test_list_agents_empty(self, client, mock_auth, mock_db_connection):
        """Test listing agents when none exist"""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = []
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.get("/agents")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_agents_with_data(self, client, mock_auth, mock_db_connection):
        """Test listing agents with data"""
        _, mock_cursor = mock_db_connection
        agent_id = uuid4()
        mock_cursor.fetchall.return_value = [
            {
                'id': agent_id,
                'name': 'Test Agent',
                'description': 'A test agent',
                'model': 'gemini/gemini-2.0-flash',
                'instructions': 'You are helpful.',
                'tools': ['read_file'],
                'tool_choice': None,
                'parallel_tool_calls': False,
                'capabilities': [],
                'autonomous_mode': False,
                'tags': ['test'],
                'metadata': {},
                'status': 'active',
                'owner_id': mock_auth,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.get("/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['name'] == 'Test Agent'
    
    def test_create_agent(self, client, mock_auth, mock_db_connection, sample_agent_data):
        """Test creating a new agent"""
        _, mock_cursor = mock_db_connection
        agent_id = uuid4()
        now = datetime.utcnow()
        
        mock_cursor.fetchone.return_value = {
            'id': agent_id,
            'name': sample_agent_data['name'],
            'description': sample_agent_data['description'],
            'model': sample_agent_data['model'],
            'instructions': sample_agent_data['instructions'],
            'tools': sample_agent_data['tools'],
            'tool_choice': sample_agent_data['tool_choice'],
            'parallel_tool_calls': sample_agent_data['parallel_tool_calls'],
            'capabilities': sample_agent_data['capabilities'],
            'autonomous_mode': sample_agent_data['autonomous_mode'],
            'tags': sample_agent_data['tags'],
            'metadata': sample_agent_data['metadata'],
            'status': sample_agent_data['status'],
            'owner_id': mock_auth,
            'created_at': now,
            'updated_at': now
        }
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.post("/agents", json=sample_agent_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == sample_agent_data['name']
        assert data['status'] == 'draft'
    
    def test_get_agent(self, client, mock_auth, mock_db_connection):
        """Test getting an agent by ID"""
        _, mock_cursor = mock_db_connection
        agent_id = uuid4()
        now = datetime.utcnow()
        
        mock_cursor.fetchone.return_value = {
            'id': agent_id,
            'name': 'Test Agent',
            'description': 'A test agent',
            'model': 'gemini/gemini-2.0-flash',
            'instructions': 'You are helpful.',
            'tools': ['read_file'],
            'tool_choice': None,
            'parallel_tool_calls': False,
            'capabilities': [],
            'autonomous_mode': False,
            'tags': ['test'],
            'metadata': {},
            'status': 'active',
            'owner_id': mock_auth,
            'created_at': now,
            'updated_at': now
        }
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.get(f"/agents/{agent_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Test Agent'
    
    def test_get_agent_not_found(self, client, mock_auth, mock_db_connection):
        """Test getting a non-existent agent"""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None
        
        agent_id = uuid4()
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.get(f"/agents/{agent_id}")
        
        assert response.status_code == 404
    
    def test_update_agent(self, client, mock_auth, mock_db_connection):
        """Test updating an agent"""
        _, mock_cursor = mock_db_connection
        agent_id = uuid4()
        now = datetime.utcnow()
        
        mock_cursor.fetchone.return_value = {
            'id': agent_id,
            'name': 'Updated Agent',
            'description': 'Updated description',
            'model': 'gemini/gemini-2.0-flash',
            'instructions': 'Updated instructions.',
            'tools': ['read_file', 'write_file'],
            'tool_choice': None,
            'parallel_tool_calls': False,
            'capabilities': [],
            'autonomous_mode': False,
            'tags': ['test', 'updated'],
            'metadata': {},
            'status': 'active',
            'owner_id': mock_auth,
            'created_at': now,
            'updated_at': now
        }
        
        update_data = {
            "name": "Updated Agent",
            "description": "Updated description",
            "status": "active"
        }
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.put(f"/agents/{agent_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Updated Agent'
        assert data['status'] == 'active'
    
    def test_delete_agent(self, client, mock_auth, mock_db_connection):
        """Test deleting an agent"""
        _, mock_cursor = mock_db_connection
        agent_id = uuid4()
        mock_cursor.fetchone.return_value = {'id': agent_id}
        
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.delete(f"/agents/{agent_id}")
        
        assert response.status_code == 204
    
    def test_delete_agent_not_found(self, client, mock_auth, mock_db_connection):
        """Test deleting a non-existent agent"""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None
        
        agent_id = uuid4()
        with patch('src.routers.agents.get_current_user_id', return_value=mock_auth):
            response = client.delete(f"/agents/{agent_id}")
        
        assert response.status_code == 404
