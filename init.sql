-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL UNIQUE, -- Added username
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workspaces Table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Roles Table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    description TEXT,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, -- NULL for global roles
    policy JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, workspace_id) -- Role names unique within a workspace (or global)
);

-- Workspace Members Table (Many-to-Many relationship between Users and Workspaces)
CREATE TABLE workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id)
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_workspaces_slug ON workspaces(slug);
CREATE INDEX idx_workspaces_owner_id ON workspaces(owner_id);
CREATE INDEX idx_workspace_members_user_id ON workspace_members(user_id);
CREATE INDEX idx_workspace_members_workspace_id ON workspace_members(workspace_id);
CREATE INDEX idx_roles_workspace_id ON roles(workspace_id);

-- Seed Default Roles
INSERT INTO roles (name, description, policy) VALUES
(
    'admin',
    'Full administrative access to workspace, members, and data.',
    '{"statements": [{"sid": "FullAccess", "effect": "allow", "actions": ["*"], "resources": ["*"]}]}'
),
(
    'editor',
    'Can manage workspace settings and members.',
    '{"statements": [{"sid": "WorkspaceManage", "effect": "allow", "actions": ["workspace:read", "workspace:update", "member:read", "member:add", "member:remove", "member:update"], "resources": ["*"]}]}'
),
(
    'viewer',
    'Read-only access to workspace and members.',
    '{"statements": [{"sid": "ReadOnly", "effect": "allow", "actions": ["workspace:read", "member:read"], "resources": ["*"]}]}'
),
(
    'deployer',
    'Can deploy and manage deployments.',
    '{"statements": [{"sid": "DeployAccess", "effect": "allow", "actions": ["workspace:read", "deployment:*"], "resources": ["*"]}]}'
);

-- ZERO TRUST: Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- RLS Policies (RBAC)

-- 1. Users Table
-- Read: Users can read their own profile
CREATE POLICY users_read_own ON users
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true)::uuid);

-- Update: Users can update their own profile
CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true)::uuid);

-- 2. Roles Table
-- Read: Global roles are visible to all. Workspace roles visible to members.
CREATE POLICY roles_read_access ON roles
    FOR SELECT
    USING (
        workspace_id IS NULL
        OR EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_id = roles.workspace_id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- 3. Workspaces Table
-- Read: Visible if owner OR member
CREATE POLICY workspaces_read_access ON workspaces
    FOR SELECT
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_id = workspaces.id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Insert: Any authenticated user can create a workspace (must be owner)
CREATE POLICY workspaces_insert ON workspaces
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- Update: Owner can update. Members with permission handled by API (RLS allows if member for now to support fine-grained)
-- NOTE: Strictly speaking, RLS should check permissions. For simplicity in this hybrid model,
-- we allow members to "see" the row for update, but API prevents actual change if no permission.
-- To be safer, we restrict UPDATE to Owner only in RLS, and rely on Owner to delegate?
-- No, that defeats the purpose of roles.
-- Let's allow Owners AND Members to *attempt* update at DB level, API filters logic.
CREATE POLICY workspaces_update ON workspaces
    FOR UPDATE
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_id = workspaces.id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Delete: Only Owner can delete the workspace
CREATE POLICY workspaces_delete ON workspaces
    FOR DELETE
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- 4. Workspace Members Table
-- Read: Visible if member of the workspace
CREATE POLICY members_read_access ON workspace_members
    FOR SELECT
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM workspace_members wm
            WHERE wm.workspace_id = workspace_members.workspace_id
            AND wm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Insert/Update/Delete: Allowed for members (API enforces role permissions)
CREATE POLICY members_write_access ON workspace_members
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM workspaces
            WHERE id = workspace_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR EXISTS (
            SELECT 1 FROM workspace_members existing_wm
            WHERE existing_wm.workspace_id = workspace_id
            AND existing_wm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );


-- Trigger to update updated_at column automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
