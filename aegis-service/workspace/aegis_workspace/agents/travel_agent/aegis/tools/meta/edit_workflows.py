"""
Meta tools for workflow management
"""

import json
import os
from aegis.registry import register_tool, registry
from aegis.environment.local_env import LocalEnv


@register_tool("list_workflows")
def list_workflows(context_variables: dict = None) -> str:
    """
    List all workflows in Aegis.
    
    Returns:
        A JSON string with information about all workflows.
    """
    try:
        workflows_info = registry.display_workflows_info
        return json.dumps(workflows_info, indent=2)
    except Exception as e:
        return f"[ERROR] Failed to list workflows. Error: {str(e)}"


@register_tool("create_workflow")
def create_workflow(
    workflow_name: str,
    workflow_code: str,
    context_variables: dict = None
) -> str:
    """
    Create a new workflow.
    
    Args:
        workflow_name: The name of the workflow.
        workflow_code: The Python code for the workflow (must include @register_workflow decorator).
    """
    env: LocalEnv = context_variables.get("code_env") if context_variables else LocalEnv()
    workspace_path = env.local_root
    workflows_dir = os.path.join(workspace_path, "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    
    # Ensure the code includes the register decorator
    if "from aegis.registry import register_workflow" not in workflow_code:
        workflow_code = "from aegis.registry import register_workflow\n" + workflow_code
    
    workflow_file = os.path.join(workflows_dir, f"{workflow_name}.py")
    
    try:
        result = env.create_file(workflow_file.replace(workspace_path + "/", ""), workflow_code)
        if result.get("status") != 0:
            return f"[ERROR] Failed to create workflow. Error: {result.get('message', 'Unknown error')}"
        
        # Try to import the workflow to validate it
        import sys
        sys.path.insert(0, workflows_dir)
        try:
            __import__(workflow_name)
            return f"[SUCCESS] Successfully created workflow: {workflow_name} in {workflow_file}"
        except Exception as e:
            return f"[WARNING] Workflow file created but validation failed: {str(e)}. File: {workflow_file}"
    except Exception as e:
        return f"[ERROR] Failed to create workflow. Error: {str(e)}"


@register_tool("delete_workflow")
def delete_workflow(workflow_name: str, context_variables: dict = None) -> str:
    """
    Delete a workflow.
    
    Args:
        workflow_name: The name of the workflow to delete.
    """
    try:
        workflows_info = json.loads(list_workflows(context_variables))
        if workflow_name not in workflows_info:
            return f"[ERROR] The workflow {workflow_name} does not exist."
        
        workflow_info = workflows_info[workflow_name]
        workflow_path = workflow_info.get('file_path', '')
        
        if workflow_path and os.path.exists(workflow_path):
            os.remove(workflow_path)
            return f"[SUCCESS] Successfully deleted workflow: {workflow_name}"
        else:
            return f"[ERROR] Workflow file not found: {workflow_path}"
    except Exception as e:
        return f"[ERROR] Failed to delete workflow. Error: {str(e)}"

