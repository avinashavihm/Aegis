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
