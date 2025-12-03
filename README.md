# Aegis - Agentic Ops Platform

Complete platform for managing users, teams, and RBAC using PostgreSQL Row Level Security.

## Architecture

```
┌─────────────────┐
│   Aegis CLI     │  (Python - Typer/Rich)
│  (HTTP Client)  │
└────────┬────────┘
         │ HTTP/JWT
         ▼
┌─────────────────┐
│ Aegis Service   │  (FastAPI)
│   (REST API)    │
└────────┬────────┘
         │ SQL + RLS
         ▼
┌─────────────────┐
│   PostgreSQL    │  (Database with RLS)
│  (Docker)       │
└─────────────────┘
```

## Components

### 1. **PostgreSQL Database** (`init.sql`)
- User management with secure password hashing
- Team management with ownership (formerly Workspaces)
- Team members with roles (Owner, Admin, Member, Viewer)
- **Policies** for granular permission definitions
- **Row Level Security (RLS)** policies for automatic RBAC enforcement
- UUID-based primary keys

### 2. **Aegis Service** (`aegis-service/`)
- **FastAPI** REST API
- JWT authentication
- No Pydantic models (traditional dict-based)
- Auto-documentation at `/docs`
- RBAC enforced via PostgreSQL RLS

### 3. **Aegis CLI** (`aegis-cli/`)
- **Typer** command-line interface
- **Rich** terminal UI
- Unified `get` command structure
- Professional role management with policy attachment

## Quick Start

### 1. Start Services with Docker

```bash
# Start PostgreSQL + Aegis Service
nerdctl compose up -d

# Check status
nerdctl compose ps
```

### 2. Install and Use CLI

```bash
cd aegis-cli
uv venv
source .venv/bin/activate
uv pip install -e .

# Login with default admin account
aegis login --username root --password admin

# Or register a new user
aegis user create yaswanth --email yaswanth@example.com -p secret123
aegis login --username yaswanth -p secret123

# Create team
aegis team create "Production"

# List everything
aegis get users
aegis get teams
aegis get roles
aegis get policies
```

## Environment Variables

Create `.env` file in project root:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agentic_ops
DB_USER=admin
DB_PASSWORD=password123

# JWT (aegis-service)
SECRET_KEY=your-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## API Endpoints

Base URL: `http://localhost:8000`

### Authentication
- `POST /auth/register` - Register user
- `POST /auth/login` - Login (get JWT)
- `GET /auth/me` - Current user

### Users
- `GET /users` - List users
- `GET /users/{id}` - Get user (includes teams & roles)
- `PUT /users/{id}` - Update user

### Teams
- `POST /teams` - Create team
- `GET /teams` - List teams
- `GET /teams/{id}` - Get team
- `PUT /teams/{id}` - Update team
- `DELETE /teams/{id}` - Delete team

### Workspaces
- `POST /workspaces` - Create workspace
- `GET /workspaces` - List workspaces
- `GET /workspaces/{id}` - Get workspace
- `PUT /workspaces/{id}` - Update workspace
- `DELETE /workspaces/{id}` - Delete workspace

### Members
- `GET /teams/{id}/members` - List members
- `POST /teams/{id}/members` - Add member
- `DELETE /teams/{id}/members/{user_id}` - Remove member

### Policies & Roles
- `GET /policies` - List policies
- `POST /policies` - Create policy
- `PUT /policies/{id}` - Update policy
- `DELETE /policies/{id}` - Delete policy
- `GET /roles` - List roles (all roles are global)
- `POST /roles` - Create role with attached policies
- `PUT /roles/{id}` - Update role
- `DELETE /roles/{id}` - Delete role

## RBAC Roles & Policies

Roles are global collections of policies that define permissions. Roles can be attached to users or teams.

| Role | Permissions |
|------|-------------|
| **administrator** | Full administrative access to all resources |
| **team-manager** | Full access to manage teams and team members |
| **read-only-viewer** | Read-only access to all resources |
| **deployment-manager** | Full access to manage deployments and view teams |
| **workspace-manager** | Full access to manage workspaces (agents & workflows) |
| **user-manager** | Full access to manage users |
| **role-viewer** | Read-only access to view roles and policies |

**Key Points:**
- All roles are **global** (not team-scoped)
- Roles can be attached to **users** directly or to **teams** (inherited by team members)
- Policies use AWS IAM-style format with `Allow` and `Deny` effects
- `Deny` statements take priority over `Allow` statements

**Available Actions:**
- `create` - Create new resources
- `modify` - Update existing resources
- `get` - Retrieve a specific resource (includes full definitions/configurations)
- `list` - List multiple resources (includes basic information)
- `read` - Read access to view resource definitions, configurations, and all metadata
- `delete` - Delete resources

**Read Access - Definitions and Configurations:**
The `read`, `get`, and `list` actions allow users to read resource definitions and configurations:

- **Workspaces**: Read access includes viewing the `content` field (agent/workflow configurations), name, description, and owner information
- **Policies**: Read access includes viewing the full policy JSON content, policy definitions, name, and description
- **Roles**: Read access includes viewing role definitions, descriptions, and attached policies
- **Teams**: Read access includes viewing team definitions, descriptions, owner, and member information
- **Users**: Read access includes viewing user profiles, email, full name, and role assignments
- **Deployments**: Read access includes viewing deployment definitions and configurations

**Important:** Read access means users can view complete resource definitions and configurations, not just basic metadata. This is essential for understanding how resources are configured and what they contain.

Actions follow the format: `resource_type:action` (e.g., `workspace:create`, `team:modify`, `user:delete`)

**Example Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WorkspaceReadWrite",
      "Effect": "Allow",
      "Action": ["workspace:create", "workspace:modify", "workspace:read", "workspace:list", "workspace:get"],
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
```

## Development

### Run Service Locally (without Docker)

```bash
cd aegis-service
uv venv
source .venv/bin/activate
uv pip install -e .
uvicorn src.main:app --reload
```

### Database Migrations

Modify `init.sql` and rebuild:

```bash
nerdctl compose down -v  # WARNING: Deletes all data
nerdctl compose up -d
```

## Project Structure

```
Aegis/
├── docker-compose.yml           # Docker services
├── init.sql                     # Database schema + RLS policies
├── aegis-service/               # FastAPI backend
│   ├── src/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB + RLS
│   │   ├── auth.py              # JWT
│   │   ├── dependencies.py      # Auth deps
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── teams.py         # Team management
│   │       ├── roles.py         # Role management
│   │       └── policies.py      # Policy management
│   ├── Dockerfile
│   └── pyproject.toml
└── aegis-cli/                   # CLI tool
    ├── src/
    │   ├── main.py              # Typer app
    │   ├── api_client.py        # HTTP client
    │   ├── config.py            # Config (~/.aegis/config)
    │   └── commands/
    │       ├── user.py
    │       ├── team.py
    │       ├── role.py
    │       └── policy.py
    └── pyproject.toml
```

## Security Features

✅ **Password Hashing** (bcrypt)  
✅ **JWT Authentication**  
✅ **Row Level Security (RLS)** - Database-enforced RBAC  
✅ **UUID Primary Keys** - Prevents enumeration  
✅ **CORS Protection**  
✅ **Environment-based Secrets**

## Default Credentials

On first deployment, a default admin account is created:
- **Username:** `root`
- **Password:** `admin`

**Important:** Change the default password after first login in production environments.

## Delete Commands

All delete commands support the `-y` or `--yes` flag to skip confirmation prompts:

```bash
# Delete with confirmation
aegis user delete username
aegis team delete team-name
aegis workspace delete workspace-name
aegis role delete role-name
aegis policy delete policy-name

# Delete without confirmation (quiet mode)
aegis user delete username -y
aegis team delete team-name -y
aegis workspace delete workspace-name -y
aegis role delete role-name -y
aegis policy delete policy-name -y
```

## Troubleshooting

**CLI can't connect to API:**
```bash
# Check if service is running
nerdctl compose ps

# Check API URL in CLI config
cat ~/.aegis/config
```

**Permission denied errors:**
- Check if you're logged in: `aegis get user`
- Verify your role: `aegis get roles`

**Database connection failed:**
```bash
# Check PostgreSQL logs
nerdctl compose logs postgres

# Restart services
nerdctl compose restart
```

**Error messages:**
- All error messages now display as clear text instead of generic "Internal Server Error"
- Database connection errors show helpful messages
- RLS policy violations show specific error details

## License

MIT
