"""
Tests for Aegis CLI commands.

Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_api_response():
    """Create a mock HTTP response."""
    def _create(status_code=200, json_data=None):
        mock = Mock()
        mock.status_code = status_code
        mock.json.return_value = json_data or {}
        mock.text = str(json_data) if json_data else ""
        return mock
    return _create


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_help(self, runner):
        """Test that CLI shows help."""
        from src.main import app
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Aegis CLI" in result.stdout
    
    def test_cli_version(self, runner):
        """Test version command."""
        from src.main import app
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()


class TestAgentCommands:
    """Test agent command group."""
    
    def test_agent_list_help(self, runner):
        """Test agent list help."""
        from src.main import app
        result = runner.invoke(app, ["agent", "list", "--help"])
        assert result.exit_code == 0
        assert "List all agents" in result.stdout
    
    @patch('src.commands.agent.get_api_client')
    def test_agent_list(self, mock_client, runner, mock_api_response):
        """Test listing agents."""
        from src.main import app
        
        mock_instance = Mock()
        mock_instance.list_agents.return_value = mock_api_response(200, [
            {"name": "test-agent", "model": "gpt-4o", "status": "active", "tools": [], "tags": []}
        ])
        mock_client.return_value = mock_instance
        
        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0
        mock_instance.list_agents.assert_called_once()
    
    @patch('src.commands.agent.get_api_client')
    def test_agent_create(self, mock_client, runner, mock_api_response):
        """Test creating an agent."""
        from src.main import app
        
        mock_instance = Mock()
        mock_instance.create_agent.return_value = mock_api_response(201, {
            "id": "test-id", "name": "new-agent", "model": "gpt-4o"
        })
        mock_client.return_value = mock_instance
        
        result = runner.invoke(app, ["agent", "create", "new-agent"])
        assert result.exit_code == 0
        mock_instance.create_agent.assert_called_once()


class TestWorkflowCommands:
    """Test workflow command group."""
    
    def test_workflow_list_help(self, runner):
        """Test workflow list help."""
        from src.main import app
        result = runner.invoke(app, ["workflow", "list", "--help"])
        assert result.exit_code == 0
        assert "List all workflows" in result.stdout
    
    @patch('src.commands.workflow.get_api_client')
    def test_workflow_list(self, mock_client, runner, mock_api_response):
        """Test listing workflows."""
        from src.main import app
        
        mock_instance = Mock()
        mock_instance.list_workflows.return_value = mock_api_response(200, [
            {"name": "test-workflow", "execution_mode": "sequential", "status": "active", "steps": [], "tags": []}
        ])
        mock_client.return_value = mock_instance
        
        result = runner.invoke(app, ["workflow", "list"])
        assert result.exit_code == 0
        mock_instance.list_workflows.assert_called_once()


class TestRunCommands:
    """Test run command group."""
    
    def test_run_list_help(self, runner):
        """Test run list help."""
        from src.main import app
        result = runner.invoke(app, ["run", "list", "--help"])
        assert result.exit_code == 0
        assert "List all runs" in result.stdout
    
    @patch('src.commands.run.get_api_client')
    def test_run_list(self, mock_client, runner, mock_api_response):
        """Test listing runs."""
        from src.main import app
        
        mock_instance = Mock()
        mock_instance.list_runs.return_value = mock_api_response(200, [
            {"id": "test-id", "run_type": "agent", "status": "completed", "started_at": "2024-01-01"}
        ])
        mock_client.return_value = mock_instance
        
        result = runner.invoke(app, ["run", "list"])
        assert result.exit_code == 0
        mock_instance.list_runs.assert_called_once()


class TestToolCommands:
    """Test tool command group."""
    
    def test_tool_list_help(self, runner):
        """Test tool list help."""
        from src.main import app
        result = runner.invoke(app, ["tool", "list", "--help"])
        assert result.exit_code == 0
        assert "List all available tools" in result.stdout
    
    @patch('src.commands.tool.get_api_client')
    def test_tool_list(self, mock_client, runner, mock_api_response):
        """Test listing tools."""
        from src.main import app
        
        mock_instance = Mock()
        mock_instance.list_tools.return_value = mock_api_response(200, {
            "tools": [{"name": "web_search", "category": "search", "source": "builtin"}],
            "categories": ["search"]
        })
        mock_client.return_value = mock_instance
        
        result = runner.invoke(app, ["tool", "list"])
        assert result.exit_code == 0
        mock_instance.list_tools.assert_called_once()


class TestResourceTypeNormalization:
    """Test resource type aliases."""
    
    def test_normalize_agent_aliases(self):
        from src.main import normalize_resource_type
        assert normalize_resource_type("agent") == "agent"
        assert normalize_resource_type("agents") == "agents"
    
    def test_normalize_workflow_aliases(self):
        from src.main import normalize_resource_type
        assert normalize_resource_type("workflow") == "workflow"
        assert normalize_resource_type("wf") == "workflow"
        assert normalize_resource_type("wfs") == "workflows"
    
    def test_normalize_workspace_aliases(self):
        from src.main import normalize_resource_type
        assert normalize_resource_type("workspace") == "workspace"
        assert normalize_resource_type("ws") == "workspace"


class TestAPIClient:
    """Test API client methods."""
    
    def test_client_initialization(self):
        from src.api_client import APIClient
        with patch('src.api_client.get_api_url', return_value='http://localhost:8000'):
            with patch('src.api_client.get_auth_token', return_value=None):
                client = APIClient()
                assert client.base_url == 'http://localhost:8000'
                assert client.timeout == 30.0
    
    def test_client_headers_without_auth(self):
        from src.api_client import APIClient
        with patch('src.api_client.get_api_url', return_value='http://localhost:8000'):
            with patch('src.api_client.get_auth_token', return_value=None):
                client = APIClient()
                headers = client._get_headers()
                assert "Authorization" not in headers
    
    def test_client_headers_with_auth(self):
        from src.api_client import APIClient
        with patch('src.api_client.get_api_url', return_value='http://localhost:8000'):
            with patch('src.api_client.get_auth_token', return_value='test-token'):
                client = APIClient()
                headers = client._get_headers()
                assert headers["Authorization"] == "Bearer test-token"


class TestConvenienceCommands:
    """Test top-level convenience commands."""
    
    def test_stats_help(self, runner):
        """Test stats command help."""
        from src.main import app
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "statistics" in result.stdout.lower()
    
    def test_config_help(self, runner):
        """Test config command help."""
        from src.main import app
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "configuration" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
