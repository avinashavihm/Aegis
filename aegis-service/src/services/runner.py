"""
Agent Runner Service - Executes agents and workflows using the Aegis framework
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID

from src.database import get_db_connection
from src.config import settings

# Import Aegis framework components
from src.aegis import Aegis, Agent, Response, Result
from src.aegis.environment.file_env import FileEnv
from src.aegis.environment.web_env import WebEnv
from src.aegis.environment.local_env import LocalEnv
from src.aegis.workflows.workflow_engine import WorkflowEngine
from src.services.tool_registry import (
    tool_registry,
    ToolDefinition,
    ToolParameter,
    ToolCategory,
)
from src.services.custom_tools import custom_tool_service
from src.services.mcp_client import mcp_client
from src.services.file_service import file_service


class AgentRunner:
    """
    Service for executing agents and workflows.
    Bridges stored agent definitions with the Aegis execution engine.
    """
    
    def __init__(self):
        self.aegis = Aegis()
        self.workflow_engine = WorkflowEngine()
        
        # Initialize environments (framework expects workspace_name, not path)
        workspace_name = settings.workspace_dir or "workspace"
        self.file_env = FileEnv(workspace_name=workspace_name)
        self.web_env = WebEnv()
        self.code_env = LocalEnv(workspace_name=workspace_name)
    
    def _register_mcp_tools(self, user_id: str, agent_id: Optional[str]) -> List[str]:
        """
        Register MCP tools for an agent and return their names.
        """
        if not agent_id:
            return []

        tool_names: List[str] = []
        # Fetch attached MCP servers
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.name, s.transport_type, s.endpoint_url, s.command, s.args, s.env_vars, s.config
                    FROM agent_mcp_servers am
                    JOIN mcp_servers s ON am.mcp_server_id = s.id
                    WHERE am.agent_id = %s
                    """,
                    (str(agent_id),),
                )
                servers = [dict(r) for r in cur.fetchall()]

        for server in servers:
            tools = mcp_client.list_tools_from_server(server)
            for t in tools:
                mcp_tool_name = f"mcp:{server.get('name', server.get('id'))}:{t.get('name')}"
                # Create wrapper that will be executed by MCP client (placeholder)
                def make_wrapper(tool_def: Dict[str, Any], server_def: Dict[str, Any]) -> Callable:
                    def wrapper(**kwargs):
                        return {
                            "status": "mcp_call_stub",
                            "tool": tool_def.get("name"),
                            "server": server_def.get("name"),
                            "args": kwargs,
                            "message": "MCP execution stub. Implement actual MCP invocation.",
                        }

                    wrapper.__name__ = mcp_tool_name
                    return wrapper

                tool_registry.register(
                    ToolDefinition(
                        name=mcp_tool_name,
                        description=t.get("description", "MCP tool"),
                        category=ToolCategory.MCP,
                        function=make_wrapper(t, server),
                        parameters=[
                            ToolParameter(
                                name=p.get("name", "arg"),
                                type=p.get("type", "string"),
                                description=p.get("description", ""),
                                required=p.get("required", True),
                                default=p.get("default"),
                            )
                            for p in t.get("parameters", [])
                        ],
                        return_type=t.get("return_type", "any"),
                        source="mcp",
                        metadata={"server_id": str(server.get("id"))},
                    )
                )
                tool_names.append(mcp_tool_name)

        return tool_names

    def _load_agent_files(self, user_id: str, agent_id: Optional[str]) -> List[Dict[str, Any]]:
        """
        Load file metadata and small content snippets for agent context.
        """
        if not agent_id:
            return []

        files = file_service.list_files(user_id, str(agent_id))
        enriched = []
        for f in files:
            entry = dict(f)
            path = f.get("file_path")
            if path and os.path.exists(path):
                try:
                    with open(path, "rb") as handle:
                        content = handle.read(20000)
                        entry["content_preview"] = content.decode(errors="ignore")
                except Exception:
                    entry["content_preview"] = None
            enriched.append(entry)
        return enriched

    def get_tool_functions(
        self,
        tool_names: List[str],
        user_id: Optional[str] = None,
        custom_tool_ids: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
    ) -> List:
        """
        Get callable tool functions for the specified tool names, including custom and MCP tools.
        """
        functions = []
        resolved_names = []
        unresolved = []

        # Ensure custom tools are loaded into registry
        if user_id:
            custom_tool_service.load_all_custom_tools(user_id)
            if custom_tool_ids:
                for ct_id in custom_tool_ids:
                    tool_record = custom_tool_service.get_tool(user_id, str(ct_id))
                    if tool_record:
                        custom_tool_service._register_in_registry(tool_record)

        # Register MCP tools for this agent
        mcp_tool_names = self._register_mcp_tools(user_id, agent_id)
        combined_tool_names = list(set(tool_names + mcp_tool_names))

        # Resolve functions from registry (with alias support)
        for name in combined_tool_names:
            func = tool_registry.get_function(name)
            if func:
                functions.append(func)
                # Track resolved name (may be different due to alias)
                resolved = tool_registry.resolve_name(name)
                resolved_names.append(resolved if resolved != name else name)
            else:
                unresolved.append(name)
        
        # Log unresolved tools as warnings
        if unresolved:
            print(f"[Tool Warning] Could not resolve tools: {unresolved}")
            print(f"[Tool Warning] Available tools: {tool_registry.get_tool_names()[:20]}...")

        return functions
    
    def build_agent(self, agent_data: Dict[str, Any], user_id: Optional[str] = None) -> Agent:
        """
        Build an Aegis Agent from stored agent definition.
        """
        tools = agent_data.get('tools') or tool_registry.get_tool_names()
        custom_tool_ids = agent_data.get('custom_tool_ids') or []
        tool_choice = agent_data.get('tool_choice') or "auto"
        parallel_flag = agent_data.get('parallel_tool_calls')
        if parallel_flag is None:
            parallel_flag = True
        autonomous_flag = agent_data.get('autonomous_mode')
        if autonomous_flag is None:
            autonomous_flag = True
        metadata = agent_data.get('metadata', {}) or {}
        metadata.setdefault('profile', 'premium')
        functions = self.get_tool_functions(
            tools,
            user_id=user_id,
            custom_tool_ids=custom_tool_ids,
            agent_id=str(agent_data.get('id') or agent_data.get('agent_id') or '')
        )
        
        # Log tool resolution for debugging
        print(f"[Agent Build] {agent_data['name']}: {len(functions)} tools loaded from {len(tools)} requested")
        print(f"[Agent Build] Tools requested: {tools[:10]}{'...' if len(tools) > 10 else ''}")
        print(f"[Agent Build] Functions resolved: {[f.__name__ for f in functions[:10]]}{'...' if len(functions) > 10 else ''}")
        
        # Enhance instructions if they're too basic and agent has tools
        instructions = agent_data.get('instructions', 'You are a helpful agent.')
        if functions and len(instructions) < 500:
            # Agent has tools but minimal instructions - add comprehensive tool guidance
            tool_names = [f.__name__ for f in functions]
            tool_guidance = f"""

═══════════════════════════════════════════════════════════════
CRITICAL SYSTEM INSTRUCTIONS - READ CAREFULLY
═══════════════════════════════════════════════════════════════

You have REAL, WORKING tools available: {', '.join(tool_names)}

🔴 MANDATORY BEHAVIORS:

1. **USE TOOLS FIRST, TALK SECOND**
   - When asked to search/find/research → USE search_web IMMEDIATELY
   - When given a URL → USE fetch_url to get content
   - Don't describe what you "would" do - ACTUALLY DO IT
   - Example: "Find flights" → search_web("flights from X to Y [dates]")

2. **NEVER SAY "I CAN'T" IF YOU HAVE RELEVANT TOOLS**
   - Wrong: "I can't book tickets directly"
   - Right: Use search_web to find booking options, then provide links
   
3. **REMEMBER THE CONVERSATION**
   - Track all information the user has provided
   - Don't ask for info they already gave you
   - Build on previous answers

4. **BE SPECIFIC AND ACTIONABLE**
   - Wrong: "There are many options..."
   - Right: "Here are 3 specific options I found: [results from search]"

5. **TOOL USAGE PATTERN**
   - Step 1: Identify what information is needed
   - Step 2: Call search_web with specific queries
   - Step 3: Call fetch_url to get details from results
   - Step 4: Present organized findings

Example good behavior:
User: "Plan a trip to Paris"
You: "I'll search for Paris trip options..." → [call search_web] → Present results

═══════════════════════════════════════════════════════════════
"""
            instructions = instructions + tool_guidance
        
        return Agent(
            name=agent_data['name'],
            model=agent_data.get('model', settings.completion_model),
            instructions=instructions,
            functions=functions,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_flag,
            autonomous_mode=autonomous_flag,
            metadata=metadata,
            tags=agent_data.get('tags', [])
        )
    
    def build_context_variables(self, user_context: Dict[str, Any] = None, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Build context variables with environments injected.
        """
        context = user_context.copy() if user_context else {}
        
        # Inject environments
        context['file_env'] = self.file_env
        context['web_env'] = self.web_env
        context['code_env'] = self.code_env

        # Attach agent files for context
        context['agent_files'] = self._load_agent_files(user_id, agent_id)
        
        return context
    
    def _build_conversation_messages(self, input_message: str, context_variables: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """
        Build conversation messages from context, supporting multi-turn conversations.
        """
        messages = []
        
        if context_variables:
            # Check for previous_messages (array of {role, content})
            prev_messages = context_variables.get('previous_messages')
            if prev_messages and isinstance(prev_messages, list):
                for msg in prev_messages:
                    if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                        role = 'user' if msg['role'] == 'user' else 'assistant'
                        messages.append({"role": role, "content": msg['content']})
                # Add the new user message only if it's not already the last message
                if not messages or messages[-1].get('content') != input_message:
                    messages.append({"role": "user", "content": input_message})
                return messages
            
            # Check for conversation_history (string format)
            conv_history = context_variables.get('conversation_history')
            if conv_history and isinstance(conv_history, str):
                # Parse conversation history string
                # Format: "User: message\n\nAssistant: response\n\nUser: message"
                parts = conv_history.split('\n\n')
                for part in parts:
                    part = part.strip()
                    if part.startswith('User:'):
                        content = part[5:].strip()
                        if content:
                            messages.append({"role": "user", "content": content})
                    elif part.startswith('Assistant:'):
                        content = part[10:].strip()
                        if content:
                            messages.append({"role": "assistant", "content": content})
                # Add the new user message if not already present
                if not messages or messages[-1].get('content') != input_message:
                    messages.append({"role": "user", "content": input_message})
                return messages
        
        # Default: single user message
        return [{"role": "user", "content": input_message}]
    
    def update_run_status(
        self,
        run_id: UUID,
        user_id: str,
        status: str,
        output: str = None,
        error: str = None,
        messages: List = None,
        tool_calls: List = None,
        step_results: List = None,
        tokens_used: int = 0,
        started_at: datetime = None,
        completed_at: datetime = None
    ):
        """
        Update a run record with execution results.
        """
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                update_fields = ["status = %s"]
                params = [status]
                
                if output is not None:
                    update_fields.append("output = %s")
                    params.append(output)
                
                if error is not None:
                    update_fields.append("error = %s")
                    params.append(error)
                
                if messages is not None:
                    update_fields.append("messages = %s")
                    params.append(json.dumps(messages))
                
                if tool_calls is not None:
                    update_fields.append("tool_calls = %s")
                    params.append(json.dumps(tool_calls))
                
                if step_results is not None:
                    update_fields.append("step_results = %s")
                    params.append(json.dumps(step_results))
                
                if tokens_used > 0:
                    update_fields.append("tokens_used = %s")
                    params.append(tokens_used)
                
                if started_at:
                    update_fields.append("started_at = %s")
                    params.append(started_at)
                
                if completed_at:
                    update_fields.append("completed_at = %s")
                    params.append(completed_at)
                
                params.append(str(run_id))
                
                cur.execute(
                    f"""
                    UPDATE agent_runs
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                    """,
                    params
                )
                conn.commit()
    
    async def execute_agent(
        self,
        run_id: UUID,
        agent_data: Dict[str, Any],
        input_message: str,
        context_variables: Dict[str, Any] = None,
        model_override: str = None,
        max_turns: int = 10,
        user_id: str = None
    ):
        """
        Execute an agent with the given input.
        This is called as a background task.
        """
        started_at = datetime.utcnow()
        
        # Update status to running
        self.update_run_status(
            run_id=run_id,
            user_id=user_id,
            status='running',
            started_at=started_at
        )
        
        try:
            # Build the agent
            agent = self.build_agent(agent_data, user_id=user_id)
            
            # Build context with environments and agent files
            context = self.build_context_variables(
                context_variables,
                user_id=user_id,
                agent_id=str(agent_data.get('id') or agent_data.get('agent_id') or '')
            )
            
            # Build messages - support multi-turn conversation
            messages = self._build_conversation_messages(input_message, context_variables)
            print(f"[Receive Task] Receiving the task: {input_message}")
            print(f"[Conversation] Total messages in context: {len(messages)}")
            
            # Run the agent
            response: Response = self.aegis.run(
                agent=agent,
                messages=messages,
                context_variables=context,
                model_override=model_override or agent_data.get('model'),
                stream=False,
                debug=settings.aegis_debug,
                max_turns=min(max_turns, settings.max_agent_turns)
            )
            
            # Extract results
            output_messages = response.messages
            
            # Get the final assistant message as output
            output = None
            for msg in reversed(output_messages):
                if msg.get('role') == 'assistant' and msg.get('content'):
                    output = msg['content']
                    break
            
            # Extract tool calls for logging
            tool_calls_log = []
            for msg in output_messages:
                if msg.get('role') == 'tool':
                    tool_calls_log.append({
                        'name': msg.get('name'),
                        'result': msg.get('content', '')[:500]  # Truncate long results
                    })
            
            # Serialize messages for storage (convert to JSON-safe format)
            serialized_messages = []
            for msg in output_messages:
                serialized_msg = {
                    'role': msg.get('role'),
                    'content': msg.get('content')
                }
                if msg.get('name'):
                    serialized_msg['name'] = msg['name']
                if msg.get('tool_call_id'):
                    serialized_msg['tool_call_id'] = msg['tool_call_id']
                serialized_messages.append(serialized_msg)
            
            completed_at = datetime.utcnow()
            
            # Update run with results
            self.update_run_status(
                run_id=run_id,
                user_id=user_id,
                status='completed',
                output=output,
                messages=serialized_messages,
                tool_calls=tool_calls_log,
                completed_at=completed_at
            )
            
        except Exception as e:
            completed_at = datetime.utcnow()
            
            # Update run with error
            self.update_run_status(
                run_id=run_id,
                user_id=user_id,
                status='failed',
                error=str(e),
                completed_at=completed_at
            )
    
    async def execute_workflow(
        self,
        run_id: UUID,
        workflow_data: Dict[str, Any],
        agents_data: Dict[str, Dict[str, Any]],
        input_message: str,
        context_variables: Dict[str, Any] = None,
        model_override: str = None,
        max_turns: int = 10,
        user_id: str = None
    ):
        """
        Execute a workflow with the given input.
        This is called as a background task.
        """
        started_at = datetime.utcnow()
        
        # Update status to running
        self.update_run_status(
            run_id=run_id,
            user_id=user_id,
            status='running',
            started_at=started_at
        )
        
        try:
            steps = workflow_data.get('steps') or []
            execution_mode = workflow_data.get('execution_mode', 'sequential')
            
            # Build context with environments
            context = self.build_context_variables(context_variables, user_id=user_id)
            context['input_message'] = input_message
            context['workflow_results'] = {}
            
            step_results = []
            all_messages = []
            all_tool_calls = []
            final_output = None
            
            if execution_mode == 'sequential':
                # Execute steps sequentially
                for step in steps:
                    step_id = step.get('step_id', str(len(step_results) + 1))
                    agent_id = step.get('agent_id')
                    
                    step_result = {
                        'step_id': step_id,
                        'status': 'pending',
                        'output': None,
                        'error': None,
                        'started_at': None,
                        'completed_at': None
                    }
                    
                    if not agent_id or agent_id not in agents_data:
                        step_result['status'] = 'failed'
                        step_result['error'] = f"Agent {agent_id} not found"
                        step_results.append(step_result)
                        continue
                    
                    agent_data = agents_data[agent_id]
                    
                    if agent_data.get('status') != 'active':
                        step_result['status'] = 'failed'
                        step_result['error'] = f"Agent is not active"
                        step_results.append(step_result)
                        continue
                    
                    step_result['started_at'] = datetime.utcnow().isoformat()
                    
                    try:
                        # Build the agent for this step
                        agent = self.build_agent(agent_data, user_id=user_id)
                        
                        # Apply input mapping
                        step_input = input_message
                        input_mapping = step.get('input_mapping', {})
                        if input_mapping:
                            # Build input from previous results
                            mapped_parts = []
                            for key, source in input_mapping.items():
                                if source in context.get('workflow_results', {}):
                                    mapped_parts.append(f"{key}: {context['workflow_results'][source]}")
                            if mapped_parts:
                                step_input = "\n".join(mapped_parts)
                        
                        # Prepare messages for this step
                        messages = [{"role": "user", "content": step_input}]
                        
                        # Run the agent
                        response: Response = self.aegis.run(
                            agent=agent,
                            messages=messages,
                            context_variables=context,
                            model_override=model_override or agent_data.get('model'),
                            stream=False,
                            debug=settings.aegis_debug,
                            max_turns=min(max_turns, settings.max_agent_turns)
                        )
                        
                        # Extract output
                        step_output = None
                        for msg in reversed(response.messages):
                            if msg.get('role') == 'assistant' and msg.get('content'):
                                step_output = msg['content']
                                break
                        
                        # Store result for next steps
                        output_key = step.get('output_key', step_id)
                        context['workflow_results'][output_key] = step_output
                        
                        # Collect messages and tool calls
                        for msg in response.messages:
                            serialized_msg = {
                                'step_id': step_id,
                                'role': msg.get('role'),
                                'content': msg.get('content')
                            }
                            if msg.get('name'):
                                serialized_msg['name'] = msg['name']
                            all_messages.append(serialized_msg)
                            
                            if msg.get('role') == 'tool':
                                all_tool_calls.append({
                                    'step_id': step_id,
                                    'name': msg.get('name'),
                                    'result': msg.get('content', '')[:500]
                                })
                        
                        step_result['status'] = 'completed'
                        step_result['output'] = step_output
                        step_result['completed_at'] = datetime.utcnow().isoformat()
                        
                        # Keep track of final output (last step's output)
                        final_output = step_output
                        
                    except Exception as e:
                        step_result['status'] = 'failed'
                        step_result['error'] = str(e)
                        step_result['completed_at'] = datetime.utcnow().isoformat()
                    
                    step_results.append(step_result)
                    
                    # Update progress
                    self.update_run_status(
                        run_id=run_id,
                        user_id=user_id,
                        status='running',
                        step_results=step_results
                    )
                    
                    # Stop if step failed
                    if step_result['status'] == 'failed':
                        break
            
            else:  # parallel execution
                # For parallel execution, we'd use asyncio.gather
                # For now, execute sequentially as a simple implementation
                # TODO: Implement true parallel execution
                pass
            
            completed_at = datetime.utcnow()
            
            # Determine final status
            failed_steps = [s for s in step_results if s['status'] == 'failed']
            final_status = 'failed' if failed_steps else 'completed'
            final_error = failed_steps[0]['error'] if failed_steps else None
            
            # Update run with results
            self.update_run_status(
                run_id=run_id,
                user_id=user_id,
                status=final_status,
                output=final_output,
                error=final_error,
                messages=all_messages,
                tool_calls=all_tool_calls,
                step_results=step_results,
                completed_at=completed_at
            )
            
        except Exception as e:
            completed_at = datetime.utcnow()
            
            # Update run with error
            self.update_run_status(
                run_id=run_id,
                user_id=user_id,
                status='failed',
                error=str(e),
                completed_at=completed_at
            )
