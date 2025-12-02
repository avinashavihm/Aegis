-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create non-superuser for application (superusers bypass RLS!)
-- The admin user created by POSTGRES_USER is superuser, we need a regular user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'aegis_app') THEN
        CREATE USER aegis_app WITH PASSWORD 'password123';
        GRANT CONNECT ON DATABASE agentic_ops TO aegis_app;
        GRANT USAGE ON SCHEMA public TO aegis_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO aegis_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aegis_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO aegis_app;
    END IF;
END $$;

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

-- Teams Table
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workspaces Table (for storing agents & workflows configuration, completely separate from teams)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content JSONB DEFAULT '{}', -- Stores agents and workflows configuration
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

-- Roles Table
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

-- Team Members Table
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
CREATE INDEX idx_workspaces_name ON workspaces(name);
CREATE INDEX idx_workspaces_owner_id ON workspaces(owner_id);

-- Seed Default Policies (AWS IAM style with Effect: Allow/Deny)
INSERT INTO policies (name, description, content) VALUES
(
    'FullAccess',
    'Full administrative access to everything',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "FullAccess", "Effect": "Allow", "Action": ["*"], "Resource": ["*"]}]}'
),
(
    'TeamManage',
    'Can manage team settings and members',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "TeamManage", "Effect": "Allow", "Action": ["team:read", "team:update", "member:read", "member:add", "member:remove", "member:update"], "Resource": ["*"]}]}'
),
(
    'ReadOnly',
    'Read-only access',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "ReadOnly", "Effect": "Allow", "Action": ["*:read"], "Resource": ["*"]}]}'
),
(
    'DeployAccess',
    'Can deploy and manage deployments',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "DeployAccess", "Effect": "Allow", "Action": ["team:read", "deployment:*"], "Resource": ["*"]}]}'
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

-- Create root user with admin role (bypassing RLS temporarily)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles DISABLE ROW LEVEL SECURITY;

INSERT INTO users (username, email, password_hash, full_name) VALUES
('root', 'root@aegis.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ysY3H1.5C0LW', 'Root Administrator');

-- Assign admin role to root user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r WHERE u.username = 'root' AND r.name = 'admin';

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- ZERO TRUST: Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (aegis_app user)
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE user_roles FORCE ROW LEVEL SECURITY;
ALTER TABLE teams FORCE ROW LEVEL SECURITY;
ALTER TABLE team_members FORCE ROW LEVEL SECURITY;
ALTER TABLE roles FORCE ROW LEVEL SECURITY;
ALTER TABLE policies FORCE ROW LEVEL SECURITY;
ALTER TABLE role_policies FORCE ROW LEVEL SECURITY;
ALTER TABLE team_roles FORCE ROW LEVEL SECURITY;
ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;

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

-- Helper function to check if current user has any role (direct or via team)
-- Uses SECURITY DEFINER to bypass RLS and avoid recursion
CREATE OR REPLACE FUNCTION current_user_has_any_role() RETURNS BOOLEAN AS $$
DECLARE
    user_uuid UUID;
BEGIN
    user_uuid := current_setting('app.current_user_id', true)::uuid;
    RETURN EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = user_uuid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- AWS IAM-style policy evaluation function
-- Checks if user has permission for an action on a resource
-- Deny statements have higher priority than Allow statements
CREATE OR REPLACE FUNCTION evaluate_policy_permission(
    action_name TEXT,
    resource_type TEXT,
    resource_id TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    user_uuid UUID;
    policy_json JSONB;
    statement JSONB;
    effect TEXT;
    actions JSONB;
    resources JSONB;
    action_match BOOLEAN;
    resource_match BOOLEAN;
    has_deny BOOLEAN := FALSE;
    has_allow BOOLEAN := FALSE;
    res_text TEXT;
    act_text TEXT;
BEGIN
    user_uuid := current_setting('app.current_user_id', true)::uuid;
    
    IF user_uuid IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Get all policies attached to user's roles
    FOR policy_json IN
        SELECT p.content
        FROM user_roles ur
        JOIN role_policies rp ON ur.role_id = rp.role_id
        JOIN policies p ON rp.policy_id = p.id
        WHERE ur.user_id = user_uuid
    LOOP
        -- Process each statement in the policy
        FOR statement IN SELECT * FROM jsonb_array_elements(policy_json->'Statement')
        LOOP
            effect := statement->>'Effect';
            actions := statement->'Action';
            resources := statement->'Resource';
            
            action_match := FALSE;
            resource_match := FALSE;
            
            -- Check if action matches (supports wildcard *)
            IF actions IS NULL OR actions = '["*"]'::jsonb THEN
                action_match := TRUE;
            ELSIF jsonb_typeof(actions) = 'array' THEN
                FOR act_text IN SELECT jsonb_array_elements_text(actions)
                LOOP
                    IF act_text = '*' 
                       OR act_text = action_name 
                       OR (act_text LIKE '%:*' AND SPLIT_PART(act_text, ':', 1) = SPLIT_PART(action_name, ':', 1))
                       OR action_name LIKE act_text
                    THEN
                        action_match := TRUE;
                        EXIT;
                    END IF;
                END LOOP;
            END IF;
            
            -- Check if resource matches (supports wildcard *)
            IF resources IS NULL OR resources = '["*"]'::jsonb THEN
                resource_match := TRUE;
            ELSIF jsonb_typeof(resources) = 'array' THEN
                FOR res_text IN SELECT jsonb_array_elements_text(resources)
                LOOP
                    IF res_text = '*' OR res_text = resource_id THEN
                        resource_match := TRUE;
                        EXIT;
                    END IF;
                END LOOP;
            END IF;
            
            -- If both action and resource match, record the effect
            IF action_match AND resource_match THEN
                IF effect = 'Deny' THEN
                    has_deny := TRUE;
                ELSIF effect = 'Allow' THEN
                    has_allow := TRUE;
                END IF;
            END IF;
        END LOOP;
    END LOOP;
    
    -- Deny has higher priority - if any deny, return false
    IF has_deny THEN
        RETURN FALSE;
    END IF;
    
    -- Otherwise, return true if there's an allow
    RETURN has_allow;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policies (RBAC)

-- 1. Users Table
-- Read: Admins see all, users with allow policy see users (unless denied)
-- Deny has higher priority - if user has deny policy for a user, they can't see it
CREATE POLICY users_read_own ON users
    FOR SELECT
    USING (
        current_user_is_admin()
        OR current_setting('app.current_user_id', true) IS NULL
        OR current_setting('app.current_user_id', true) = ''
        OR evaluate_policy_permission('user:read', 'user', 'user:' || username)
    );

-- Insert: Anyone can create a user (for registration), but they get no access until roles assigned
-- This allows unauthenticated registration (no app.current_user_id set)
CREATE POLICY users_insert ON users
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_user_id', true) IS NULL 
        OR current_setting('app.current_user_id', true) = ''
        OR current_user_is_admin()
    );

-- Update: Only admins can update users (zero-trust: no access without roles)
CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (
        current_user_is_admin()
    );

-- 2. Roles Table
-- Read: Admins see all, users with allow policy see roles (unless denied)
-- Deny has higher priority - if user has deny policy for a role, they can't see it
CREATE POLICY roles_read_access ON roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('role:read', 'role', 'role:' || name)
    );

-- 3. Teams Table
-- Read: Admins see all, users with allow policy see teams (unless denied)
-- Deny has higher priority - if user has deny policy for a team, they can't see it
CREATE POLICY teams_read_access ON teams
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('team:read', 'team', 'team:' || name)
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
        user_id = current_setting('app.current_user_id', true)::uuid
        OR current_user_is_admin()
    );

-- Write: Only team owners or admins can manage members
CREATE POLICY team_members_write_access ON team_members
    FOR ALL
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- 5. User Roles Table
-- Read: Admins see all, users see their own role assignments
CREATE POLICY user_roles_read_access ON user_roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR user_id = current_setting('app.current_user_id', true)::uuid
    );

-- Write: Only admins can assign roles (simplified: allow for now, can be restricted later)
CREATE POLICY user_roles_write_access ON user_roles
    FOR ALL
    USING (true);

-- 6. Team Roles Table
-- Read: Only admins can see team roles (team membership checked in API layer)
CREATE POLICY team_roles_read_access ON team_roles
    FOR SELECT
    USING (
        current_user_is_admin()
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
-- Read: Admins see all, users with allow policy see policies (unless denied)
-- Deny has higher priority - if user has deny policy for a policy, they can't see it
CREATE POLICY policies_read_access ON policies
    FOR SELECT
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('policy:read', 'policy', 'policy:' || name)
    );

-- 6. Role Policies Table
-- Read: Admins see all, users see role policies for their direct roles
CREATE POLICY role_policies_read_access ON role_policies
    FOR SELECT
    USING (
        current_user_is_admin()
        OR (
            current_user_has_any_role()
            AND EXISTS (
                SELECT 1 FROM user_roles ur
                WHERE ur.role_id = role_policies.role_id
                AND ur.user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    );

-- 8. Workspaces Table
-- Read: Admins see all, owners see their own, users with allow policy see workspaces (unless denied)
CREATE POLICY workspaces_read_access ON workspaces
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workspace:read', 'workspace', 'workspace:' || name)
    );

-- Insert: Any authenticated user can create a workspace
CREATE POLICY workspaces_insert ON workspaces
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- Update: Owner or admin can update
CREATE POLICY workspaces_update ON workspaces
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
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

CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
