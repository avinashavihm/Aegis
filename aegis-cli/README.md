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
aegis get teams
aegis get workspaces  # or 'ws' or 'workspace'
aegis get policies

# Get specific resource
aegis get user yaswanth
aegis get role administrator
aegis get team my-team
aegis get workspace my-workspace  # or 'ws my-workspace'
aegis get policy AdministratorAccess
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
Teams are for organizing users and managing access control.

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

# Remove member from team
aegis team remove-member --team "My Team" --user username

# Attach role to team
aegis attach-team-role --team "My Team" --role role-name

# Detach role from team
aegis detach-team-role --team "My Team" --role role-name
```

### Workspace Management
Workspaces are for storing agent and workflow configurations. They are separate from teams.

```bash
# Create a workspace
aegis workspace create "My Workspace" --desc "Description"

# List workspaces
aegis get workspaces  # or 'aegis get ws' or 'aegis get workspace'

# View workspace details (shows content with agents & workflows)
aegis get workspace "My Workspace"  # or 'aegis get ws "My Workspace"'
```

**Note:** Workspaces store agent and workflow configurations in the `content` field (JSON format). The workspace owner can manage the content through the API.

### Policy Management
Policies define permissions and are attached to roles. Policies use AWS IAM-style format with granular CRUD actions.

**Default Policies:**
- `AdministratorAccess` - Full administrative access to all resources
- `TeamManagement` - Full access to manage teams and team members
- `ReadOnlyAccess` - Read-only access to all resources
- `DeploymentManagement` - Full access to manage deployments and view teams
- `WorkspaceManagement` - Full access to manage workspaces (delete denied)
- `UserManagement` - Full access to manage users (delete denied)
- `RoleAndPolicyViewer` - Read-only access to view roles and policies

**Note:** All policies with read access allow reading resource definitions and configurations, not just basic metadata.

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
name: ReadOnlyAccessPolicy
description: Read-only access policy
content:
  Version: "2012-10-17"
  Statement:
    - Sid: AllowRead
      Effect: Allow
      Action: ["*:read", "*:list", "*:get"]
      Resource: ["*"]
---
name: WriteAccessPolicy
description: Write access policy
content:
  Version: "2012-10-17"
  Statement:
    - Sid: AllowWrite
      Effect: Allow
      Action: ["*:create", "*:modify"]
      Resource: ["*"]
---
name: FullManagementPolicy
description: Full management access
content:
  Version: "2012-10-17"
  Statement:
    - Sid: AllowAll
      Effect: Allow
      Action: ["*:create", "*:modify", "*:get", "*:list", "*:read", "*:delete"]
      Resource: ["*"]
---
name: DenyAllPolicy
description: Deny all access
content:
  Version: "2012-10-17"
  Statement:
    - Sid: DenyAll
      Effect: Deny
      Action: ["*"]
      Resource: ["*"]
```

**Available Actions:**
- `create` - Create new resources (INSERT operations)
- `modify` - Update existing resources (UPDATE operations)
- `get` - Retrieve a specific resource by ID/name (includes full definitions/configurations)
- `list` - List multiple resources (includes basic information)
- `read` - General read access to view resource definitions, configurations, and all metadata
- `delete` - Delete resources (DELETE operations)

**Read Access - Definitions and Configurations:**
The `read`, `get`, and `list` actions allow users to read resource definitions and configurations:

- **Workspaces**: Read access includes viewing the `content` field (agent/workflow configurations), name, description, and owner information
- **Policies**: Read access includes viewing the full policy JSON content, policy definitions, name, and description
- **Roles**: Read access includes viewing role definitions, descriptions, and attached policies
- **Teams**: Read access includes viewing team definitions, descriptions, owner, and member information
- **Users**: Read access includes viewing user profiles, email, full name, and role assignments
- **Deployments**: Read access includes viewing deployment definitions and configurations

**Important:** Read access means users can view complete resource definitions and configurations, not just basic metadata. This is essential for understanding how resources are configured and what they contain.

**Action Format:**
Actions follow the format: `resource_type:action` 

**Examples:**
- `workspace:create` - Create workspaces
- `workspace:modify` - Update workspaces
- `workspace:get` - Get a specific workspace
- `workspace:list` - List all workspaces
- `workspace:read` - General read access to workspaces
- `workspace:delete` - Delete workspaces
- `team:create`, `team:modify`, `team:delete` - Team management
- `user:create`, `user:modify`, `user:delete` - User management
- `role:create`, `role:modify`, `role:delete` - Role management
- `policy:create`, `policy:modify`, `policy:delete` - Policy management
- `member:create`, `member:delete` - Team member management

**Wildcards:**
- `*` - All actions for all resources
- `*:read` - Read action for all resource types
- `workspace:*` - All actions for workspace resources

When using multiple policies in one file:
- Use `---` to separate each policy document
- Each document should have `name`, `description`, and `content` fields
- The `name` argument in the command is ignored when multiple policies are detected
- All policies will be created in a single operation

### Role Management
Roles are global and can be attached to users or teams. They link policies to define permissions.

**Default Roles:**
- `administrator` - Full administrative access to all resources
- `team-manager` - Full access to manage teams and team members
- `read-only-viewer` - Read-only access to all resources
- `deployment-manager` - Full access to manage deployments and view teams
- `workspace-manager` - Full access to manage workspaces (agents & workflows)
- `user-manager` - Full access to manage users
- `role-viewer` - Read-only access to view roles and policies

```bash
# List roles
aegis get roles

# Create a custom role with attached policies
aegis role create custom-role --desc "Custom role description" --policy AdministratorAccess --policy ReadOnlyAccess

# View role details and attached policies
aegis get role administrator

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

# Delete role (with confirmation)
aegis role delete role-name

# Delete role without confirmation
aegis role delete role-name -y
```

### Delete Operations

All delete commands support the `-y` or `--yes` flag to skip confirmation:

```bash
# Delete user
aegis user delete username -y

# Delete team
aegis team delete team-name -y

# Delete workspace
aegis workspace delete workspace-name -y

# Delete role
aegis role delete role-name -y

# Delete policy
aegis policy delete policy-name -y

# Remove member from team
aegis team remove-member username --team team-name -y

# Remove role from team
aegis team remove-role role-name --team team-name -y

# Remove role from user
aegis user remove-role username role-name -y
```

## Example Workflow

```bash
# 1. Start the API service (in aegis-service/)
cd ../aegis-service
uvicorn src.main:app --reload

# 2. Login with default admin account
aegis login --username root --password admin

# Or register a new user
aegis user create john --email john@example.com -p secret123
aegis login --username john -p secret123

# 3. Create team
aegis team create "Production"

# 4. List teams
aegis get teams

# 5. View team members
aegis team members --team "Production"

# 6. Create workspace for agents/workflows
aegis workspace create "Production Agents" --desc "Production agent workspace"

# 7. List workspaces
aegis get workspaces

# 8. Create a custom policy with granular permissions
cat > workspace-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowWorkspaceRead",
      "Effect": "Allow",
      "Action": ["workspace:read", "workspace:list", "workspace:get"],
      "Resource": ["workspace:*"]
    },
    {
      "Sid": "AllowWorkspaceCreate",
      "Effect": "Allow",
      "Action": ["workspace:create"],
      "Resource": ["workspace:*"]
    },
    {
      "Sid": "DenyWorkspaceDelete",
      "Effect": "Deny",
      "Action": ["workspace:delete"],
      "Resource": ["workspace:*"]
    }
  ]
}
EOF
aegis policy create WorkspaceManagement -f workspace-policy.json --desc "Can create and read workspaces but not delete"

# 9. Create role and attach policy
aegis role create workspace-manager --desc "Workspace manager role" --policy WorkspaceManagement

# 10. Attach role to user
aegis attach-user-role --user john --role workspace-manager

# 11. Attach role to team (all team members inherit the role)
aegis attach-team-role --team "Production" --role workspace-manager
```

## Configuration File

`~/.aegis/config` example:
```yaml
api_url: http://localhost:8000
auth_token: eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Quick Reference

### Resource Types
- **Users** - System users who can authenticate
- **Teams** - Groups of users for organization and access control
- **Workspaces** - Containers for agent and workflow configurations (separate from teams)
- **Roles** - Global collections of policies that define permissions
- **Policies** - AWS IAM-style permission definitions with granular CRUD actions

### Key Concepts

**Teams vs Workspaces:**
- **Teams** are for organizing users and managing access control
- **Workspaces** are for storing agent and workflow configurations
- A user can belong to multiple teams
- A user can own multiple workspaces
- Teams and workspaces are independent concepts

**RBAC Model:**
- Roles are **global** (not team-scoped)
- Roles can be attached to **users** directly or to **teams** (inherited by team members)
- Policies use AWS IAM-style format with `Allow` and `Deny` effects
- `Deny` statements take priority over `Allow` statements
- Actions: `create`, `modify`, `get`, `list`, `read`, `delete`

**Read Access:**
- `read`, `get`, and `list` actions allow reading resource **definitions and configurations**
- Read access includes viewing complete resource data, not just basic metadata
- For workspaces: includes viewing `content` field (agent/workflow configurations)
- For policies: includes viewing full policy JSON content
- For roles: includes viewing role definitions and attached policies
- For teams: includes viewing team definitions and member information
- For users: includes viewing user profiles and role assignments

**Zero-Trust Security:**
- Users without roles have **no access** by default
- All access must be explicitly granted through roles and policies
- Row Level Security (RLS) enforces permissions at the database level

**Note:** Team context is no longer used. All commands require explicit team specification when needed.

