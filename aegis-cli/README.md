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

### Team Management
```bash
# Create a team
aegis team create "My Team"

# List teams
aegis get teams

# View team details
aegis get team "My Team"

# List team members
aegis team members --team "My Team"

# Add member to team
aegis team add-member --team "My Team" --user username

# Attach role to team
aegis attach-team-role --team "My Team" --role role-name
```

### Policy Management
Policies define permissions and are attached to roles. Policies use AWS IAM-style format.

```bash
# List policies
aegis get policies

# Create a policy from JSON file (using --file or -f)
aegis policy create MyPolicy --file policy.json --desc "Policy description"
aegis policy create MyPolicy -f policy.json --desc "Policy description"

# Create multiple policies from a single file (YAML format with --- separator)
aegis policy create dummy -f policies.yaml
# The 'name' argument is ignored when file contains multiple policies

# Create a policy from JSON string (using --content or -c)
aegis policy create MyPolicy --content '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": ["*"], "Resource": ["*"]}]}' --desc "Policy description"
aegis policy create MyPolicy -c '{"Version": "2012-10-17", "Statement": [...]}' --desc "Policy description"

# View policy details
aegis get policy MyPolicy

# Update policy from file (using --file or -f)
aegis policy update MyPolicy --file updated-policy.json
aegis policy update MyPolicy -f updated-policy.json

# Update policy from content (using --content or -c)
aegis policy update MyPolicy --content '{"Version": "2012-10-17", "Statement": [...]}'
aegis policy update MyPolicy -c '{"Version": "2012-10-17", "Statement": [...]}'
```

**Single Policy File Example** (`policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAll",
      "Effect": "Allow",
      "Action": ["*"],
      "Resource": ["*"]
    }
  ]
}
```

**Multiple Policies File Example** (`policies.yaml`):
```yaml
name: ReadOnlyPolicy
description: Read-only access policy
content:
  Version: "2012-10-17"
  Statement:
    - Sid: AllowRead
      Effect: Allow
      Action: ["*:read"]
      Resource: ["*"]
---
name: WritePolicy
description: Write access policy
content:
  Version: "2012-10-17"
  Statement:
    - Sid: AllowWrite
      Effect: Allow
      Action: ["*:write"]
      Resource: ["*"]
---
name: DenyPolicy
description: Deny all access
content:
  Version: "2012-10-17"
  Statement:
    - Sid: DenyAll
      Effect: Deny
      Action: ["*"]
      Resource: ["*"]
```

When using multiple policies in one file:
- Use `---` to separate each policy document
- Each document should have `name`, `description`, and `content` fields
- The `name` argument in the command is ignored when multiple policies are detected
- All policies will be created in a single operation

### Role Management
Roles are global and can be attached to users or teams. They link policies to define permissions.
Default roles: `admin`, `editor`, `viewer`, `deployer`.

```bash
# List roles
aegis get roles

# Create a custom role with attached policies
aegis role create custom-role --desc "Custom role description" --policy FullAccess --policy ReadOnly

# View role details and attached policies
aegis get role admin

# Attach role to user
aegis attach-user-role --user username --role role-name

# Attach role to team
aegis attach-team-role --team team-name --role role-name

# Attach policy to role
aegis attach-role-policy --role role-name --policy policy-name

# Edit role (interactive)
aegis edit role role-name

# Update role
aegis role edit role-name --desc "Updated description" --policy Policy1 --policy Policy2
```

## Example Workflow

```bash
# 1. Start the API service (in aegis-service/)
cd ../aegis-service
uvicorn src.main:app --reload

# 2. Register and login
aegis user create john --email john@example.com -p secret123
aegis login --username john -p secret123

# 3. Create team
aegis team create "Production"

# 4. List teams
aegis get teams

# 5. View team members
aegis team members

# 6. Create role and attach to user
aegis role create developer --desc "Developer role" --policy DeployAccess
aegis attach-user-role --user john --role developer

# 7. Attach role to team
aegis attach-team-role --team production --role developer
```

## Configuration File

`~/.aegis/config` example:
```yaml
api_url: http://localhost:8000
auth_token: eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Note:** Team context is no longer used. All commands require explicit team specification when needed.

