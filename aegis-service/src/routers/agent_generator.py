"""
Agent Generator Router - Superior multi-file agent generation API

This router provides endpoints for:
- Generating sophisticated multi-file agent projects 
- Running agents in sandbox environments
- Downloading agent packages
- Managing generated projects
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import os
import base64
import asyncio
import subprocess
from datetime import datetime
import re

from src.dependencies import get_current_user_id
from src.routers.settings import decrypt_api_key
from src.database import get_db_connection

router = APIRouter(prefix="/agent-generator", tags=["agent-generator"])


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateAgentRequest(BaseModel):
    """Request model for generating a superior agent"""
    description: str = Field(..., description="Detailed description of what the agent should do")
    project_name: Optional[str] = Field(None, description="Name for the project")
    project_type: str = Field("simple", description="Type of project: simple, multi_agent, data_pipeline, etc.")
    tools: Optional[List[str]] = Field(None, description="List of aegis tools to use")
    capabilities: Optional[List[str]] = Field(None, description="Agent capabilities")
    model: Optional[str] = Field("gpt-4o", description="LLM model for generation")
    key_providers: Optional[List[str]] = Field(None, description="Provider ids whose keys should be injected")


class GenerateMultipleAgentsRequest(BaseModel):
    """Request model for generating multiple agents"""
    agents: List[GenerateAgentRequest] = Field(..., description="List of agent generation requests")
    workflow_name: Optional[str] = Field(None, description="Name for the workflow that connects these agents")


class GeneratedFileResponse(BaseModel):
    """Response model for a generated file"""
    path: str
    content: str
    description: Optional[str] = None


class GenerateAgentResponse(BaseModel):
    """Response model for agent generation"""
    success: bool
    project_name: str
    project_type: str
    files_count: int
    files: List[str]
    dependencies: List[str]
    created_at: str
    run_command: str
    interactive_command: str
    message: Optional[str] = None
    error: Optional[str] = None


class GenerateMultipleAgentsResponse(BaseModel):
    """Response model for multiple agent generation"""
    success: bool
    agents: List[GenerateAgentResponse]
    workflow_name: Optional[str] = None
    workflow_created: bool = False
    message: Optional[str] = None
    error: Optional[str] = None


class UpdateAgentConfigRequest(BaseModel):
    """Request model for updating agent configuration"""
    project_name: str = Field(..., description="Name of the agent project")
    config_updates: Dict[str, Any] = Field(..., description="Configuration updates to apply")
    file_path: Optional[str] = Field(None, description="Specific file to update (optional)")


class UpdateAgentConfigResponse(BaseModel):
    """Response model for agent configuration update"""
    success: bool
    project_name: str
    files_updated: List[str]
    message: Optional[str] = None
    error: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    """Request model for creating a workflow from agents"""
    workflow_name: str = Field(..., description="Name of the workflow")
    agent_projects: List[str] = Field(..., description="List of agent project names to include")
    description: Optional[str] = Field(None, description="Workflow description")
    execution_mode: str = Field("sequential", description="Workflow execution mode: sequential or parallel")


class CreateWorkflowResponse(BaseModel):
    """Response model for workflow creation"""
    success: bool
    workflow_name: str
    workflow_id: Optional[str] = None
    agent_count: int
    message: Optional[str] = None
    error: Optional[str] = None


class UpdateWorkflowRequest(BaseModel):
    """Request model for updating a workflow"""
    workflow_name: str
    updates: Dict[str, Any] = Field(..., description="Workflow updates to apply")


class UpdateWorkflowResponse(BaseModel):
    """Response model for workflow update"""
    success: bool
    workflow_name: str
    message: Optional[str] = None
    error: Optional[str] = None


class GenerateDockerArtifactsRequest(BaseModel):
    """Request model for generating docker artifacts"""
    project_name: str = Field(..., description="Name of the agent project")
    include_compose: bool = Field(True, description="Include docker-compose.yml")


class DockerArtifactInfo(BaseModel):
    """Information about a docker artifact"""
    filename: str
    content: str
    description: str


class GenerateDockerArtifactsResponse(BaseModel):
    """Response model for docker artifacts generation"""
    success: bool
    project_name: str
    artifacts: List[DockerArtifactInfo]
    package_structure: str
    message: Optional[str] = None
    error: Optional[str] = None


class BuildDockerImageRequest(BaseModel):
    """Request model for building docker image"""
    project_name: str = Field(..., description="Name of the agent project")
    image_name: Optional[str] = Field(None, description="Custom image name/tag")
    build_context: Optional[str] = Field(".", description="Build context path")


class BuildDockerImageResponse(BaseModel):
    """Response model for docker image build"""
    success: bool
    project_name: str
    image_name: str
    build_output: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class DeployDockerRequest(BaseModel):
    """Request model for deploying docker container"""
    project_name: str = Field(..., description="Name of the agent project")
    container_name: Optional[str] = Field(None, description="Custom container name")
    port_mapping: Optional[str] = Field(None, description="Port mapping (host:container)")
    env_file: Optional[str] = Field(None, description="Environment file path")


class DeployDockerResponse(BaseModel):
    """Response model for docker deployment"""
    success: bool
    project_name: str
    container_name: str
    container_id: Optional[str] = None
    deployment_output: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class RunSandboxRequest(BaseModel):
    """Request model for running agent in sandbox"""
    project_name: str = Field(..., description="Name of the agent project")
    task: str = Field(..., description="Task to execute")
    sandbox_type: str = Field("local", description="Sandbox type: local, venv, docker, e2b")
    timeout_seconds: int = Field(300, description="Maximum execution time")
    env_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    key_providers: Optional[List[str]] = Field(None, description="Provider ids whose keys should be injected")


class RunSandboxResponse(BaseModel):
    """Response model for sandbox execution"""
    success: bool
    output: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    sandbox_type: str
    error: Optional[str] = None


class DownloadPackageRequest(BaseModel):
    """Request model for downloading agent package"""
    project_name: str
    format: str = Field("zip", description="Package format: zip or tar.gz")
    include_docker: bool = Field(False, description="Include Docker files")


class DownloadPackageResponse(BaseModel):
    """Response model for package download"""
    success: bool
    package_name: str
    format: str
    size_bytes: int
    file_count: int
    download_url: Optional[str] = None
    base64_content: Optional[str] = None
    error: Optional[str] = None


class ProjectTypeInfo(BaseModel):
    """Information about a project type"""
    name: str
    description: str
    use_case: str


class ProjectTypesResponse(BaseModel):
    """Response model for project types list"""
    types: Dict[str, ProjectTypeInfo]


class ProjectFilesResponse(BaseModel):
    """Response model for project files"""
    success: bool
    project_name: str
    file_count: int
    files: List[str]
    structure: str
    error: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_workspace_path(user_id: str) -> str:
    """Get the workspace path for a user"""
    import os
    base_path = os.path.join(os.getcwd(), "workspace", "aegis_workspace")
    os.makedirs(base_path, exist_ok=True)
    return base_path


def get_agents_dir(user_id: str) -> str:
    """Get the agents directory"""
    workspace = get_workspace_path(user_id)
    agents_dir = os.path.join(workspace, "agents")
    os.makedirs(agents_dir, exist_ok=True)
    return agents_dir


# =============================================================================
# Registry stubs (to satisfy frontend fetches)
# =============================================================================

@router.get("/registry/agents")
async def list_registry_agents():
    """Stubbed registry endpoint (no registered sub-agents yet)."""
    return []


@router.get("/registry/directory")
async def registry_directory():
    """Stubbed registry directory markdown."""
    return {"markdown": ""}


# Default env vars forwarded into sandboxes so generated agents can run with
# the same credentials the backend already has configured.
SANDBOX_ENV_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "GROQ_API_KEY",
    "COHERE_API_KEY",
    "E2B_API_KEY",
    "HUGGINGFACE_HUB_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "OPENAI_BASE_URL",
    "OPENAI_ORG_ID",
    "FIRECRAWL_API_KEY",
    "FIRECRAWL_BASE_URL",
]


def _fetch_user_api_env(user_id: str, allowed_providers: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Load stored API keys for the user and map them to standard env vars.
    """
    env: Dict[str, str] = {}
    allowed_set = {p.lower() for p in allowed_providers} if allowed_providers else None
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT provider, api_key_encrypted, base_url, organization_id, is_active
                FROM api_keys
                WHERE owner_id = %s AND is_active = TRUE
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            for row in rows:
                provider = (row["provider"] or "").lower()
                if allowed_set is not None and provider not in allowed_set:
                    continue
                api_key = decrypt_api_key(row["api_key_encrypted"])
                base_url = row.get("base_url")
                org_id = row.get("organization_id")

                if provider == "openai":
                    env["OPENAI_API_KEY"] = api_key
                    if base_url:
                        env["OPENAI_BASE_URL"] = base_url
                    if org_id:
                        env["OPENAI_ORG_ID"] = org_id
                elif provider == "anthropic":
                    env["ANTHROPIC_API_KEY"] = api_key
                elif provider in ("google", "gemini"):
                    env["GEMINI_API_KEY"] = api_key
                    env["GOOGLE_API_KEY"] = api_key
                elif provider == "groq":
                    env["GROQ_API_KEY"] = api_key
                elif provider == "mistral":
                    env["MISTRAL_API_KEY"] = api_key
                elif provider == "cohere":
                    env["COHERE_API_KEY"] = api_key
                elif provider == "together":
                    env["TOGETHER_API_KEY"] = api_key
                elif provider == "azure":
                    env["AZURE_OPENAI_API_KEY"] = api_key
                    if base_url:
                        env["AZURE_OPENAI_ENDPOINT"] = base_url
                elif provider == "firecrawl":
                    env["FIRECRAWL_API_KEY"] = api_key
                    if base_url:
                        env["FIRECRAWL_BASE_URL"] = base_url
                elif provider == "custom":
                    # store under CUSTOM_API_KEY and CUSTOM_BASE_URL if provided
                    env["CUSTOM_API_KEY"] = api_key
                    if base_url:
                        env["CUSTOM_BASE_URL"] = base_url
    return env


def build_sandbox_env(
    overrides: Optional[Dict[str, str]],
    user_id: Optional[str] = None,
    allowed_providers: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Merge backend keys with request overrides and stored user keys (request wins)."""
    env: Dict[str, str] = {}
    if user_id:
        env.update(_fetch_user_api_env(user_id, allowed_providers))
    env.update({k: v for k in SANDBOX_ENV_KEYS if (v := os.getenv(k))})
    if overrides:
        env.update(overrides)
    return env


def _require_e2b_key(env: Dict[str, str]):
    if not env.get("E2B_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E2B_API_KEY is required for e2b sandbox. Set it in backend env or pass via env_variables.",
        )


def _apply_user_keys_to_env(user_id: str, allowed_providers: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
    """
    Apply user API keys to the process env for the lifetime of a request.
    Returns the previous values to allow restoration.
    """
    new_env = _fetch_user_api_env(user_id, allowed_providers)
    previous: Dict[str, Optional[str]] = {}
    for key, value in new_env.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    return previous


def _restore_env(previous: Dict[str, Optional[str]]):
    for key, old_val in previous.items():
        if old_val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_val


def _extract_missing_module(error_text: str) -> Optional[str]:
    match = re.search(r"ModuleNotFoundError: No module named ['\\\"]([^'\\\" ]+)['\\\"]", error_text or "")
    return match.group(1) if match else None


async def create_workflow_from_agents(workflow_name: str, agent_names: List[str], user_id: UUID) -> bool:
    """
    Create a workflow that connects multiple agents.

    Args:
        workflow_name: Name of the workflow
        agent_names: List of agent project names
        user_id: User ID

    Returns:
        True if workflow was created successfully
    """
    try:
        from src.schemas import WorkflowStep

        if len(agent_names) < 2:
            return False

        # Create workflow steps for each agent
        steps = []
        for i, agent_name in enumerate(agent_names):
            step = WorkflowStep(
                step_id=f"step_{i+1}",
                agent_id=agent_name,  # For now, use agent name as ID
                name=f"Execute {agent_name}",
                description=f"Execute the {agent_name} agent",
                input_mapping={} if i == 0 else {"input": f"step_{i}.output"},  # Chain outputs
                output_key=f"step_{i+1}_output",
                config={"agent_project": agent_name}
            )
            steps.append(step)

        # Create workflow in database
        with get_db_connection(str(user_id)) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflows (
                        name, description, steps, execution_mode,
                        tags, metadata, status, owner_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_name,
                        f"Workflow connecting agents: {', '.join(agent_names)}",
                        json.dumps([s.model_dump() for s in steps]),
                        "sequential",
                        json.dumps(["generated", "multi-agent"]),
                        json.dumps({
                            "generated_agents": agent_names,
                            "agent_count": len(agent_names)
                        }),
                        "draft",
                        str(user_id)
                    )
                )
                conn.commit()

        return True

    except Exception as e:
        print(f"Failed to create workflow: {e}")
        return False


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/types", response_model=ProjectTypesResponse)
async def list_project_types():
    """List all available agent project types"""
    types = {
        "simple": ProjectTypeInfo(
            name="Simple Agent",
            description="Basic single-purpose agent project",
            use_case="Simple tasks, quick automation"
        ),
        "multi_agent": ProjectTypeInfo(
            name="Multi-Agent System",
            description="Multiple specialized agents with orchestration",
            use_case="Complex tasks requiring different expertise"
        ),
        "data_pipeline": ProjectTypeInfo(
            name="Data Pipeline Agent",
            description="ETL and data processing pipelines",
            use_case="Data extraction, transformation, analysis"
        ),
        "web_automation": ProjectTypeInfo(
            name="Web Automation Agent",
            description="Web scraping and browser automation",
            use_case="Web data collection, form automation"
        ),
        "api_integration": ProjectTypeInfo(
            name="API Integration Agent",
            description="REST API integration and orchestration",
            use_case="External service integration, webhooks"
        ),
        "research": ProjectTypeInfo(
            name="Research Agent",
            description="Research and analysis with web search",
            use_case="Information gathering, market research"
        ),
        "code_assistant": ProjectTypeInfo(
            name="Code Assistant Agent",
            description="Code generation, review, and refactoring",
            use_case="Development assistance, code quality"
        ),
        "workflow": ProjectTypeInfo(
            name="Workflow Agent",
            description="Workflow automation with stages",
            use_case="Business process automation"
        ),
        "custom": ProjectTypeInfo(
            name="Custom Agent",
            description="Fully customizable agent project",
            use_case="Specialized requirements"
        )
    }
    
    return ProjectTypesResponse(types=types)


@router.post("/generate", response_model=GenerateAgentResponse)
async def generate_agent(
    request: GenerateAgentRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Generate a sophisticated multi-file agent project.
    
    This creates production-ready agents with multiple interconnected files,

    """
    try:
        from aegis.generator import AgentGenerator
        from aegis.generator.project_templates import AgentProjectType
        
        # Map project type
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
        
        project_type = type_map.get(request.project_type.lower(), AgentProjectType.SIMPLE)
        
        # Get output directory
        agents_dir = get_agents_dir(str(current_user_id))
        
        # Create generator and generate project (with user-selected keys applied)
        allowed = [p.lower() for p in (request.key_providers or [])] or None
        previous_env = _apply_user_keys_to_env(str(current_user_id), allowed)
        try:
            generator = AgentGenerator(model=request.model or "gpt-4o")
            
            project = generator.generate(
                description=request.description,
                project_name=request.project_name,
                project_type=project_type,
                tools=request.tools,
                capabilities=request.capabilities,
                model_override=request.model
            )
        finally:
            _restore_env(previous_env)
        
        # Save project
        project_dir = generator.save_project(project, agents_dir)
        
        return GenerateAgentResponse(
            success=True,
            project_name=project.name,
            project_type=request.project_type,
            files_count=len(project.files),
            files=[f.path for f in project.files],
            dependencies=project.dependencies,
            created_at=project.created_at,
            run_command=f"cd {project_dir} && python main.py 'your task'",
            interactive_command=f"cd {project_dir} && python main.py -i",
            message=f"Successfully generated {project.name} with {len(project.files)} files"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate agent: {str(e)}"
        )


@router.post("/generate-multiple", response_model=GenerateMultipleAgentsResponse)
async def generate_multiple_agents(
    request: GenerateMultipleAgentsRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Generate multiple sophisticated multi-file agent projects.

    This creates production-ready agents with multiple interconnected files,
    and optionally creates a workflow to connect them.
    """
    try:
        from aegis.generator import AgentGenerator
        from aegis.generator.project_templates import AgentProjectType

        # Map project type
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

        # Get output directory
        agents_dir = get_agents_dir(str(current_user_id))

        generated_agents = []
        workflow_created = False

        # Generate each agent
        for agent_request in request.agents:
            project_type = type_map.get(agent_request.project_type.lower(), AgentProjectType.SIMPLE)

            # Create generator and generate project (with user-selected keys applied)
            allowed = [p.lower() for p in (agent_request.key_providers or [])] or None
            previous_env = _apply_user_keys_to_env(str(current_user_id), allowed)
            try:
                generator = AgentGenerator(model=agent_request.model or "gpt-4o")

                project = generator.generate(
                    description=agent_request.description,
                    project_name=agent_request.project_name,
                    project_type=project_type,
                    tools=agent_request.tools,
                    capabilities=agent_request.capabilities,
                    model_override=agent_request.model
                )
            finally:
                _restore_env(previous_env)

            # Save project
            project_dir = generator.save_project(project, agents_dir)

            agent_response = GenerateAgentResponse(
                success=True,
                project_name=project.name,
                project_type=agent_request.project_type,
                files_count=len(project.files),
                files=[f.path for f in project.files],
                dependencies=project.dependencies,
                created_at=project.created_at,
                run_command=f"cd {project_dir} && python main.py 'your task'",
                interactive_command=f"cd {project_dir} && python main.py -i",
                message=f"Successfully generated {project.name} with {len(project.files)} files"
            )
            generated_agents.append(agent_response)

        # Create workflow if requested and we have at least 2 agents
        if request.workflow_name and len(generated_agents) >= 2:
            try:
                workflow_created = await create_workflow_from_agents(
                    request.workflow_name,
                    [agent.project_name for agent in generated_agents],
                    current_user_id
                )
            except Exception as workflow_error:
                # Don't fail the entire request if workflow creation fails
                pass

        return GenerateMultipleAgentsResponse(
            success=True,
            agents=generated_agents,
            workflow_name=request.workflow_name,
            workflow_created=workflow_created,
            message=f"Successfully generated {len(generated_agents)} agents{' and workflow' if workflow_created else ''}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate multiple agents: {str(e)}"
        )


@router.put("/update-config", response_model=UpdateAgentConfigResponse)
async def update_agent_config(
    request: UpdateAgentConfigRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update the configuration of a generated agent project.
    """
    try:
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)

        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )

        files_updated = []

        # If specific file is provided, update only that file
        if request.file_path:
            file_path = os.path.join(project_path, request.file_path)
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {request.file_path}"
                )

            # Read current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Apply configuration updates (simple key-value replacement for now)
            updated_content = content
            for key, value in request.config_updates.items():
                # Look for patterns like key = "old_value" or key: "old_value"
                import re
                pattern = rf'(\b{re.escape(key)}\s*[:=]\s*)["\']([^"\']*)["\']'
                replacement = f'\\1"{value}"' if isinstance(value, str) else f'\\1{value}'
                updated_content = re.sub(pattern, replacement, updated_content)

            # Write back the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            files_updated.append(request.file_path)

        else:
            # Update all relevant config files
            config_files = ['config.py', 'main.py', 'requirements.txt']

            for config_file in config_files:
                file_path = os.path.join(project_path, config_file)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Apply configuration updates
                    updated_content = content
                    for key, value in request.config_updates.items():
                        import re
                        pattern = rf'(\b{re.escape(key)}\s*[:=]\s*)["\']([^"\']*)["\']'
                        replacement = f'\\1"{value}"' if isinstance(value, str) else f'\\1{value}'
                        updated_content = re.sub(pattern, replacement, updated_content)

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                    files_updated.append(config_file)

        return UpdateAgentConfigResponse(
            success=True,
            project_name=request.project_name,
            files_updated=files_updated,
            message=f"Successfully updated {len(files_updated)} files in {request.project_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent configuration: {str(e)}"
        )


@router.post("/create-workflow", response_model=CreateWorkflowResponse)
async def create_workflow_endpoint(
    request: CreateWorkflowRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a workflow that orchestrates multiple agent projects.
    """
    try:
        # Validate that all agent projects exist
        agents_dir = get_agents_dir(str(current_user_id))
        missing_agents = []

        for agent_name in request.agent_projects:
            agent_path = os.path.join(agents_dir, agent_name)
            if not os.path.exists(agent_path):
                missing_agents.append(agent_name)

        if missing_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent projects not found: {', '.join(missing_agents)}"
            )

        # Create workflow steps
        from src.schemas import WorkflowStep
        steps = []
        for i, agent_name in enumerate(request.agent_projects):
            step = WorkflowStep(
                step_id=f"step_{i+1}",
                agent_id=agent_name,
                name=f"Execute {agent_name}",
                description=f"Execute the {agent_name} agent",
                input_mapping={} if i == 0 else {"input": f"step_{i}.output"},
                output_key=f"step_{i+1}_output",
                config={"agent_project": agent_name}
            )
            steps.append(step)

        # Create workflow in database
        with get_db_connection(str(current_user_id)) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflows (
                        name, description, steps, execution_mode,
                        tags, metadata, status, owner_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        request.workflow_name,
                        request.description or f"Workflow orchestrating agents: {', '.join(request.agent_projects)}",
                        json.dumps([s.model_dump() for s in steps]),
                        request.execution_mode,
                        json.dumps(["generated", "agent-workflow"]),
                        json.dumps({
                            "agent_projects": request.agent_projects,
                            "agent_count": len(request.agent_projects)
                        }),
                        "draft",
                        str(current_user_id)
                    )
                )
                result = cur.fetchone()
                workflow_id = result['id']
                conn.commit()

        return CreateWorkflowResponse(
            success=True,
            workflow_name=request.workflow_name,
            workflow_id=str(workflow_id),
            agent_count=len(request.agent_projects),
            message=f"Successfully created workflow '{request.workflow_name}' with {len(request.agent_projects)} agents"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.put("/update-workflow", response_model=UpdateWorkflowResponse)
async def update_workflow_endpoint(
    request: UpdateWorkflowRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update an existing workflow configuration.
    """
    try:
        with get_db_connection(str(current_user_id)) as conn:
            with conn.cursor() as cur:
                # Check if workflow exists
                cur.execute(
                    "SELECT id FROM workflows WHERE name = %s AND owner_id = %s",
                    (request.workflow_name, str(current_user_id))
                )
                existing = cur.fetchone()

                if not existing:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Workflow not found: {request.workflow_name}"
                    )

                # Build update query
                update_fields = []
                update_values = []

                for key, value in request.updates.items():
                    if key in ['name', 'description', 'execution_mode', 'status']:
                        update_fields.append(f"{key} = %s")
                        update_values.append(value)
                    elif key == 'steps':
                        update_fields.append("steps = %s")
                        update_values.append(json.dumps(value))
                    elif key == 'tags':
                        update_fields.append("tags = %s")
                        update_values.append(json.dumps(value))
                    elif key == 'metadata':
                        update_fields.append("metadata = %s")
                        update_values.append(json.dumps(value))

                if not update_fields:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No valid update fields provided"
                    )

                update_query = f"""
                    UPDATE workflows
                    SET {', '.join(update_fields)}, updated_at = NOW()
                    WHERE name = %s AND owner_id = %s
                """
                update_values.extend([request.workflow_name, str(current_user_id)])

                cur.execute(update_query, update_values)
                conn.commit()

        return UpdateWorkflowResponse(
            success=True,
            workflow_name=request.workflow_name,
            message=f"Successfully updated workflow '{request.workflow_name}'"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.post("/generate-docker-artifacts", response_model=GenerateDockerArtifactsResponse)
async def generate_docker_artifacts(
    request: GenerateDockerArtifactsRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Generate Docker artifacts for an agent project and show package structure.
    """
    try:
        from aegis.generator.agent_packager import AgentPackager
        from aegis.generator.agent_generator import GeneratedProject, GeneratedFile

        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)

        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )

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
                            files.append(GeneratedFile(path=rel_path, content=content))
                    except:
                        pass

        # Create project object
        project = GeneratedProject(
            name=request.project_name,
            description=f"Agent project: {request.project_name}",
            project_type="custom",
            files=files,
            dependencies=["litellm", "python-dotenv"]
        )

        # Generate package structure
        structure_lines = []
        for root, dirs, filenames in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.venv']
            level = root.replace(project_path, '').count(os.sep)
            indent = '  ' * level
            folder_name = os.path.basename(root)
            if folder_name:
                structure_lines.append(f"{indent}{folder_name}/")

            sub_indent = '  ' * (level + 1)
            for filename in sorted(filenames):
                if not filename.startswith('.'):
                    structure_lines.append(f"{sub_indent}{filename}")

        package_structure = "\n".join(structure_lines)

        # Generate Docker artifacts
        packager = AgentPackager()
        artifacts = []

        try:
            # Copy Aegis framework to project directory for Docker builds
            aegis_src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(project_path))), "src", "aegis")
            aegis_dest_path = os.path.join(project_path, "aegis")

            if os.path.exists(aegis_src_path) and not os.path.exists(aegis_dest_path):
                import shutil
                shutil.copytree(aegis_src_path, aegis_dest_path)

            # Generate Dockerfile
            dockerfile_content = packager._create_dockerfile(project)
            artifacts.append(DockerArtifactInfo(
                filename="Dockerfile",
                content=dockerfile_content,
                description="Docker image definition for containerizing the agent"
            ))

            # Save Dockerfile to project directory
            dockerfile_path = os.path.join(project_path, "Dockerfile")
            with open(dockerfile_path, 'w', encoding='utf-8') as f:
                f.write(dockerfile_content)

            # Generate docker-compose if requested
            if request.include_compose:
                docker_compose_content = packager._create_docker_compose(project)
                artifacts.append(DockerArtifactInfo(
                    filename="docker-compose.yml",
                    content=docker_compose_content,
                    description="Docker Compose configuration for easy deployment"
                ))

                # Save docker-compose.yml to project directory
                docker_compose_path = os.path.join(project_path, "docker-compose.yml")
                with open(docker_compose_path, 'w', encoding='utf-8') as f:
                    f.write(docker_compose_content)

            # Generate .dockerignore
            dockerignore_content = packager._create_dockerignore()
            artifacts.append(DockerArtifactInfo(
                filename=".dockerignore",
                content=dockerignore_content,
                description="Docker ignore file to exclude unnecessary files"
            ))

            # Save .dockerignore to project directory
            dockerignore_path = os.path.join(project_path, ".dockerignore")
            with open(dockerignore_path, 'w', encoding='utf-8') as f:
                f.write(dockerignore_content)

            # Clean up macOS resource fork files that cause xattr errors
            import glob
            for resource_fork in glob.glob(os.path.join(project_path, "._*")):
                try:
                    os.remove(resource_fork)
                except Exception:
                    pass  # Ignore errors removing resource forks

        finally:
            packager.cleanup()

        return GenerateDockerArtifactsResponse(
            success=True,
            project_name=request.project_name,
            artifacts=artifacts,
            package_structure=package_structure,
            message=f"Generated {len(artifacts)} Docker artifacts for {request.project_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Docker artifacts: {str(e)}"
        )


@router.post("/build-docker-image", response_model=BuildDockerImageResponse)
async def build_docker_image(
    request: BuildDockerImageRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Build a Docker image for an agent project.
    """
    try:
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)

        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )

        # Generate default image name if not provided
        image_name = request.image_name or f"aegis-{request.project_name.lower()}:latest"

        # Ensure Dockerfile exists
        dockerfile_path = os.path.join(project_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dockerfile not found. Generate Docker artifacts first."
            )

            # Clean up macOS resource fork files that cause xattr errors
            import glob
            for resource_fork in glob.glob(os.path.join(project_path, "._*")):
                try:
                    os.remove(resource_fork)
                except Exception:
                    pass  # Ignore errors removing resource forks

        # Build Docker image
        import subprocess
        build_command = [
            "docker", "build",
            "-t", image_name,
            "-f", dockerfile_path,
            request.build_context if request.build_context != "." else project_path
        ]

        try:
            result = subprocess.run(
                build_command,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            if result.returncode == 0:
                return BuildDockerImageResponse(
                    success=True,
                    project_name=request.project_name,
                    image_name=image_name,
                    build_output=result.stdout,
                    message=f"Successfully built Docker image: {image_name}"
                )
            else:
                return BuildDockerImageResponse(
                    success=False,
                    project_name=request.project_name,
                    image_name=image_name,
                    build_output=result.stdout,
                    error=result.stderr,
                    message=f"Failed to build Docker image: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Docker build timed out after 10 minutes"
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Docker command not found. Please ensure Docker is installed."
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build Docker image: {str(e)}"
        )


@router.post("/deploy-docker", response_model=DeployDockerResponse)
async def deploy_docker_container(
    request: DeployDockerRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Deploy an agent project as a Docker container.
    """
    try:
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)

        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )

        # Generate container name if not provided
        container_name = request.container_name or f"aegis-{request.project_name.lower()}"

        # Check if docker-compose.yml exists
        compose_path = os.path.join(project_path, "docker-compose.yml")
        if os.path.exists(compose_path):
            # Ensure .env.example exists, create from .env if needed
            env_example_path = os.path.join(project_path, ".env.example")
            env_path = os.path.join(project_path, ".env")
            if not os.path.exists(env_example_path) and os.path.exists(env_path):
                import shutil
                shutil.copy(env_path, env_example_path)
                pass  # .env.example created
            elif not os.path.exists(env_example_path):
                # Create a minimal .env.example
                with open(env_example_path, 'w') as f:
                    f.write("# Environment variables for the agent\n")
                    f.write("# Copy this file to .env and fill in your API keys\n")
                    f.write("OPENAI_API_KEY=\n")
                    f.write("ANTHROPIC_API_KEY=\n")
                    f.write("GEMINI_API_KEY=\n")
                    f.write("LOG_LEVEL=INFO\n")

            # Use docker-compose
            deploy_command = ["docker-compose", "up", "-d", "--build"]
            # Add env_file if provided and exists, otherwise use .env.example if it exists
            if request.env_file and os.path.exists(request.env_file):
                deploy_command.extend(["--env-file", request.env_file])
            elif os.path.exists(env_example_path):
                deploy_command.extend(["--env-file", env_example_path])

            try:
                result = subprocess.run(
                    deploy_command,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minutes timeout
                )

                if result.returncode == 0:
                    # Get container ID
                    container_id = None
                    try:
                        inspect_result = subprocess.run(
                            ["docker", "ps", "-q", "-f", f"name={container_name}"],
                            capture_output=True,
                            text=True
                        )
                        container_id = inspect_result.stdout.strip()
                    except:
                        pass

                    return DeployDockerResponse(
                        success=True,
                        project_name=request.project_name,
                        container_name=container_name,
                        container_id=container_id,
                        deployment_output=result.stdout,
                        message=f"Successfully deployed Docker container: {container_name}"
                    )
                else:
                    return DeployDockerResponse(
                        success=False,
                        project_name=request.project_name,
                        container_name=container_name,
                        deployment_output=result.stdout,
                        error=result.stderr,
                        message=f"Failed to deploy Docker container: {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Docker deployment timed out"
                )
        else:
            # Use docker run directly
            image_name = f"aegis-{request.project_name.lower()}:latest"
            run_command = [
                "docker", "run", "-d",
                "--name", container_name
            ]

            if request.port_mapping:
                run_command.extend(["-p", request.port_mapping])

            if request.env_file:
                run_command.extend(["--env-file", request.env_file])

            run_command.append(image_name)

            try:
                result = subprocess.run(
                    run_command,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    return DeployDockerResponse(
                        success=True,
                        project_name=request.project_name,
                        container_name=container_name,
                        container_id=container_id,
                        deployment_output=result.stdout,
                        message=f"Successfully deployed Docker container: {container_name}"
                    )
                else:
                    return DeployDockerResponse(
                        success=False,
                        project_name=request.project_name,
                        container_name=container_name,
                        deployment_output=result.stdout,
                        error=result.stderr,
                        message=f"Failed to deploy Docker container: {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Docker deployment timed out"
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy Docker container: {str(e)}"
        )


@router.post("/generate/stream")
async def generate_agent_stream(
    request: GenerateAgentRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Generate an agent with streaming output.
    
    Returns a Server-Sent Events stream with progress updates.
    """
    try:
        from aegis.generator import AgentGenerator
        from aegis.generator.project_templates import AgentProjectType
        
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
        
        project_type = type_map.get(request.project_type.lower(), AgentProjectType.SIMPLE)
        
        async def generate_stream():
            allowed = [p.lower() for p in (request.key_providers or [])] or None
            previous_env = _apply_user_keys_to_env(str(current_user_id), allowed)
            try:
                generator = AgentGenerator(model=request.model or "gpt-4o")
            
                for event in generator.generate_streaming(
                    description=request.description,
                    project_name=request.project_name,
                    project_type=project_type,
                    tools=request.tools,
                    capabilities=request.capabilities,
                    model_override=request.model
                ):
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0)  # Allow other tasks to run
                
                # Save project at the end
                if "project" in event:
                    agents_dir = get_agents_dir(str(current_user_id))
                    generator.save_project(generator.generated_projects.get(event["project"]["name"]), agents_dir)
            finally:
                _restore_env(previous_env)
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/sandbox/run", response_model=RunSandboxResponse)
async def run_in_sandbox(
    request: RunSandboxRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Run an agent project in an isolated sandbox environment.
    """
    import os
    
    try:
        from aegis.generator import AgentSandbox, create_sandbox
        from aegis.generator.agent_sandbox import SandboxType, SandboxConfig
        
        # Get project path
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)
        
        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )
        
        # Map sandbox type
        type_map = {
            "local": SandboxType.LOCAL,
            "venv": SandboxType.VENV,
            "docker": SandboxType.DOCKER,
            "e2b": SandboxType.E2B,
        }
        
        sb_type = type_map.get(request.sandbox_type.lower(), SandboxType.LOCAL)
        
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
        
        # Build env and validate E2B if needed
        merged_env = build_sandbox_env(
            request.env_variables,
            str(current_user_id),
            [p.lower() for p in (request.key_providers or [])] or None,
        )
        if sb_type == SandboxType.E2B:
            _require_e2b_key(merged_env)

        # Create and run sandbox
        config = SandboxConfig(
            sandbox_type=sb_type,
            timeout_seconds=request.timeout_seconds,
            env_variables=merged_env,
            auto_install_deps=True
        )
        
        sandbox = create_sandbox(sb_type, config)
        
        try:
            sandbox.create(project_files)
            
            # Install dependencies
            install_result = sandbox.install_dependencies()
            if not install_result.success:
                return RunSandboxResponse(
                    success=False,
                    sandbox_type=request.sandbox_type,
                    stderr=install_result.stderr,
                    error=f"Failed to install dependencies: {install_result.error}"
                )
            
            # Run task
            result = sandbox.run(task=request.task)

            # Auto-fix missing dependency once
            if not result.success:
                missing_mod = _extract_missing_module(result.stderr or result.error or "")
                if missing_mod:
                    fix_result = sandbox.install_dependencies(requirements=[missing_mod])
                    if fix_result.success:
                        retry = sandbox.run(task=request.task)
                        retry.stdout = (result.stdout or "") + f"\n[auto-fix] Installed {missing_mod} and re-ran.\n" + (retry.stdout or "")
                        retry.stderr = (result.stderr or "") + (retry.stderr or "")
                        result = retry

            return RunSandboxResponse(
                success=result.success,
                output=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                execution_time=result.execution_time,
                sandbox_type=request.sandbox_type,
                error=result.error
            )
            
        finally:
            sandbox.cleanup()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox execution failed: {str(e)}"
        )


@router.post("/sandbox/run/stream")
async def run_in_sandbox_stream(
    request: RunSandboxRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Run an agent in sandbox with streaming output.
    """
    import os
    
    try:
        from aegis.generator import create_sandbox
        from aegis.generator.agent_sandbox import SandboxType, SandboxConfig
        
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)
        
        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )
        
        type_map = {
            "local": SandboxType.LOCAL,
            "venv": SandboxType.VENV,
            "docker": SandboxType.DOCKER,
            "e2b": SandboxType.E2B,
        }
        
        sb_type = type_map.get(request.sandbox_type.lower(), SandboxType.LOCAL)
        
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
        
        async def run_stream():
            merged_env = build_sandbox_env(
                request.env_variables,
                str(current_user_id),
                [p.lower() for p in (request.key_providers or [])] or None,
            )
            if sb_type == SandboxType.E2B:
                _require_e2b_key(merged_env)

            config = SandboxConfig(
                sandbox_type=sb_type,
                timeout_seconds=request.timeout_seconds,
                env_variables=merged_env,
                auto_install_deps=True,
            )
            
            sandbox = create_sandbox(sb_type, config)
            
            try:
                sandbox.create(project_files)
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Installing dependencies...'})}\n\n"
                
                install_result = sandbox.install_dependencies()
                if not install_result.success:
                    yield f"data: {json.dumps({'type': 'error', 'message': install_result.error or install_result.stderr or 'Dependency installation failed'})}\n\n"
                    return
                
                yield f"data: {json.dumps({'type': 'status', 'message': 'Running task...'})}\n\n"
                
                output_lines = []
                def on_output(line):
                    output_lines.append(line)
                
                result = sandbox.run(task=request.task, on_output=on_output)

                # Attempt one auto-fix for missing dependencies
                if not result.success:
                    missing_mod = _extract_missing_module(result.stderr or result.error or "")
                    if missing_mod:
                        yield f"data: {json.dumps({'type': 'status', 'message': f'Auto-fixing missing dependency: {missing_mod}'})}\n\n"
                        fix_result = sandbox.install_dependencies(requirements=[missing_mod])
                        if not fix_result.success:
                            yield f"data: {json.dumps({'type': 'error', 'message': fix_result.error or fix_result.stderr or 'Failed to auto-install dependency'})}\n\n"
                            return

                        # Rerun after installing dependency
                        output_lines = []
                        result = sandbox.run(task=request.task, on_output=on_output)
                        for line in output_lines:
                            yield f"data: {json.dumps({'type': 'output', 'text': line})}\n\n"
                            await asyncio.sleep(0)
                
                for line in output_lines:
                    yield f"data: {json.dumps({'type': 'output', 'text': line})}\n\n"
                    await asyncio.sleep(0)
                
                yield f"data: {json.dumps({'type': 'complete', 'success': result.success, 'exit_code': result.exit_code, 'stderr': result.stderr, 'error': result.error})}\n\n"
            except Exception as e:
                # Surface sandbox errors to the client
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                sandbox.cleanup()
        
        return StreamingResponse(
            run_stream(),
            media_type="text/event-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/package", response_model=DownloadPackageResponse)
async def create_package(
    request: DownloadPackageRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a downloadable package from an agent project.
    
    Returns package info with base64 encoded content for download.
    """
    import os
    
    try:
        from aegis.generator import AgentPackager
        from aegis.generator.agent_generator import GeneratedProject, GeneratedFile
        
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, request.project_name)
        
        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {request.project_name}"
            )
        
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
                            files.append(GeneratedFile(path=rel_path, content=content))
                    except:
                        pass
        
        # Create project object
        project = GeneratedProject(
            name=request.project_name,
            description=f"Agent project: {request.project_name}",
            project_type="custom",
            files=files,
            dependencies=["litellm", "python-dotenv"]
        )
        
        # Create package
        packager = AgentPackager()
        
        try:
            if request.format.lower() == "tar.gz":
                package_info = packager.create_tar_gz(project)
            else:
                package_info = packager.create_zip(
                    project,
                    include_docker=request.include_docker,
                    include_venv_setup=True
                )
            
            return DownloadPackageResponse(
                success=True,
                package_name=package_info.name,
                format=package_info.format,
                size_bytes=package_info.size_bytes,
                file_count=package_info.file_count,
                download_url=package_info.data_url,
                base64_content=package_info.base64_content
            )
            
        finally:
            packager.cleanup()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create package: {str(e)}"
        )


@router.get("/package/{project_name}/download")
async def download_package_file(
    project_name: str,
    format: str = "zip",
    include_docker: bool = False,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Download an agent package as a file.
    """
    import os
    
    try:
        from aegis.generator import AgentPackager
        from aegis.generator.agent_generator import GeneratedProject, GeneratedFile
        
        agents_dir = get_agents_dir(str(current_user_id))
        project_path = os.path.join(agents_dir, project_name)
        
        if not os.path.exists(project_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_name}"
            )
        
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
                            files.append(GeneratedFile(path=rel_path, content=content))
                    except:
                        pass
        
        project = GeneratedProject(
            name=project_name,
            description=f"Agent project: {project_name}",
            project_type="custom",
            files=files
        )
        
        packager = AgentPackager()
        
        try:
            if format.lower() == "tar.gz":
                package_info = packager.create_tar_gz(project)
                media_type = "application/gzip"
            else:
                package_info = packager.create_zip(project, include_docker=include_docker)
                media_type = "application/zip"
            
            content = base64.b64decode(package_info.base64_content)
            
            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={package_info.name}"
                }
            )
            
        finally:
            packager.cleanup()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/projects", response_model=List[str])
async def list_projects(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all generated agent projects"""
    import os
    
    agents_dir = get_agents_dir(str(current_user_id))
    
    if not os.path.exists(agents_dir):
        return []
    
    projects = []
    for item in os.listdir(agents_dir):
        item_path = os.path.join(agents_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Check if it looks like a project (has main.py or config.py)
            if os.path.exists(os.path.join(item_path, "main.py")) or \
               os.path.exists(os.path.join(item_path, "config.py")):
                projects.append(item)
    
    return projects


@router.get("/projects/{project_name}", response_model=ProjectFilesResponse)
async def get_project_files(
    project_name: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get the files and structure of a generated project"""
    import os
    
    agents_dir = get_agents_dir(str(current_user_id))
    project_path = os.path.join(agents_dir, project_name)
    
    if not os.path.exists(project_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_name}"
        )
    
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
    
    return ProjectFilesResponse(
        success=True,
        project_name=project_name,
        file_count=len(files),
        files=files,
        structure="\n".join(structure)
    )


@router.get("/projects/{project_name}/files/{file_path:path}")
async def get_file_content(
    project_name: str,
    file_path: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get the content of a specific file in a project"""
    import os
    
    agents_dir = get_agents_dir(str(current_user_id))
    full_path = os.path.join(agents_dir, project_name, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "path": file_path,
            "content": content
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )


@router.delete("/projects/{project_name}")
async def delete_project(
    project_name: str,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a generated project"""
    import os
    import shutil
    
    agents_dir = get_agents_dir(str(current_user_id))
    project_path = os.path.join(agents_dir, project_name)
    
    if not os.path.exists(project_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_name}"
        )
    
    try:
        shutil.rmtree(project_path)
        return {"success": True, "message": f"Project '{project_name}' deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
