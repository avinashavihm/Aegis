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
docker compose up -d

# Check status
docker compose ps
```

### 2. Install and Use CLI

```bash
cd aegis-cli
uv venv
source .venv/bin/activate
uv pip install -e .

# Register and login
aegis user create john --email john@example.com -p secret123
aegis login --username john -p secret123

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

### Teams (formerly Workspaces)
- `POST /teams` - Create team
- `GET /teams` - List teams
- `GET /teams/{id}` - Get team
- `PUT /teams/{id}` - Update team
- `DELETE /teams/{id}` - Delete team

### Members
- `GET /teams/{id}/members` - List members
- `POST /teams/{id}/members` - Add member
- `DELETE /teams/{id}/members/{user_id}` - Remove member

### Policies & Roles
- `GET /policies` - List policies
- `POST /policies` - Create policy
- `GET /roles` - List roles
- `POST /roles` - Create role with attached policies

## RBAC Roles & Policies

Roles are collections of policies that define permissions.

| Role | Permissions |
|------|-------------|
| **admin** | Full administrative access to team, members, and data |
| **editor** | Can manage team settings and members |
| **viewer** | Read-only access to team and members |
| **deployer** | Can deploy and manage deployments |

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
docker compose down -v  # WARNING: Deletes all data
docker compose up -d
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

## Troubleshooting

**CLI can't connect to API:**
```bash
# Check if service is running
docker compose ps

# Check API URL in CLI config
cat ~/.aegis/config
```

**Permission denied errors:**
- Check if you're logged in: `aegis user me`
- Verify your role in team: `aegis team members`

**Database connection failed:**
```bash
# Check PostgreSQL logs
docker compose logs postgres

# Restart services
docker compose restart
```

## License

MIT
