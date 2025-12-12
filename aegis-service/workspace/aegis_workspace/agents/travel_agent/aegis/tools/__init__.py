"""Tools for Aegis agents"""

# Import core tools for easy access
from aegis.tools.file_tools import read_file, write_file, list_files, search_files

# Web tools - may fail if duckduckgo_search not installed
try:
    from aegis.tools.web_tools import fetch_url, search_web, extract_content, fetch_and_extract
except ImportError:
    fetch_url = search_web = extract_content = fetch_and_extract = None

from aegis.tools.code_tools import execute_python, execute_command, run_script
from aegis.tools.terminal_tools import run_command, list_directory
from aegis.tools.inner import (
    case_resolved, case_not_resolved,
    report_progress, get_task_status, verify_result,
    rollback_task, set_task_dependency, task_tracker
)

# Import autonomous tools
from aegis.tools.autonomous import (
    create_task_plan, add_subtask, set_dependencies,
    get_plan_status, execute_next_subtask, complete_plan,
    check_escalation_needed, create_escalation,
    resolve_escalation, list_escalations
)

# Import knowledge tools
from aegis.tools.knowledge import (
    create_connector, list_connectors, query_connector,
    search_knowledge, remove_connector, test_connector,
    get_connector_status
)

# Import store tools
from aegis.tools.meta.store_tools import (
    browse_store, search_store, get_agent_details,
    install_from_store, uninstall_from_store, 
    update_store_agent, list_installed_store_agents
)

__all__ = [
    # File tools
    'read_file', 'write_file', 'list_files', 'search_files',
    
    # Web tools
    'fetch_url', 'search_web', 'extract_content', 'fetch_and_extract',
    
    # Code tools
    'execute_python', 'execute_command', 'run_script',
    
    # Terminal tools
    'run_command', 'list_directory',
    
    # Case resolution and task tracking
    'case_resolved', 'case_not_resolved',
    'report_progress', 'get_task_status', 'verify_result',
    'rollback_task', 'set_task_dependency', 'task_tracker',
    
    # Autonomous planning tools
    'create_task_plan', 'add_subtask', 'set_dependencies',
    'get_plan_status', 'execute_next_subtask', 'complete_plan',
    
    # Escalation tools
    'check_escalation_needed', 'create_escalation',
    'resolve_escalation', 'list_escalations',
    
    # Knowledge connector tools
    'create_connector', 'list_connectors', 'query_connector',
    'search_knowledge', 'remove_connector', 'test_connector',
    'get_connector_status',
    
    # Agent store tools
    'browse_store', 'search_store', 'get_agent_details',
    'install_from_store', 'uninstall_from_store',
    'update_store_agent', 'list_installed_store_agents'
]
