"""
Core Aegis engine for agent orchestration
"""

import copy
import json
import inspect
import warnings
from collections import defaultdict
from typing import List, Callable, Union, Optional
from litellm import completion, acompletion
import litellm
from httpx import RemoteProtocolError, ConnectError
from litellm.exceptions import APIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from litellm.types.utils import Message as litellmMessage

from aegis.types import Agent, Response, Result
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message
from aegis.utils import function_to_json, debug_print, merge_chunk
from aegis.logger import AegisLogger, LoggerManager
from aegis.config import FN_CALL, API_BASE_URL, NOT_SUPPORT_SENDER, ADD_USER, NON_FN_CALL

# Suppress Pydantic serialization warnings for litellm Message objects
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

__CTX_VARS_NAME__ = "context_variables"
logger = LoggerManager.get_logger()


def should_retry_error(exception):
    """Check if error should be retried"""
    if isinstance(exception, (APIError, RemoteProtocolError, ConnectError)):
        return True
    error_msg = str(exception).lower()
    return any([
        "connection error" in error_msg,
        "server disconnected" in error_msg,
        "eof occurred" in error_msg,
        "timeout" in error_msg,
        "event loop is closed" in error_msg,
        "anthropicexception" in error_msg,
    ])


def convert_tools_to_description(tools: list[dict]) -> str:
    """Convert tools to text description for non-function calling models"""
    ret = ''
    for i, tool in enumerate(tools):
        assert tool['type'] == 'function'
        fn = tool['function']
        if i > 0:
            ret += '\n'
        ret += f"---- BEGIN FUNCTION #{i+1}: {fn['name']} ----\n"
        ret += f"Description: {fn['description']}\n"
        if 'parameters' in fn:
            ret += 'Parameters:\n'
            properties = fn['parameters'].get('properties', {})
            required_params = set(fn['parameters'].get('required', []))
            for j, (param_name, param_info) in enumerate(properties.items()):
                is_required = param_name in required_params
                param_status = 'required' if is_required else 'optional'
                param_type = param_info.get('type', 'string')
                desc = param_info.get('description', 'No description provided')
                if 'enum' in param_info:
                    enum_values = ', '.join(f'`{v}`' for v in param_info['enum'])
                    desc += f'\nAllowed values: [{enum_values}]'
                ret += f'  ({j+1}) {param_name} ({param_type}, {param_status}): {desc}\n'
        else:
            ret += 'No parameters are required for this function.\n'
        ret += f'---- END FUNCTION #{i+1} ----\n'
    return ret


SYSTEM_PROMPT_SUFFIX_TEMPLATE = """
You have access to the following functions:

{description}

If you choose to call a function, reply in the following format:
<function=function_name>
<parameter=param1>value1</parameter>
<parameter=param2>value2</parameter>
</function>
"""


def adapt_tools_for_gemini(tools):
    """Adapt tools for Gemini compatibility"""
    if tools is None:
        return None
    adapted_tools = []
    for tool in tools:
        adapted_tool = copy.deepcopy(tool)
        if "parameters" in adapted_tool["function"]:
            params = adapted_tool["function"]["parameters"]
            if params.get("type") == "object":
                if "properties" not in params or not params["properties"]:
                    params["properties"] = {
                        "dummy": {
                            "type": "string",
                            "description": "Dummy property for Gemini compatibility"
                        }
                    }
            if "properties" in params:
                for prop_name, prop in params["properties"].items():
                    if isinstance(prop, dict) and prop.get("type") == "object":
                        if "properties" not in prop or not prop["properties"]:
                            prop["properties"] = {
                                "dummy": {
                                    "type": "string",
                                    "description": "Dummy property for Gemini compatibility"
                                }
                            }
        adapted_tools.append(adapted_tool)
    return adapted_tools


class Aegis:
    """Main orchestration engine for Aegis"""
    
    def __init__(self, log_path: Union[str, None, AegisLogger] = None):
        """Initialize Aegis engine"""
        if isinstance(log_path, AegisLogger):
            self.logger = log_path
        else:
            self.logger = AegisLogger(log_path=log_path)
    
    def get_chat_completion(
        self,
        agent: Agent,
        history: List,
        context_variables: dict,
        model_override: str = None,
        stream: bool = False,
        debug: bool = False,
    ) -> Message:
        """Get chat completion from LLM"""
        context_variables = defaultdict(str, context_variables)
        
        # Get instructions
        instructions = (
            agent.instructions(context_variables)
            if callable(agent.instructions)
            else agent.instructions
        )
        
        # Add examples if provided
        if agent.examples:
            examples = agent.examples(context_variables) if callable(agent.examples) else agent.examples
            history = examples + history
        
        messages = [{"role": "system", "content": instructions}] + history
        
        # Convert functions to tools
        tools = [function_to_json(f) for f in agent.functions]
        
        # Hide context_variables from model
        for tool in tools:
            params = tool["function"]["parameters"]
            params["properties"].pop(__CTX_VARS_NAME__, None)
            if __CTX_VARS_NAME__ in params.get("required", []):
                params["required"].remove(__CTX_VARS_NAME__)
        
        create_model = model_override or agent.model
        
        # Adapt for Gemini
        if "gemini" in create_model.lower():
            tools = adapt_tools_for_gemini(tools)
        
        if FN_CALL:
            assert litellm.supports_function_calling(model=create_model) == True, \
                f"Model {create_model} does not support function calling, please set `FN_CALL=False`"
            
            create_params = {
                "model": create_model,
                "messages": messages,
                "tools": tools or None,
                "tool_choice": agent.tool_choice,
                "stream": stream,
            }
            
            # Remove sender field for models that don't support it
            NO_SENDER_MODE = False
            for not_sender_model in NOT_SUPPORT_SENDER:
                if not_sender_model in create_model:
                    NO_SENDER_MODE = True
                    break
            
            if NO_SENDER_MODE:
                messages = create_params["messages"]
                for message in messages:
                    if 'sender' in message:
                        del message['sender']
                create_params["messages"] = messages
            
            if tools and create_params['model'].startswith("gpt"):
                create_params["parallel_tool_calls"] = agent.parallel_tool_calls
            
            completion_response = completion(**create_params)
        else:
            # Non-function calling mode
            assert agent.tool_choice == "required", \
                f"Non-function calling mode MUST use tool_choice = 'required'"
            
            last_content = messages[-1]["content"]
            tools_description = convert_tools_to_description(tools)
            messages[-1]["content"] = last_content + "\n[IMPORTANT] You MUST use the tools provided to complete the task.\n" + \
                SYSTEM_PROMPT_SUFFIX_TEMPLATE.format(description=tools_description)
            
            # Remove sender field if needed
            NO_SENDER_MODE = False
            for not_sender_model in NOT_SUPPORT_SENDER:
                if not_sender_model in create_model:
                    NO_SENDER_MODE = True
                    break
            
            if NO_SENDER_MODE:
                for message in messages:
                    if 'sender' in message:
                        del message['sender']
            
            create_params = {
                "model": create_model,
                "messages": messages,
                "stream": stream,
            }
            if API_BASE_URL:
                create_params["base_url"] = API_BASE_URL
            
            completion_response = completion(**create_params)
            # Convert response to function calling format (simplified)
            last_message = [{"role": "assistant", "content": completion_response.choices[0].message.content}]
            # For now, we'll parse the response manually if needed
            # This is a simplified version - full implementation would parse <function=...> tags
            converted_tool_calls = None
            completion_response.choices[0].message = litellmMessage(
                content=last_message[0]["content"],
                role="assistant",
                tool_calls=converted_tool_calls
            )
        
        return completion_response
    
    def handle_function_result(self, result, debug: bool) -> Result:
        """Handle function execution result"""
        if isinstance(result, Result):
            return result
        elif isinstance(result, Agent):
            return Result(
                value=json.dumps({"assistant": result.name}),
                agent=result,
            )
        else:
            try:
                # Handle None, empty dict, empty list
                if result is None:
                    return Result(value="No result returned")
                elif isinstance(result, dict) and len(result) == 0:
                    return Result(value="Empty result")
                elif isinstance(result, list) and len(result) == 0:
                    return Result(value="Empty result")
                else:
                    result_str = str(result)
                    # If result is just "{}" or empty, provide better message
                    if result_str.strip() in ["{}", "[]", ""]:
                        return Result(value="Task completed (no output)")
                    return Result(value=result_str)
            except Exception as e:
                error_message = f"Failed to cast response to string: {result}. Error: {str(e)}"
                self.logger.error(error_message, title="Handle Function Result Error")
                raise TypeError(error_message)
    
    def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[Callable],
        context_variables: dict,
        debug: bool,
        handle_mm_func: Callable = None,
    ) -> Response:
        """Handle tool calls and execute functions"""
        function_map = {f.__name__: f for f in functions}
        partial_response = Response(
            messages=[],
            agent=None,
            context_variables={}
        )
        
        for tool_call in tool_calls:
            name = tool_call.function.name
            if name not in function_map:
                self.logger.warning(f"Tool {name} not found in function map", title="Tool Call Error")
                partial_response.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": f"Error: Tool {name} not found.",
                })
                continue
            
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}
            
            func = function_map[name]
            # Inject context_variables if function accepts it
            if __CTX_VARS_NAME__ in inspect.signature(func).parameters.keys():
                args[__CTX_VARS_NAME__] = context_variables
            
            try:
                raw_result = func(**args)
            except Exception as e:
                self.logger.error(f"Error executing {name}: {str(e)}", title="Tool Execution Error")
                partial_response.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": f"Error: {str(e)}",
                })
                continue
            
            result: Result = self.handle_function_result(raw_result, debug)
            
            partial_response.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": result.value,
            })
            
            self.logger.pretty_print_messages(partial_response.messages[-1])
            
            if result.image:
                assert handle_mm_func, f"handle_mm_func is not provided, but an image is returned"
                partial_response.messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": handle_mm_func(name, tool_call.function.arguments)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{result.image}"
                            }
                        }
                    ]
                })
            
            partial_response.context_variables.update(result.context_variables)
            if result.agent:
                partial_response.agent = result.agent
        
        return partial_response
    
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=10, max=180),
        retry=retry_if_exception_type((APIError, RemoteProtocolError, ConnectError)),
        before_sleep=lambda retry_state: print(f"Retrying... (attempt {retry_state.attempt_number})")
    )
    def run(
        self,
        agent: Agent,
        messages: List,
        context_variables: dict = {},
        model_override: str = None,
        stream: bool = False,
        debug: bool = True,
        max_turns: int = 10,  # Default max turns to prevent infinite loops and rate limits
        execute_tools: bool = True,
    ) -> Response:
        """Run agent with message history"""
        active_agent = agent
        enter_agent = agent
        context_variables = copy.copy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)
        
        self.logger.info("Receiving the task:", history[-1]['content'], title="Receive Task", color="green")
        
        # Safety: prevent infinite loops and rate limits - lowered to 10 turns
        actual_max_turns = min(max_turns, 10) if max_turns != float("inf") else 10
        
        # Track recent tool calls to detect loops
        recent_tool_calls = []  # Store last 5 tool call signatures
        MAX_RECENT_CALLS = 5
        tool_call_counts = {}  # Count how many times each tool has been called
        placeholder_tool_calls = 0  # Count placeholder tool calls
        
        while len(history) - init_len < actual_max_turns and active_agent:
            # Get completion
            completion = self.get_chat_completion(
                agent=active_agent,
                history=history,
                context_variables=context_variables,
                model_override=model_override,
                stream=stream,
                debug=debug,
            )
            
            message: Message = completion.choices[0].message
            message.sender = active_agent.name
            # Convert Message to dict for logging
            message_dict = json.loads(message.model_dump_json())
            self.logger.pretty_print_messages(message_dict)
            history.append(message_dict)
            
            # Check if we should end
            if enter_agent.tool_choice != "required":
                if (not message.tool_calls and active_agent.name == enter_agent.name) or not execute_tools:
                    self.logger.info("Ending turn.", title="End Turn", color="red")
                    break
            else:
                if message.tool_calls and message.tool_calls[0].function.name == "case_resolved":
                    self.logger.info("Ending turn with case resolved.", title="End Turn", color="red")
                    partial_response = self.handle_tool_calls(
                        message.tool_calls,
                        active_agent.functions,
                        context_variables,
                        debug,
                        handle_mm_func=active_agent.handle_mm_func
                    )
                    history.extend(partial_response.messages)
                    context_variables.update(partial_response.context_variables)
                    
                    # Extract the result from case_resolved tool response and add as final message
                    for tool_msg in partial_response.messages:
                        if tool_msg.get("role") == "tool" and tool_msg.get("name") == "case_resolved":
                            tool_content = tool_msg.get("content", "")
                            # Add as final assistant message for easier extraction
                            history.append({
                                "role": "assistant",
                                "content": tool_content,
                                "sender": active_agent.name
                            })
                            break
                    break
                elif message.tool_calls and message.tool_calls[0].function.name == "case_not_resolved":
                    self.logger.info("Ending turn with case not resolved.", title="End Turn", color="red")
                    partial_response = self.handle_tool_calls(
                        message.tool_calls,
                        active_agent.functions,
                        context_variables,
                        debug,
                        handle_mm_func=active_agent.handle_mm_func
                    )
                    history.extend(partial_response.messages)
                    context_variables.update(partial_response.context_variables)
                    
                    # Extract the result from case_not_resolved tool response and add as final message
                    for tool_msg in partial_response.messages:
                        if tool_msg.get("role") == "tool" and tool_msg.get("name") == "case_not_resolved":
                            tool_content = tool_msg.get("content", "")
                            # Add as final assistant message for easier extraction
                            history.append({
                                "role": "assistant",
                                "content": tool_content,
                                "sender": active_agent.name
                            })
                            break
                    break
                elif not message.tool_calls or not execute_tools:
                    self.logger.info("Ending turn with no tool calls.", title="End Turn", color="red")
                    break
            
            # Handle tool calls
            if message.tool_calls:
                # Detect loops: check if we're making the same tool calls repeatedly
                tool_call_signatures = []
                tool_names_in_call = []
                for tc in message.tool_calls:
                    func_name = tc.function.name
                    tool_names_in_call.append(func_name)
                    # Count tool calls
                    tool_call_counts[func_name] = tool_call_counts.get(func_name, 0) + 1
                    # Create a signature from tool name and first 50 chars of arguments
                    args_preview = tc.function.arguments[:50] if tc.function.arguments else ""
                    signature = f"{func_name}({args_preview})"
                    tool_call_signatures.append(signature)
                
                # Check if this exact pattern was seen recently
                current_pattern = "|".join(sorted(tool_call_signatures))
                if current_pattern in recent_tool_calls:
                    # Same pattern seen before - likely in a loop
                    self.logger.warning(
                        f"Detected repeated tool call pattern. Stopping to prevent infinite loop.",
                        title="Loop Detection"
                    )
                    # Add a message explaining why we stopped
                    history.append({
                        "role": "assistant",
                        "content": "I've detected that I'm making the same tool calls repeatedly. This suggests the tools may not be providing the expected results, or I need to try a different approach. Please review the tool results above.",
                        "sender": active_agent.name
                    })
                    break
                
                # Check if same tool is being called too many times (even with different args)
                # This catches cases like calling search_web multiple times with different queries
                excessive_tool_detected = False
                for tool_name, count in tool_call_counts.items():
                    if count >= 3:  # Very aggressive: if a tool is called 3+ times, likely stuck
                        self.logger.warning(
                            f"Tool '{tool_name}' has been called {count} times. This may indicate the tool is not working as expected. Stopping to prevent excessive API calls.",
                            title="Excessive Tool Calls"
                        )
                        history.append({
                            "role": "assistant",
                            "content": f"I've called the '{tool_name}' tool {count} times, but it doesn't seem to be providing the expected results. This tool may be a placeholder or require additional setup. Please review the tool responses above or try a different approach.",
                            "sender": active_agent.name
                        })
                        excessive_tool_detected = True
                        break
                
                # Stop if we detected excessive tool calls
                if excessive_tool_detected:
                    break
                
                # Add current pattern to recent calls
                recent_tool_calls.append(current_pattern)
                if len(recent_tool_calls) > MAX_RECENT_CALLS:
                    recent_tool_calls.pop(0)  # Keep only last N patterns
                
                partial_response = self.handle_tool_calls(
                    message.tool_calls,
                    active_agent.functions,
                    context_variables,
                    debug,
                    handle_mm_func=active_agent.handle_mm_func
                )
                
                # Check for placeholder responses IMMEDIATELY after tool execution
                # This stops early before making more API calls
                placeholder_responses_in_batch = sum(1 for msg in partial_response.messages if 
                    msg.get("role") == "tool" and 
                    ("PLACEHOLDER" in str(msg.get("content", "")) or 
                     "not perform real" in str(msg.get("content", "")) or
                     "requires API integration" in str(msg.get("content", ""))))
                
                # Check if agent is making progress (successful tool calls)
                successful_tools = sum(1 for msg in partial_response.messages if 
                    msg.get("role") == "tool" and 
                    msg.get("name") not in ["case_resolved", "case_not_resolved"] and
                    "PLACEHOLDER" not in str(msg.get("content", "")) and
                    "not perform real" not in str(msg.get("content", "")) and
                    "Error" not in str(msg.get("content", "")))
                
                # Count total placeholder responses so far
                total_placeholder_count = sum(1 for msg in history if 
                    msg.get("role") == "tool" and 
                    ("PLACEHOLDER" in str(msg.get("content", "")) or 
                     "not perform real" in str(msg.get("content", "")) or
                     "requires API integration" in str(msg.get("content", ""))))
                
                total_placeholder_count += placeholder_responses_in_batch
                
                # Stop early if we get placeholder responses, but only if no successful tools
                # This allows agents to make progress even if some tools are placeholders
                if total_placeholder_count >= 3 and successful_tools == 0:
                    self.logger.warning(
                        f"Received {total_placeholder_count} placeholder tool responses with no successful tool calls. Tools may not be functioning properly. Stopping to prevent further API calls.",
                        title="Placeholder Tool Detection"
                    )
                    history.extend(partial_response.messages)
                    history.append({
                        "role": "assistant",
                        "content": f"I've received {total_placeholder_count} placeholder responses from tools, indicating they may not be fully functional. Please check tool configuration or try a different approach.",
                        "sender": active_agent.name
                    })
                    break
            else:
                # Convert Message object to dict for Response
                message_dict = json.loads(message.model_dump_json())
                # Ensure content is not None
                if message_dict.get("content") is None:
                    message_dict["content"] = "Task completed"
                partial_response = Response(messages=[message_dict])
            
            history.extend(partial_response.messages)
            context_variables.update(partial_response.context_variables)
            if partial_response.agent:
                active_agent = partial_response.agent
        
        return Response(
            messages=history[init_len:],
            agent=active_agent,
            context_variables=context_variables,
        )
    
    async def run_async(
        self,
        agent: Agent,
        messages: List,
        context_variables: dict = {},
        model_override: str = None,
        stream: bool = False,
        debug: bool = True,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        """Async version of run"""
        # Similar to run but using acompletion
        # Simplified for now - full implementation would mirror run() with async calls
        active_agent = agent
        context_variables = copy.copy(context_variables)
        history = copy.deepcopy(messages)
        init_len = len(messages)
        
        self.logger.info("Receiving the task:", history[-1]['content'], title="Receive Task", color="green")
        
        while len(history) - init_len < max_turns and active_agent:
            # Get async completion (simplified - would need full async implementation)
            # For now, fall back to sync
            return self.run(agent, messages, context_variables, model_override, stream, debug, max_turns, execute_tools)

