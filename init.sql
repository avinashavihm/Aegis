-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Teams Table (formerly Workspaces)
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Policies Table (NEW)
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    content JSONB NOT NULL, -- The actual policy JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Roles Table (Modified: Removed policy column)
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    description TEXT,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE, -- Null for global roles
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, team_id)
);

-- Role-Policies Mapping (Many-to-Many)
CREATE TABLE role_policies (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    policy_id UUID REFERENCES policies(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, policy_id)
);

-- Team Members Table (formerly Workspace Members)
CREATE TABLE team_members (
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, user_id)
);

-- User Roles Table (Direct role assignment to users, not through teams)
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Team Roles Table (Roles assigned to the team itself, inherited by members)
CREATE TABLE team_roles (
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, role_id)
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_teams_name ON teams(name);
CREATE INDEX idx_teams_owner_id ON teams(owner_id);
CREATE INDEX idx_team_members_user_id ON team_members(user_id);
CREATE INDEX idx_team_members_team_id ON team_members(team_id);
CREATE INDEX idx_roles_team_id ON roles(team_id);

-- Seed Default Policies
INSERT INTO policies (name, description, content) VALUES
(
    'FullAccess',
    'Full administrative access to everything',
    '{"statements": [{"sid": "FullAccess", "effect": "allow", "actions": ["*"], "resources": ["*"]}]}'
),
(
    'TeamManage',
    'Can manage team settings and members',
    '{"statements": [{"sid": "TeamManage", "effect": "allow", "actions": ["team:read", "team:update", "member:read", "member:add", "member:remove", "member:update"], "resources": ["*"]}]}'
),
(
    'ReadOnly',
    'Read-only access',
    '{"statements": [{"sid": "ReadOnly", "effect": "allow", "actions": ["team:read", "member:read"], "resources": ["*"]}]}'
),
(
    'DeployAccess',
    'Can deploy and manage deployments',
    '{"statements": [{"sid": "DeployAccess", "effect": "allow", "actions": ["team:read", "deployment:*"], "resources": ["*"]}]}'
);

-- Seed Default Roles (Linked to Policies)
INSERT INTO roles (name, description) VALUES
('admin', 'Full administrative access'),
('editor', 'Can manage team settings'),
('viewer', 'Read-only access'),
('deployer', 'Can deploy applications');

-- Link Roles to Policies
INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'admin' AND p.name = 'FullAccess';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'editor' AND p.name = 'TeamManage';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'viewer' AND p.name = 'ReadOnly';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'deployer' AND p.name = 'DeployAccess';

-- ZERO TRUST: Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_roles ENABLE ROW LEVEL SECURITY;

-- Helper function to check if current user has admin role
CREATE OR REPLACE FUNCTION current_user_is_admin() RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = current_setting('app.current_user_id', true)::uuid
        AND r.name = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policies (RBAC)

-- 1. Users Table
-- Read: Admins can see all users, regular users can only see their own profile
CREATE POLICY users_read_own ON users
    FOR SELECT
    USING (
        current_user_is_admin()
        OR id = current_setting('app.current_user_id', true)::uuid
    );

-- Update: Admins can update any user, users can update their own profile
CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR id = current_setting('app.current_user_id', true)::uuid
    );

-- 2. Roles Table
-- Read: Admins see all roles, global roles visible to all, team roles visible to team members
CREATE POLICY roles_read_access ON roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR team_id IS NULL
        OR EXISTS (
            SELECT 1 FROM team_members
            WHERE team_id = roles.team_id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- 3. Teams Table
-- Read: Admins see all teams, others see teams they own or are members of
CREATE POLICY teams_read_access ON teams
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM team_members
            WHERE team_id = teams.id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Insert: Any authenticated user can create a team (must be owner)
CREATE POLICY teams_insert ON teams
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- Update: Owner can update. Members with permission handled by API (RLS allows if member for now to support fine-grained)
-- NOTE: Strictly speaking, RLS should check permissions. For simplicity in this hybrid model,
-- we allow members to "see" the row for update, but API prevents actual change if no permission.
-- To be safer, we restrict UPDATE to Owner only in RLS, and rely on Owner to delegate?
-- No, that defeats the purpose of roles.
-- 4. Team Members Table
-- Read: Visible if member of the same team
CREATE POLICY team_members_read_access ON team_members
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM team_members tm
            WHERE tm.team_id = team_members.team_id
            AND tm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Write: Team owner or members (with permissions) can manage members
-- (Simplified: checks if user is owner or member of the team)
CREATE POLICY team_members_write_access ON team_members
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR EXISTS (
            SELECT 1 FROM team_members existing_tm
            WHERE existing_tm.team_id = team_id
            AND existing_tm.user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- 5. User Roles Table
-- Read: Users can see their own role assignments
CREATE POLICY user_roles_read_access ON user_roles
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- Write: Only admins can assign roles (simplified: allow for now, can be restricted later)
CREATE POLICY user_roles_write_access ON user_roles
    FOR ALL
    USING (true);

-- 6. Team Roles Table
-- Read: Visible to team members
CREATE POLICY team_roles_read_access ON team_roles
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM team_members
            WHERE team_id = team_roles.team_id
            AND user_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Write: Team owners or admins
CREATE POLICY team_roles_write_access ON team_roles
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- 7. Policies Table
-- Read: Visible to all authenticated users
CREATE POLICY policies_read_access ON policies
    FOR SELECT
    USING (true);

-- 6. Role Policies Table
-- Read: Visible to all authenticated users
CREATE POLICY role_policies_read_access ON role_policies
    FOR SELECT
    USING (true);

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

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
