# Aegis Service

FastAPI Backend Service for Agentic Ops with RBAC enforcement via PostgreSQL Row Level Security.

## Features

- **JWT Authentication**: Secure token-based auth
- **RBAC**: Row Level Security policies automatically enforce permissions
- **User Management**: Registration, login, profile management
- **Workspace Management**: CRUD operations with role-based access
- **Member Management**: Add/remove workspace members with role control
- **OpenAPI Docs**: Auto-generated API documentation

## Installation

1. **Prerequisites**: Python 3.9+, PostgreSQL (running), [uv](https://github.com/astral-sh/uv)
2. **Setup**:
   ```bash
   cd aegis-service
   uv venv
   source .venv/bin/activate  
   uv pip install -e .
   ```

3. **Configuration** (optional):
   Create `.env` file:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=agentic_ops
   DB_USER=aegis_app
   DB_PASSWORD=password123
   SECRET_KEY=your-secret-key-here
   ```

## Default Credentials

On first deployment, a default admin account is created:
- **Username:** `root`
- **Password:** `admin`

**Important:** Change the default password after first login in production environments.

## Running

```bash
# Development
uvicorn src.main:app --reload

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (get JWT token)
- `GET /auth/me` - Get current user

### Users
- `GET /users` - List users
- `GET /users/{id}` - Get user details
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### Workspaces
- `POST /workspaces` - Create workspace
- `GET /workspaces` - List workspaces
- `GET /workspaces/{id}` - Get workspace
- `PUT /workspaces/{id}` - Update workspace
- `DELETE /workspaces/{id}` - Delete workspace

### Teams
- `POST /teams` - Create team
- `GET /teams` - List teams
- `GET /teams/{id}` - Get team
- `PUT /teams/{id}` - Update team
- `DELETE /teams/{id}` - Delete team
- `GET /teams/{id}/members` - List members
- `POST /teams/{id}/members` - Add member
- `DELETE /teams/{id}/members/{user_id}` - Remove member
- `POST /teams/{id}/roles/{role_id}` - Attach role to team
- `DELETE /teams/{id}/roles/{role_id}` - Detach role from team

### Policies
- `GET /policies` - List policies
- `POST /policies` - Create policy
- `GET /policies/{id}` - Get policy
- `PUT /policies/{id}` - Update policy
- `DELETE /policies/{id}` - Delete policy

### Roles
- `GET /roles` - List roles
- `POST /roles` - Create role
- `GET /roles/{id}` - Get role
- `PUT /roles/{id}` - Update role
- `DELETE /roles/{id}` - Delete role
- `POST /roles/{id}/policies/{policy_id}` - Attach policy to role
- `DELETE /roles/{id}/policies/{policy_id}` - Detach policy from role

## RBAC Implementation

RBAC is enforced at the **database level** using PostgreSQL Row Level Security:

1. Each request sets `app.current_user_id` session variable
2. RLS policies automatically filter queries based on user permissions
3. No need for manual permission checks in application code

**Roles**:
- **Owner**: Full control over workspace
- **Admin**: Can manage members and update workspace
- **Member**: Can view and use workspace
- **Viewer**: Read-only access

## Example Usage

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "secret123"}'

# Login
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret123"}' | jq -r '.access_token')

# Create Workspace
curl -X POST http://localhost:8000/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workspace", "slug": "my-workspace"}'

# List Workspaces
curl -X GET http://localhost:8000/workspaces \
  -H "Authorization: Bearer $TOKEN"
```
