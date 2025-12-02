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
- **Current Context**: Active team

Set custom API URL:
```bash
# Via environment variable
export AEGIS_API_URL=http://your-api-server:8000

# Or via config
python -c "from src.config import set_api_url; set_api_url('http://your-api:8000')"
```

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
aegis get teams (or 'ws')
aegis get policies

# Get specific resource
aegis get user yaswanth
aegis get role admin
aegis get team my-team
aegis get policy FullAccess
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

### Team Management (formerly Workspaces)
```bash
# Create a team (auto-sets as current context)
aegis team create "My Team"
# Note: Name is automatically slugified (e.g., "My Team" -> "my-team")

# List teams
aegis get teams

# Set current team context
aegis team set my-team

# List team members
aegis team members
```

### Policy Management
Policies define permissions and are attached to roles.

```bash
# List policies
aegis get policies

# Create a policy
aegis policy create MyPolicy --content '{"statements": [{"effect": "allow", "actions": ["*"], "resources": ["*"]}]}'

# View policy details
aegis get policy MyPolicy
```

### Role Management
Roles link users to policies within a team or globally.
Default roles: `admin`, `editor`, `viewer`, `deployer`.

```bash
# List roles
aegis get roles

# Create a custom role with attached policies
aegis role create custom-role --policy FullAccess --policy ReadOnly

# View role details and attached policies
aegis get role admin
```

## Example Workflow

```bash
# 1. Start the API service (in aegis-service/)
cd ../aegis-service
uvicorn src.main:app --reload

# 2. Register and login
aegis user create john --email john@example.com -p secret123
aegis login --username john -p secret123

# 3. Create and use team
aegis team create "Production" --slug prod
aegis team ls

# 4. View members
aegis team members
```

## Configuration File

`~/.aegis/config` example:
```yaml
api_url: http://localhost:8000
auth_token: eyJ0eXAiOiJKV1QiLCJhbGc...
current_context: prod
```

