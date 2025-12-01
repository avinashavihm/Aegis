# Aegis CLI

Command Line Interface for Agentic Ops - connects to Aegis API service.

## Prerequisites

1. **Python 3.9+**
2. **Aegis API service** running (see `aegis-service/`)
3. **uv** for package management

## Installation

```bash
cd aegis-cli
uv venv
source .venv/bin/activate  
uv pip install -e .
```

## Configuration

The CLI stores configuration in `~/.aegis/config`:
- **API URL**: Service endpoint (default: `http://localhost:8000`)
- **Auth Token**: JWT token from login
- **Current Context**: Active workspace

Set custom API URL:
```bash
# Via environment variable
export AEGIS_API_URL=http://your-api-server:8000

# Or via config
python -c "from src.config import set_api_url; set_api_url('http://your-api:8000')"
```

## Usage

## Usage

### Global Options

- `--output`, `-o`: Output format. Options: `table` (default), `json`, `yaml`, `text`.

Example:
```bash
aegis get users --output yaml
```

### Unified Get Command
The `get` command is the primary way to retrieve resources. It supports singular/plural forms and ID/name lookups.

```bash
# List resources
aegis get users
aegis get roles
aegis get workspaces (or 'ws')

# Get specific resource
aegis get user yaswanth
aegis get role admin
aegis get workspace my-workspace
```

### User Management
```bash
# Register a new user
aegis user create <username> --email <email> -p <password> --name "Full Name"

# Login (saves token to ~/.aegis/config)
aegis login --username <username> -p <password>

# View current user
aegis get user
```

### Workspace Management
```bash
# Create a workspace (auto-sets as current context)
aegis workspace create "My Workspace"
# Note: Name is automatically slugified (e.g., "My Workspace" -> "my-workspace")

# List workspaces
aegis get ws

# Set current workspace context
aegis workspace set my-workspace

# List workspace members
aegis workspace members
```

### Role Management
Roles use professional naming conventions: `admin`, `editor`, `viewer`, `deployer`.

```bash
# List roles
aegis get roles

# View role details and policy
aegis get role admin -o yaml
```

## Example Workflow

```bash
# 1. Start the API service (in aegis-service/)
cd ../aegis-service
uvicorn src.main:app --reload

# 2. Register and login
aegis user create john --email john@example.com -p secret123
aegis user login

# 3. Create and use workspace
aegis workspace create "Production" --slug prod
aegis workspace ls

# 4. View members
aegis workspace members
```

## Configuration File

`~/.aegis/config` example:
```yaml
api_url: http://localhost:8000
auth_token: eyJ0eXAiOiJKV1QiLCJhbGc...
current_context: prod
```

