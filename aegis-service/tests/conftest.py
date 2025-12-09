"""
Test configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Mock the database connection before importing the app
@pytest.fixture(autouse=True)
def mock_db_connection():
    """Mock database connection for all tests"""
    with patch('src.database.get_db_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock.return_value = mock_conn
        yield mock, mock_cursor


@pytest.fixture
def client():
    """Create test client"""
    from src.main import app
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication for tests"""
    user_id = uuid4()
    with patch('src.dependencies.get_current_user_id') as mock:
        mock.return_value = user_id
        yield user_id


@pytest.fixture
def sample_agent_data():
    """Sample agent data for tests"""
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "model": "gemini/gemini-2.0-flash",
        "instructions": "You are a helpful test agent.",
        "tools": ["read_file", "write_file"],
        "tool_choice": None,
        "parallel_tool_calls": False,
        "capabilities": [],
        "autonomous_mode": False,
        "tags": ["test", "demo"],
        "metadata": {"version": "1.0"},
        "status": "draft"
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for tests"""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "steps": [
            {
                "step_id": "step1",
                "agent_id": str(uuid4()),
                "name": "First Step",
                "description": "Process input",
                "input_mapping": {},
                "output_key": "step1_output"
            }
        ],
        "execution_mode": "sequential",
        "tags": ["test"],
        "metadata": {},
        "status": "draft"
    }


@pytest.fixture
def sample_run_request():
    """Sample run request data"""
    return {
        "input_message": "Hello, please help me with a task.",
        "context_variables": {"user_name": "Test User"},
        "max_turns": 5
    }
