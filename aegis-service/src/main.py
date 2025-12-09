import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.routers import auth, users, teams, roles, policies, workspaces
from src.routers import agents, workflows, runs, tools, agent_files, mcp, configuration, files
from src.services.logging_service import AegisLogger

app = FastAPI(
    title="Aegis API",
    description="Backend Service for Agentic Ops with RBAC and Agent Framework",
    version="0.2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log API requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration_ms = (time.time() - start_time) * 1000
    
    # Extract user_id from request state if available
    user_id = getattr(request.state, 'user_id', None)
    
    # Log the request (skip health checks)
    if request.url.path not in ['/health', '/']:
        AegisLogger.log_api_request(
            method=request.method,
            path=request.url.path,
            user_id=user_id,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
    
    return response

# Include routers - RBAC
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(roles.router)
app.include_router(policies.router)
app.include_router(workspaces.router)

# Include routers - Agent Framework
app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(tools.router)
app.include_router(agent_files.router)
app.include_router(mcp.router)
app.include_router(configuration.router)
app.include_router(files.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Aegis API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
