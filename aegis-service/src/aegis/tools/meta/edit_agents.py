"""
Meta tools for agent management

Includes tools for:
- Basic agent CRUD operations
- Superior multi-file agent generation 
- Sandbox execution
- Package download
"""

import json
import os
import difflib
import time
import base64
from aegis.registry import register_tool, registry
from aegis.environment.local_env import LocalEnv
from typing import Union, List, Optional, Dict, Any


def get_workspace_path(env: LocalEnv) -> str:
    """Get the workspace path"""
    return env.local_root


def get_aegis_project_root() -> str:
    """Get the Aegis project root directory (where aegis module is located)"""
    # Get the directory of this file (aegis/tools/meta/edit_agents.py)
    current_file = os.path.abspath(__file__)
    # Go up: meta -> tools -> aegis -> project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    return project_root


@register_tool("list_agents")
def list_agents(context_variables: dict = None) -> str:
    """
    List all plugin agents in Aegis.
    
    Returns:
        A JSON string with information about all plugin agents.
    """
    try:
        # First, load agents from workspace directory
        env = context_variables.get("code_env") if context_variables else None
        if env is None:
            from aegis.environment.local_env import LocalEnv
            env = LocalEnv()
        
        workspace_path = get_workspace_path(env)
        agents_dir = os.path.join(workspace_path, "agents")
        
        # Dynamically import all agent files from workspace
        if os.path.exists(agents_dir):
            import importlib.util
            import sys
            
            for filename in os.listdir(agents_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = f"workspace_agent_{filename[:-3]}"
                    file_path = os.path.join(agents_dir, filename)
                    
                    # Only import if not already imported
                    if module_name not in sys.modules:
                        try:
                            spec = importlib.util.spec_from_file_location(module_name, file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                # Add project root to path so imports work
                                project_root = get_aegis_project_root()
                                if project_root not in sys.path:
                                    sys.path.insert(0, project_root)
                                spec.loader.exec_module(module)
                        except Exception as e:
                            # Silently skip files that can't be imported
                            pass
        
        # Now get the agents info
        agents_info = registry.display_plugin_agents_info
        if not agents_info:
            return json.dumps({}, indent=2)
        return json.dumps(agents_info, indent=2)
    except Exception as e:
        return f"[ERROR] Failed to list agents. Error: {str(e)}"


@register_tool("create_agent")
def create_agent(
    agent_name: str,
    agent_description: str,
    agent_tools: list[str],
    agent_instructions: str,
    context_variables: dict = None
) -> str:
    """
    Create a new agent or modify an existing agent.
    
    Args:
        agent_name: The name of the agent.
        agent_description: The description of the agent.
        agent_tools: The tools the agent can use (list of tool names).
        agent_instructions: The system instructions for the agent.
    """
    env: LocalEnv = context_variables.get("code_env") if context_variables else LocalEnv()
    workspace_path = get_workspace_path(env)
    agents_dir = os.path.join(workspace_path, "agents")
    os.makedirs(agents_dir, exist_ok=True)
    
    # Build tool imports - import all tools on one line
    if agent_tools:
        tools_str = "from aegis.tools import " + ", ".join(agent_tools) + "\n"
    else:
        tools_str = ""
    
    agent_func = f"get_{agent_name.lower().replace(' ', '_')}"
    # Create tool list string like AutoAgent: "[read_file, write_file]"
    tool_list = "[{}]".format(', '.join(f'{tool}' for tool in agent_tools))
    
    # Create agent code
    agent_code = f"""from aegis.registry import register_plugin_agent
from aegis.types import Agent
{tools_str}
from aegis.tools.inner import case_resolved, case_not_resolved

@register_plugin_agent(name="{agent_name}", func_name="{agent_func}")
def {agent_func}(model: str):
    '''
    {agent_description}
    '''
    instructions = {repr(agent_instructions)}
    
    tools = {tool_list} + [case_resolved, case_not_resolved]
    
    return Agent(
        name="{agent_name}",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False
    )
"""
    
    agent_file = os.path.join(agents_dir, f"{agent_name.lower().replace(' ', '_')}.py")
    
    try:
        result = env.create_file(agent_file.replace(workspace_path + "/", ""), agent_code)
        if result.get("status") != 0:
            return f"[ERROR] Failed to create agent. Error: {result.get('message', 'Unknown error')}"
        
        # Validate by running the agent file from project root (like AutoAgent does)
        project_root = get_aegis_project_root()
        # Get relative path from project root to agent file
        try:
            rel_agent_path = os.path.relpath(agent_file, project_root)
        except ValueError:
            # If agent_file is not relative to project_root, use absolute path
            rel_agent_path = agent_file
        
        try:
            # Run from project root with PYTHONPATH set so aegis can be imported
            # This matches AutoAgent's approach: run from project root where aegis module is
            pythonpath = f"{project_root}:{os.environ.get('PYTHONPATH', '')}"
            command = f'PYTHONPATH={pythonpath} python {rel_agent_path}'
            result = env.run_command(command, cwd=project_root)
            if result.get("status") != 0:
                error_msg = result.get("result", result.get("message", "Unknown error"))
                # Clean up error message - show just the relevant part
                if "ModuleNotFoundError" in error_msg:
                    # Extract just the error message
                    lines = error_msg.split('\n')
                    for line in lines:
                        if "ModuleNotFoundError" in line or "No module named" in line:
                            error_msg = line.strip()
                            break
                return f"[WARNING] Agent file created but validation failed: {error_msg}. File: {agent_file}"
            
            # Import the agent file to register it
            try:
                import importlib.util
                import sys
                module_name = f"workspace_agent_{agent_name.lower().replace(' ', '_')}"
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                spec = importlib.util.spec_from_file_location(module_name, agent_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except Exception as import_error:
                # Import failed, but file was created successfully
                return f"[SUCCESS] Successfully created agent: {agent_name} in {agent_file} (Note: Agent will be loaded when list_agents is called)"
            
            return f"[SUCCESS] Successfully created agent: {agent_name} in {agent_file}"
        except Exception as e:
            return f"[WARNING] Agent file created but validation failed: {str(e)}. File: {agent_file}"
    except Exception as e:
        return f"[ERROR] Failed to create agent. Error: {str(e)}"


@register_tool("delete_agent")
def delete_agent(agent_name: str, context_variables: dict = None) -> str:
    """
    Delete a plugin agent.
    
    Args:
        agent_name: The name of the agent to delete.
    """
    try:
        agents_info = json.loads(list_agents(context_variables))
        if not isinstance(agents_info, dict):
            return f"[ERROR] Failed to parse agent registry. Result: {agents_info}"
        
        def _normalize(name: str) -> str:
            return name.lower().replace(" ", "_")
        
        normalized_map = {_normalize(name): name for name in agents_info.keys()}
        target_key = _normalize(agent_name)
        resolved_name = None
        auto_messages = []
        
        if target_key in normalized_map:
            resolved_name = normalized_map[target_key]
        else:
            candidates = difflib.get_close_matches(target_key, normalized_map.keys(), n=1, cutoff=0.6)
            if candidates:
                resolved_name = normalized_map[candidates[0]]
                auto_messages.append(
                    f"[AUTO-FIX] Requested agent '{agent_name}' not found. Using closest match '{resolved_name}'."
                )
            else:
                suggestion_keys = difflib.get_close_matches(target_key, normalized_map.keys(), n=3, cutoff=0.1)
                suggestions = [normalized_map[key] for key in suggestion_keys]
                if suggestions:
                    suggestion_text = f" Did you mean: {', '.join(suggestions)}?"
                else:
                    suggestion_text = f" Available agents: {', '.join(agents_info.keys())}"
                return f"[ERROR] The agent '{agent_name}' does not exist.{suggestion_text}"
        
        agent_info = agents_info[resolved_name]
        agent_path = agent_info.get('file_path', '')
        
        if agent_path and os.path.exists(agent_path):
            os.remove(agent_path)
            return f"[SUCCESS] Successfully deleted agent: {agent_name}"
        else:
            return f"[ERROR] Agent file not found: {agent_path}"
    except Exception as e:
        return f"[ERROR] Failed to delete agent. Error: {str(e)}"


@register_tool("run_agent")
def run_agent(
    agent_name: str,
    query: str,
    model: str = None,
    context_variables: dict = None
) -> str:
    """
    Run a plugin agent.
    
    Args:
        agent_name: The name of the agent to run.
        query: The query/task for the agent.
        model: The model to use (optional, uses default from config if not provided).
               If the specified model is not available, the default model will be used instead.
    """
    from aegis.config import COMPLETION_MODEL
    from aegis import Aegis
    from aegis.agents.system.system_triage_agent import get_system_triage_agent
    try:
        from litellm import RateLimitError
    except Exception:  # pragma: no cover - fallback if litellm signature changes
        class RateLimitError(Exception):
            """Fallback RateLimitError when litellm is unavailable."""
            pass
    
    # Always use the default model from config to ensure compatibility with available API keys
    # Ignore the model parameter to prevent API key mismatches
    model = COMPLETION_MODEL
    
    try:
        agents_info = json.loads(list_agents(context_variables))
        if not isinstance(agents_info, dict):
            return f"[ERROR] Failed to parse agent registry. Result: {agents_info}"
        
        def _normalize(name: str) -> str:
            return name.lower().replace(" ", "_")
        
        normalized_map = {_normalize(name): name for name in agents_info.keys()}
        target_key = _normalize(agent_name)
        resolved_name = None
        auto_messages = []
        
        if target_key in normalized_map:
            resolved_name = normalized_map[target_key]
        else:
            candidates = difflib.get_close_matches(target_key, normalized_map.keys(), n=1, cutoff=0.6)
            if candidates:
                resolved_name = normalized_map[candidates[0]]
                auto_messages.append(
                    f"[AUTO-FIX] Requested agent '{agent_name}' not found. Using closest match '{resolved_name}'."
                )
            else:
                suggestion_keys = difflib.get_close_matches(target_key, normalized_map.keys(), n=3, cutoff=0.1)
                suggestions = [normalized_map[key] for key in suggestion_keys]
                if suggestions:
                    suggestion_text = f" Did you mean: {', '.join(suggestions)}?"
                else:
                    suggestion_text = f" Available agents: {', '.join(agents_info.keys())}"
                return f"[ERROR] The agent '{agent_name}' does not exist.{suggestion_text}"
        
        agent_info = agents_info[resolved_name]
        func_name = agent_info.get('func_name', '')
        
        # Get the agent function from registry
        if func_name in registry.plugin_agents:
            agent_func = registry.plugin_agents[func_name]
            agent = agent_func(model)
            
            aegis = Aegis()
            messages = [{"role": "user", "content": query}]
            gemini_key_pool = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
            
            def rotate_gemini_key() -> bool:
                if len(gemini_key_pool) <= 1:
                    return False
                current_key = os.getenv("GEMINI_API_KEY")
                try:
                    current_index = gemini_key_pool.index(current_key)
                except ValueError:
                    current_index = -1
                next_index = (current_index + 1) % len(gemini_key_pool)
                if next_index == current_index:
                    return False
                os.environ["GEMINI_API_KEY"] = gemini_key_pool[next_index]
                auto_messages.append(
                    f"[AUTO-FIX] Gemini quota reached. Switching to alternate key ({next_index + 1}/{len(gemini_key_pool)})."
                )
                return True
            
            def execute_with_retries(agent_to_run, agent_label):
                retry_attempts = 3
                last_error = None
                for attempt in range(1, retry_attempts + 1):
                    try:
                        response = aegis.run(agent_to_run, messages, context_variables or {}, debug=False)
                        return response, agent_label
                    except RateLimitError as rl_err:
                        last_error = rl_err
                        rotated = rotate_gemini_key()
                        if rotated:
                            continue
                        wait_time = min(30, max(10, 5 * attempt))
                        auto_messages.append(
                            f"[AUTO-FIX] Rate limit encountered (attempt {attempt}/{retry_attempts}). Waiting {wait_time}s before retrying."
                        )
                        time.sleep(wait_time)
                if last_error:
                    raise last_error
            
            try:
                response, active_agent_name = execute_with_retries(agent, resolved_name)
            except RateLimitError:
                auto_messages.append(
                    "[AUTO-FIX] Rate limit persists after retries. Delegating to the System Triage Agent."
                )
                try:
                    fallback_agent = get_system_triage_agent(model)
                    response, active_agent_name = execute_with_retries(fallback_agent, fallback_agent.name)
                    resolved_name = active_agent_name
                except RateLimitError:
                    return ("[ERROR] Gemini quota exhausted across all configured API keys. "
                            "Please wait for the quota window to reset or provide additional keys.")
                except Exception as fallback_error:
                    return (f"[ERROR] Fallback agent failed due to: {fallback_error}. "
                            "Please review the task or provide additional context.")
            except Exception as run_error:
                try:
                    fallback_agent = get_system_triage_agent(model)
                    auto_messages.append(
                        f"[AUTO-FIX] Primary agent '{resolved_name}' failed ({run_error}). Falling back to '{fallback_agent.name}'."
                    )
                    response, active_agent_name = execute_with_retries(fallback_agent, fallback_agent.name)
                    resolved_name = active_agent_name
                except Exception as fallback_error:
                    return (f"[ERROR] Failed to run agent '{resolved_name}'. Original error: {run_error}. "
                            f"Fallback agent also failed: {fallback_error}")
            
            # Extract final response - prioritize tool results from case_resolved/case_not_resolved
            if response.messages:
                import re
                
                # First, check for case_resolved or case_not_resolved tool results
                for msg in reversed(response.messages):
                    if msg.get("role") == "tool":
                        tool_name = msg.get("name", "")
                        content = msg.get("content", "")
                        
                        # Extract solution from case_resolved
                        if tool_name == "case_resolved" and content:
                            # Try to extract content from <solution> tags
                            solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                            if solution_match:
                                return solution_match.group(1).strip()
                            # Otherwise return the full result
                            result_match = re.search(r'result of the case resolution is: (.*?)(?:\.|$)', content, re.DOTALL)
                            if result_match:
                                result = result_match.group(1).strip()
                                # Check for solution tags in the result
                                solution_match = re.search(r'<solution>(.*?)</solution>', result, re.DOTALL)
                                if solution_match:
                                    return solution_match.group(1).strip()
                                return result
                            return content
                        
                        # Return case_not_resolved content (formatted nicely)
                        if tool_name == "case_not_resolved" and content:
                            # Extract the failure reason
                            reason_match = re.search(r'reason is: (.*?)(?:\. But|$)', content, re.DOTALL)
                            if reason_match:
                                reason = reason_match.group(1).strip()
                                # Extract takeaway if present
                                takeaway_match = re.search(r'gain some information: (.*?)(?:\.|$)', content, re.DOTALL)
                                if takeaway_match:
                                    takeaway = takeaway_match.group(1).strip()
                                    return f"Task not completed.\n\nReason: {reason}\n\nNote: {takeaway}"
                                else:
                                    return f"Task not completed.\n\nReason: {reason}"
                            return content
                
                # Second, look for the last assistant message with content
                for msg in reversed(response.messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content")
                        if content and content.strip() and content.strip() != "None":
                            # Try to extract solution from <solution> tags
                            solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                            if solution_match:
                                return solution_match.group(1).strip()
                            return content
                
                # Third, check for any tool results that might contain useful info
                for msg in reversed(response.messages):
                    if msg.get("role") == "tool":
                        content = msg.get("content", "")
                        if content and len(content) > 50:  # Only return substantial tool results
                            # Skip placeholder messages
                            if "PLACEHOLDER" not in content and "not perform real" not in content:
                                return content[:500]  # Return first 500 chars
                
                # Last resort: return summary of what happened
                tool_calls_made = []
                for msg in response.messages:
                    if msg.get("role") == "assistant" and msg.get("tool_calls"):
                        for tc in msg.get("tool_calls", []):
                            tool_name = tc.get("function", {}).get("name", "unknown")
                            if tool_name not in ["case_resolved", "case_not_resolved"]:
                                tool_calls_made.append(tool_name)
                
                if tool_calls_made:
                    content = f"[SUCCESS] Agent '{resolved_name}' executed tools: {', '.join(set(tool_calls_made))}. Check tool results above for details."
                else:
                    content = f"[SUCCESS] Agent '{resolved_name}' executed successfully. Check tool results above for details."
            else:
                content = f"[ERROR] Agent '{resolved_name}' executed but no response received."
            
            if auto_messages:
                auto_messages.append(content)
                content = "\n".join(auto_messages)
            return content
        else:
            return f"[ERROR] Agent function {func_name} not found in registry."
    except Exception as e:
        return f"[ERROR] Failed to run agent. Error: {str(e)}"


# =============================================================================
# SUPERIOR AGENT GENERATION TOOLS (Multi-file, Sandbox, Download)
# =============================================================================

@register_tool("create_superior_agent")
def create_superior_agent(
    description: str,
    project_name: str = None,
    project_type: str = "simple",
    tools: list = None,
    capabilities: list = None,
    model: str = None,
    context_variables: dict = None
) -> str:
    """
    Create a sophisticated multi-file agent project using AI.
    
    This generates production-ready agents with multiple interconnected files,
    
    Args:
        description: Detailed description of what the agent should do
        project_name: Name for the project (auto-generated if not provided)
        project_type: Type of project - simple, multi_agent, data_pipeline, 
                      web_automation, api_integration, research, code_assistant, workflow
        tools: List of aegis tools the agent should use (e.g., ['read_file', 'write_file'])
        capabilities: List of capabilities the agent should have
        model: LLM model to use for generation (default: gpt-4o)
    
    Returns:
        JSON string with generated project info and file list
    """
    try:
        from aegis.generator import AgentGenerator
        from aegis.generator.project_templates import AgentProjectType
        
        # Get workspace path
        env = context_variables.get("code_env") if context_variables else None
        if env is None:
            from aegis.environment.local_env import LocalEnv
            env = LocalEnv()
        
        workspace_path = get_workspace_path(env)
        agents_dir = os.path.join(workspace_path, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # Map project type string to enum
        type_map = {
            "simple": AgentProjectType.SIMPLE,
            "multi_agent": AgentProjectType.MULTI_AGENT,
            "data_pipeline": AgentProjectType.DATA_PIPELINE,
            "web_automation": AgentProjectType.WEB_AUTOMATION,
            "api_integration": AgentProjectType.API_INTEGRATION,
            "research": AgentProjectType.RESEARCH,
            "code_assistant": AgentProjectType.CODE_ASSISTANT,
            "workflow": AgentProjectType.WORKFLOW,
            "custom": AgentProjectType.CUSTOM,
        }
        
        agent_type = type_map.get(project_type.lower(), AgentProjectType.SIMPLE)
        
        # Create generator and generate project
        generator = AgentGenerator(model=model or "gpt-4o")
        
        project = generator.generate(
            description=description,
            project_name=project_name,
            project_type=agent_type,
            tools=tools,
            capabilities=capabilities,
            model_override=model
        )
        
        # Save project to workspace
        project_dir = generator.save_project(project, agents_dir)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully created superior agent project: {project.name}",
            "project_name": project.name,
            "project_type": project_type,
            "project_path": project_dir,
            "files_count": len(project.files),
            "files": [f.path for f in project.files],
            "dependencies": project.dependencies,
            "run_command": f"cd {project_dir} && python main.py 'your task here'",
            "interactive_command": f"cd {project_dir} && python main.py -i"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create superior agent: {str(e)}"
        }, indent=2)


@register_tool("run_agent_in_sandbox")
def run_agent_in_sandbox(
    project_name: str,
    task: str,
    sandbox_type: str = "local",
    timeout_seconds: int = 300,
    context_variables: dict = None
) -> str:
    """
    Run an agent project in an isolated sandbox environment.
    
    Args:
        project_name: Name of the agent project to run
        task: The task to execute
        sandbox_type: Type of sandbox - local, venv, docker, or e2b
        timeout_seconds: Maximum execution time
    
    Returns:
        JSON string with execution results
    """
    try:
        from aegis.generator import AgentSandbox, create_sandbox
        from aegis.generator.agent_sandbox import SandboxType, SandboxConfig
        
        # Get workspace path
        env = context_variables.get("code_env") if context_variables else None
        if env is None:
            from aegis.environment.local_env import LocalEnv
            env = LocalEnv()
        
        workspace_path = get_workspace_path(env)
        project_path = os.path.join(workspace_path, "agents", project_name)
        
        if not os.path.exists(project_path):
            return json.dumps({
                "success": False,
                "error": f"Project not found: {project_name}. Use create_superior_agent first."
            })
        
        # Map sandbox type
        type_map = {
            "local": SandboxType.LOCAL,
            "venv": SandboxType.VENV,
            "docker": SandboxType.DOCKER,
            "e2b": SandboxType.E2B,
        }
        
        sb_type = type_map.get(sandbox_type.lower(), SandboxType.LOCAL)
        
        # Read project files
        project_files = {}
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for filename in files:
                if not filename.startswith('.'):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, project_path)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            project_files[rel_path] = f.read()
                    except:
                        pass
        
        # Create and run sandbox
        config = SandboxConfig(
            sandbox_type=sb_type,
            timeout_seconds=timeout_seconds,
            auto_install_deps=True
        )
        
        output_lines = []
        def capture_output(line: str):
            output_lines.append(line)
        
        sandbox = create_sandbox(sb_type, config)
        
        try:
            # Create sandbox with project files
            sandbox.create(project_files)
            
            # Install dependencies
            install_result = sandbox.install_dependencies()
            if not install_result.success:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to install dependencies: {install_result.error}",
                    "stderr": install_result.stderr
                })
            
            # Run the agent
            result = sandbox.run(
                task=task,
                on_output=capture_output
            )
            
            return json.dumps({
                "success": result.success,
                "output": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time": result.execution_time,
                "sandbox_type": sandbox_type
            }, indent=2)
            
        finally:
            sandbox.cleanup()
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Sandbox execution failed: {str(e)}"
        }, indent=2)


@register_tool("download_agent_package")
def download_agent_package(
    project_name: str,
    output_format: str = "zip",
    include_docker: bool = False,
    context_variables: dict = None
) -> str:
    """
    Create a downloadable package from an agent project.
    
    The package can be downloaded and run anywhere without modification.
    
    Args:
        project_name: Name of the agent project to package
        output_format: Package format - zip or tar.gz
        include_docker: Include Dockerfile and docker-compose.yml
    
    Returns:
        JSON string with download information (base64 encoded package)
    """
    try:
        from aegis.generator import AgentPackager, AgentGenerator
        from aegis.generator.agent_generator import GeneratedProject, GeneratedFile
        
        # Get workspace path
        env = context_variables.get("code_env") if context_variables else None
        if env is None:
            from aegis.environment.local_env import LocalEnv
            env = LocalEnv()
        
        workspace_path = get_workspace_path(env)
        project_path = os.path.join(workspace_path, "agents", project_name)
        
        if not os.path.exists(project_path):
            return json.dumps({
                "success": False,
                "error": f"Project not found: {project_name}"
            })
        
        # Read project files
        files = []
        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.venv']
            
            for filename in filenames:
                if not filename.startswith('.'):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, project_path)
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            files.append(GeneratedFile(
                                path=rel_path,
                                content=content
                            ))
                    except:
                        pass
        
        # Create project object
        project = GeneratedProject(
            name=project_name,
            description=f"Agent project: {project_name}",
            project_type="custom",
            files=files,
            dependencies=["litellm", "python-dotenv"]
        )
        
        # Create packager and generate package
        packager = AgentPackager()
        
        try:
            if output_format.lower() == "tar.gz":
                package_info = packager.create_tar_gz(project)
            else:
                package_info = packager.create_zip(
                    project,
                    include_docker=include_docker,
                    include_venv_setup=True
                )
            
            return json.dumps({
                "success": True,
                "message": f"Package created successfully: {package_info.name}",
                "package_name": package_info.name,
                "format": package_info.format,
                "size_bytes": package_info.size_bytes,
                "file_count": package_info.file_count,
                "data_url": package_info.data_url,
                "download_instructions": (
                    f"The package is ready to download. "
                    f"Extract and run: cd {project_name} && bash setup.sh && python main.py -i"
                )
            }, indent=2)
            
        finally:
            packager.cleanup()
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create package: {str(e)}"
        }, indent=2)


@register_tool("list_agent_project_types")
def list_agent_project_types(context_variables: dict = None) -> str:
    """
    List available agent project types for superior agent generation.
    
    Returns:
        JSON string with available project types and their descriptions
    """
    types = {
        "simple": {
            "name": "Simple Agent",
            "description": "Basic single-purpose agent project",
            "use_case": "Simple tasks, quick automation"
        },
        "multi_agent": {
            "name": "Multi-Agent System",
            "description": "Multiple specialized agents with orchestration",
            "use_case": "Complex tasks requiring different expertise"
        },
        "data_pipeline": {
            "name": "Data Pipeline Agent",
            "description": "ETL and data processing pipelines",
            "use_case": "Data extraction, transformation, analysis"
        },
        "web_automation": {
            "name": "Web Automation Agent",
            "description": "Web scraping and browser automation",
            "use_case": "Web data collection, form automation"
        },
        "api_integration": {
            "name": "API Integration Agent",
            "description": "REST API integration and orchestration",
            "use_case": "External service integration, webhooks"
        },
        "research": {
            "name": "Research Agent",
            "description": "Research and analysis with web search",
            "use_case": "Information gathering, market research"
        },
        "code_assistant": {
            "name": "Code Assistant Agent",
            "description": "Code generation, review, and refactoring",
            "use_case": "Development assistance, code quality"
        },
        "workflow": {
            "name": "Workflow Agent",
            "description": "Workflow automation with stages",
            "use_case": "Business process automation"
        },
        "custom": {
            "name": "Custom Agent",
            "description": "Fully customizable agent project",
            "use_case": "Specialized requirements"
        }
    }
    
    return json.dumps({
        "available_types": types,
        "usage": "Use create_superior_agent with project_type parameter"
    }, indent=2)


@register_tool("get_agent_project_files")
def get_agent_project_files(
    project_name: str,
    context_variables: dict = None
) -> str:
    """
    Get the list of files in a generated agent project.
    
    Args:
        project_name: Name of the agent project
    
    Returns:
        JSON string with file list and structure
    """
    try:
        env = context_variables.get("code_env") if context_variables else None
        if env is None:
            from aegis.environment.local_env import LocalEnv
            env = LocalEnv()
        
        workspace_path = get_workspace_path(env)
        project_path = os.path.join(workspace_path, "agents", project_name)
        
        if not os.path.exists(project_path):
            return json.dumps({
                "success": False,
                "error": f"Project not found: {project_name}"
            })
        
        files = []
        structure = []
        
        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.venv']
            
            level = root.replace(project_path, '').count(os.sep)
            indent = '  ' * level
            folder_name = os.path.basename(root)
            structure.append(f"{indent}{folder_name}/")
            
            sub_indent = '  ' * (level + 1)
            for filename in filenames:
                if not filename.startswith('.'):
                    structure.append(f"{sub_indent}{filename}")
                    rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                    files.append(rel_path)
        
        return json.dumps({
            "success": True,
            "project_name": project_name,
            "project_path": project_path,
            "file_count": len(files),
            "files": files,
            "structure": "\n".join(structure)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

