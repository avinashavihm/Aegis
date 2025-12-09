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
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
CREATE INDEX idx_workspaces_name ON workspaces(name);
CREATE INDEX idx_workspaces_owner_id ON workspaces(owner_id);

-- Seed Default Policies (AWS IAM style with Effect: Allow/Deny)
-- Policies use PascalCase naming convention
-- Note: read, get, and list actions allow reading resource definitions and configurations
INSERT INTO policies (name, description, content) VALUES
(
    'AdministratorAccess',
    'Full administrative access to all resources',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "AdministratorAccess", "Effect": "Allow", "Action": ["*"], "Resource": ["*"]}]}'
),
(
    'TeamManagement',
    'Full access to manage teams and team members',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "TeamManagement", "Effect": "Allow", "Action": ["team:create", "team:modify", "team:get", "team:list", "team:read", "team:delete", "member:create", "member:modify", "member:get", "member:list", "member:read", "member:delete"], "Resource": ["*"]}]}'
),
(
    'ReadOnlyAccess',
    'Read-only access to all resources',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "ReadOnlyAccess", "Effect": "Allow", "Action": ["*:read", "*:list", "*:get"], "Resource": ["*"]}]}'
),
(
    'DeploymentManagement',
    'Full access to manage deployments and view teams',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "DeploymentManagement", "Effect": "Allow", "Action": ["team:read", "team:list", "team:get", "deployment:create", "deployment:modify", "deployment:get", "deployment:list", "deployment:read", "deployment:delete"], "Resource": ["*"]}]}'
),
(
    'WorkspaceManagement',
    'Full access to manage workspaces (delete denied)',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "WorkspaceManagement", "Effect": "Allow", "Action": ["workspace:create", "workspace:modify", "workspace:get", "workspace:list", "workspace:read"], "Resource": ["workspace:*"]}, {"Sid": "DenyWorkspaceDelete", "Effect": "Deny", "Action": ["workspace:delete"], "Resource": ["workspace:*"]}]}'
),
(
    'UserManagement',
    'Full access to manage users (delete denied)',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "UserManagement", "Effect": "Allow", "Action": ["user:create", "user:modify", "user:get", "user:list", "user:read"], "Resource": ["user:*"]}, {"Sid": "DenyUserDelete", "Effect": "Deny", "Action": ["user:delete"], "Resource": ["user:*"]}]}'
),
(
    'RoleAndPolicyViewer',
    'Read-only access to view roles and policies',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "RoleAndPolicyViewer", "Effect": "Allow", "Action": ["role:get", "role:list", "role:read", "policy:get", "policy:list", "policy:read"], "Resource": ["*"]}]}'
);

-- Seed Default Roles (Linked to Policies)
-- Roles use kebab-case naming convention
-- Note: Roles with read access allow reading resource definitions and configurations
INSERT INTO roles (name, description) VALUES
('administrator', 'Full administrative access to all resources'),
('team-manager', 'Full access to manage teams and team members'),
('read-only-viewer', 'Read-only access to all resources'),
('deployment-manager', 'Full access to manage deployments and view teams'),
('workspace-manager', 'Full access to manage workspaces (agents & workflows)'),
('user-manager', 'Full access to manage users'),
('role-viewer', 'Read-only access to view roles and policies');

-- Link Roles to Policies
INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'administrator' AND p.name = 'AdministratorAccess';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'team-manager' AND p.name = 'TeamManagement';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'read-only-viewer' AND p.name = 'ReadOnlyAccess';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'deployment-manager' AND p.name = 'DeploymentManagement';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'workspace-manager' AND p.name = 'WorkspaceManagement';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'user-manager' AND p.name = 'UserManagement';

INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'role-viewer' AND p.name = 'RoleAndPolicyViewer';

-- Create root user with admin role (bypassing RLS temporarily)
-- This ensures root user exists on first-time setup with administrator role attached
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles DISABLE ROW LEVEL SECURITY;

-- Create root user if it doesn't exist
-- Password: admin (bcrypt hash)
INSERT INTO users (username, email, password_hash, full_name) 
SELECT 'root', 'root@aegis.local', '$2b$12$SGyhdYqrQCjlcdfSnvTPS.fWNBCE.6cojJ3/ExZ/MG99BwtG5.Q82', 'Root Administrator'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'root');

-- Assign administrator role to root user (if not already assigned)
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'root' 
  AND r.name = 'administrator'
  AND NOT EXISTS (
    SELECT 1 FROM user_roles ur 
    WHERE ur.user_id = u.id AND ur.role_id = r.id
  );

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

-- Helper function to check if current user has administrator role
CREATE OR REPLACE FUNCTION current_user_is_admin() RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = current_setting('app.current_user_id', true)::uuid
        AND r.name = 'administrator'
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
-- Note: read, get, and list actions allow reading resource definitions and configurations
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
    user_id_str TEXT;
BEGIN
    -- Safely get user_id, handling NULL and empty string
    user_id_str := current_setting('app.current_user_id', true);
    
    IF user_id_str IS NULL OR user_id_str = '' THEN
        RETURN FALSE;
    END IF;
    
    BEGIN
        user_uuid := user_id_str::uuid;
    EXCEPTION WHEN OTHERS THEN
        RETURN FALSE;
    END;
    
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

-- Helper function to check if policy is attached to any roles (bypasses RLS)
CREATE OR REPLACE FUNCTION check_policy_attached_to_roles(policy_uuid UUID) 
RETURNS TABLE(role_id UUID, role_name VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT r.id, r.name
    FROM roles r
    JOIN role_policies rp ON r.id = rp.role_id
    WHERE rp.policy_id = policy_uuid
    LIMIT 5;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to check if role is attached to users or teams (bypasses RLS)
CREATE OR REPLACE FUNCTION check_role_attachments(role_uuid UUID) 
RETURNS TABLE(
    attachment_type TEXT,
    user_id UUID,
    username VARCHAR,
    team_id UUID,
    team_name VARCHAR
) AS $$
BEGIN
    -- Check user_roles
    RETURN QUERY
    SELECT 
        'user'::TEXT,
        u.id,
        u.username,
        NULL::UUID,
        NULL::VARCHAR
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    WHERE ur.role_id = role_uuid
    LIMIT 5;
    
    -- Check team_roles
    RETURN QUERY
    SELECT 
        'team'::TEXT,
        NULL::UUID,
        NULL::VARCHAR,
        t.id,
        t.name
    FROM teams t
    JOIN team_roles tr ON t.id = tr.team_id
    WHERE tr.role_id = role_uuid
    LIMIT 5;
    
    -- Check team_members
    RETURN QUERY
    SELECT 
        'team_member'::TEXT,
        u.id,
        u.username,
        t.id,
        t.name
    FROM team_members tm
    JOIN users u ON tm.user_id = u.id
    JOIN teams t ON tm.team_id = t.id
    WHERE tm.role_id = role_uuid
    LIMIT 5;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS Policies (RBAC)

-- 1. Users Table
-- Read/List/Get: Admins see all, users with allow policy see users (unless denied)
-- Read access allows viewing user definitions, profiles, email, and role assignments
-- Deny has higher priority - if user has deny policy for a user, they can't see it
CREATE POLICY users_read_own ON users
    FOR SELECT
    USING (
        current_user_is_admin()
        OR current_setting('app.current_user_id', true) IS NULL
        OR current_setting('app.current_user_id', true) = ''
        OR evaluate_policy_permission('user:read', 'user', 'user:' || username)
        OR evaluate_policy_permission('user:list', 'user', 'user:' || username)
        OR evaluate_policy_permission('user:get', 'user', 'user:' || username)
    );

-- Insert: Anyone can create a user (for registration), but they get no access until roles assigned
-- This allows unauthenticated registration (no app.current_user_id set)
CREATE POLICY users_insert ON users
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_user_id', true) IS NULL 
        OR current_setting('app.current_user_id', true) = ''
        OR current_user_is_admin()
        OR evaluate_policy_permission('user:create', 'user', NULL)
    );

-- Update: Only admins can update users (zero-trust: no access without roles)
CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('user:modify', 'user', 'user:' || username)
    );

-- Delete: Only admins can delete users
CREATE POLICY users_delete ON users
    FOR DELETE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('user:delete', 'user', 'user:' || username)
    );

-- 2. Roles Table
-- Read/List/Get: Admins see all, users with allow policy see roles (unless denied)
-- Read access allows viewing role definitions, descriptions, and attached policies
-- Deny has higher priority - if user has deny policy for a role, they can't see it
CREATE POLICY roles_read_access ON roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('role:read', 'role', 'role:' || name)
        OR evaluate_policy_permission('role:list', 'role', 'role:' || name)
        OR evaluate_policy_permission('role:get', 'role', 'role:' || name)
    );

-- Insert: Only admins can create roles (zero-trust: no access without roles)
CREATE POLICY roles_insert ON roles
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR evaluate_policy_permission('role:create', 'role', NULL)
    );

-- Update: Only admins can update roles (zero-trust: no access without roles)
CREATE POLICY roles_update ON roles
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('role:modify', 'role', 'role:' || name)
    );

-- Delete: Only admins can delete roles (zero-trust: no access without roles)
CREATE POLICY roles_delete ON roles
    FOR DELETE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('role:delete', 'role', 'role:' || name)
    );

-- 3. Teams Table
-- Read/List/Get: Admins see all, users with allow policy see teams (unless denied)
-- Read access allows viewing team definitions, descriptions, and member information
-- Deny has higher priority - if user has deny policy for a team, they can't see it
CREATE POLICY teams_read_access ON teams
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('team:read', 'team', 'team:' || name)
        OR evaluate_policy_permission('team:list', 'team', 'team:' || name)
        OR evaluate_policy_permission('team:get', 'team', 'team:' || name)
    );

-- Insert: Any authenticated user can create a team (must be owner)
CREATE POLICY teams_insert ON teams
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('team:create', 'team', NULL)
    );

-- Update: Owner can update. Members with permission handled by API (RLS allows if member for now to support fine-grained)
-- NOTE: Strictly speaking, RLS should check permissions. For simplicity in this hybrid model,
-- we allow members to "see" the row for update, but API prevents actual change if no permission.
-- To be safer, we restrict UPDATE to Owner only in RLS, and rely on Owner to delegate?
-- No, that defeats the purpose of roles.
CREATE POLICY teams_update ON teams
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('team:modify', 'team', 'team:' || name)
    );

-- Delete: Owner or admin can delete
CREATE POLICY teams_delete ON teams
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('team:delete', 'team', 'team:' || name)
    );
-- 4. Team Members Table
-- Read/List/Get: Visible if member of the same team
CREATE POLICY team_members_read_access ON team_members
    FOR SELECT
    USING (
        user_id = current_setting('app.current_user_id', true)::uuid
        OR current_user_is_admin()
        OR evaluate_policy_permission('member:read', 'member', NULL)
        OR evaluate_policy_permission('member:list', 'member', NULL)
        OR evaluate_policy_permission('member:get', 'member', NULL)
    );

-- Insert: Only team owners or admins can add members
CREATE POLICY team_members_insert ON team_members
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('member:create', 'member', NULL)
    );

-- Update: Only team owners or admins can modify members
CREATE POLICY team_members_update ON team_members
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('member:modify', 'member', NULL)
    );

-- Delete: Only team owners or admins can remove members
CREATE POLICY team_members_delete ON team_members
    FOR DELETE
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('member:delete', 'member', NULL)
    );

-- 5. User Roles Table
-- Read/List/Get: Admins see all, users see their own role assignments
CREATE POLICY user_roles_read_access ON user_roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR user_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('user_role:read', 'user_role', NULL)
        OR evaluate_policy_permission('user_role:list', 'user_role', NULL)
        OR evaluate_policy_permission('user_role:get', 'user_role', NULL)
    );

-- Insert: Admins or users with user:modify permission can assign roles
CREATE POLICY user_roles_insert ON user_roles
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR evaluate_policy_permission('user_role:create', 'user_role', NULL)
        OR evaluate_policy_permission('user:modify', 'user', NULL)
    );

-- Delete: Admins or users with user:modify permission can remove role assignments
CREATE POLICY user_roles_delete ON user_roles
    FOR DELETE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('user_role:delete', 'user_role', NULL)
        OR evaluate_policy_permission('user:modify', 'user', NULL)
    );

-- 6. Team Roles Table
-- Read/List/Get: Only admins can see team roles (team membership checked in API layer)
CREATE POLICY team_roles_read_access ON team_roles
    FOR SELECT
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('team_role:read', 'team_role', NULL)
        OR evaluate_policy_permission('team_role:list', 'team_role', NULL)
        OR evaluate_policy_permission('team_role:get', 'team_role', NULL)
    );

-- Insert: Team owners, admins, or users with team:modify permission
CREATE POLICY team_roles_insert ON team_roles
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('team_role:create', 'team_role', NULL)
        OR evaluate_policy_permission('team:modify', 'team', NULL)
    );

-- Delete: Team owners, admins, or users with team:modify permission
CREATE POLICY team_roles_delete ON team_roles
    FOR DELETE
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM teams
            WHERE id = team_id
            AND owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('team_role:delete', 'team_role', NULL)
        OR evaluate_policy_permission('team:modify', 'team', NULL)
    );

-- 7. Policies Table
-- Read/List/Get: Admins see all, users with allow policy see policies (unless denied)
-- Read access allows viewing policy definitions, descriptions, and full policy content (JSON)
-- Deny has higher priority - if user has deny policy for a policy, they can't see it
CREATE POLICY policies_read_access ON policies
    FOR SELECT
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('policy:read', 'policy', 'policy:' || name)
        OR evaluate_policy_permission('policy:list', 'policy', 'policy:' || name)
        OR evaluate_policy_permission('policy:get', 'policy', 'policy:' || name)
    );

-- Insert: Only admins can create policies (zero-trust: no access without roles)
CREATE POLICY policies_insert ON policies
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR evaluate_policy_permission('policy:create', 'policy', NULL)
    );

-- Update: Only admins can update policies (zero-trust: no access without roles)
CREATE POLICY policies_update ON policies
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('policy:modify', 'policy', 'policy:' || name)
    );

-- Delete: Only admins can delete policies (zero-trust: no access without roles)
CREATE POLICY policies_delete ON policies
    FOR DELETE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('policy:delete', 'policy', 'policy:' || name)
    );

-- 6. Role Policies Table
-- Read: Admins see all, users with roles can see role policies
CREATE POLICY role_policies_read_access ON role_policies
    FOR SELECT
    USING (
        current_user_is_admin()
        OR current_user_has_any_role()
    );

-- Insert: Admins or users with role:modify permission can attach policies to roles
CREATE POLICY role_policies_insert ON role_policies
    FOR INSERT
    WITH CHECK (
        current_user_is_admin()
        OR evaluate_policy_permission('role:modify', 'role', NULL)
    );

-- Delete: Admins or users with role:modify permission can detach policies from roles
CREATE POLICY role_policies_delete ON role_policies
    FOR DELETE
    USING (
        current_user_is_admin()
        OR evaluate_policy_permission('role:modify', 'role', NULL)
    );

-- 8. Workspaces Table
-- Read/List/Get: Admins see all, owners see their own, users with allow policy see workspaces (unless denied)
-- Read access allows viewing workspace definitions, descriptions, and content (agent/workflow configurations)
CREATE POLICY workspaces_read_access ON workspaces
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workspace:read', 'workspace', 'workspace:' || name)
        OR evaluate_policy_permission('workspace:list', 'workspace', 'workspace:' || name)
        OR evaluate_policy_permission('workspace:get', 'workspace', 'workspace:' || name)
    );

-- Insert: Any authenticated user can create a workspace
CREATE POLICY workspaces_insert ON workspaces
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workspace:create', 'workspace', NULL)
    );

-- Update: Owner or admin can update
CREATE POLICY workspaces_update ON workspaces
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workspace:modify', 'workspace', 'workspace:' || name)
    );

-- Delete: Owner or admin can delete
CREATE POLICY workspaces_delete ON workspaces
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workspace:delete', 'workspace', 'workspace:' || name)
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

-- ============================================
-- AEGIS AGENT FRAMEWORK TABLES
-- ============================================

-- Agents Table - stores agent definitions
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    model VARCHAR(100) NOT NULL DEFAULT 'gemini/gemini-2.0-flash',
    instructions TEXT NOT NULL DEFAULT 'You are a helpful agent.',
    tools JSONB DEFAULT '[]',  -- List of tool names
    tool_choice VARCHAR(50),
    parallel_tool_calls BOOLEAN DEFAULT FALSE,
    capabilities JSONB DEFAULT '[]',  -- Agent capabilities for routing
    autonomous_mode BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, active, inactive
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflows Table - stores workflow definitions
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    steps JSONB DEFAULT '[]',  -- Array of workflow steps
    execution_mode VARCHAR(20) NOT NULL DEFAULT 'sequential',  -- sequential, parallel
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, active, inactive
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Runs Table - stores execution history
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_type VARCHAR(20) NOT NULL,  -- 'agent' or 'workflow'
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    input_message TEXT NOT NULL,
    context_variables JSONB DEFAULT '{}',
    output TEXT,
    error TEXT,
    step_results JSONB DEFAULT '[]',  -- For workflow runs
    messages JSONB DEFAULT '[]',  -- Conversation history
    tool_calls JSONB DEFAULT '[]',  -- Tool call log
    tokens_used INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_run_type CHECK (
        (run_type = 'agent' AND agent_id IS NOT NULL) OR
        (run_type = 'workflow' AND workflow_id IS NOT NULL)
    )
);

-- Indexes for performance
CREATE INDEX idx_agents_owner_id ON agents(owner_id);
CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_workflows_owner_id ON workflows(owner_id);
CREATE INDEX idx_workflows_name ON workflows(name);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_agent_runs_owner_id ON agent_runs(owner_id);
CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_workflow_id ON agent_runs(workflow_id);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_created_at ON agent_runs(created_at DESC);

-- Triggers for updated_at
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

-- Force RLS
ALTER TABLE agents FORCE ROW LEVEL SECURITY;
ALTER TABLE workflows FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_runs FORCE ROW LEVEL SECURITY;

-- RLS Policies for Agents
CREATE POLICY agents_read_access ON agents
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:read', 'agent', 'agent:' || name)
        OR evaluate_policy_permission('agent:list', 'agent', 'agent:' || name)
        OR evaluate_policy_permission('agent:get', 'agent', 'agent:' || name)
    );

CREATE POLICY agents_insert ON agents
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:create', 'agent', NULL)
    );

CREATE POLICY agents_update ON agents
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:modify', 'agent', 'agent:' || name)
    );

CREATE POLICY agents_delete ON agents
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:delete', 'agent', 'agent:' || name)
    );

-- RLS Policies for Workflows
CREATE POLICY workflows_read_access ON workflows
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workflow:read', 'workflow', 'workflow:' || name)
        OR evaluate_policy_permission('workflow:list', 'workflow', 'workflow:' || name)
        OR evaluate_policy_permission('workflow:get', 'workflow', 'workflow:' || name)
    );

CREATE POLICY workflows_insert ON workflows
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workflow:create', 'workflow', NULL)
    );

CREATE POLICY workflows_update ON workflows
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workflow:modify', 'workflow', 'workflow:' || name)
    );

CREATE POLICY workflows_delete ON workflows
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('workflow:delete', 'workflow', 'workflow:' || name)
    );

-- RLS Policies for Agent Runs
CREATE POLICY agent_runs_read_access ON agent_runs
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('run:read', 'run', NULL)
        OR evaluate_policy_permission('run:list', 'run', NULL)
        OR evaluate_policy_permission('run:get', 'run', NULL)
    );

CREATE POLICY agent_runs_insert ON agent_runs
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('run:create', 'run', NULL)
    );

CREATE POLICY agent_runs_update ON agent_runs
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('run:modify', 'run', NULL)
    );

CREATE POLICY agent_runs_delete ON agent_runs
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('run:delete', 'run', NULL)
    );

-- Add Agent Management policy
INSERT INTO policies (name, description, content) VALUES
(
    'AgentManagement',
    'Full access to manage agents and workflows',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "AgentManagement", "Effect": "Allow", "Action": ["agent:create", "agent:modify", "agent:get", "agent:list", "agent:read", "agent:delete", "workflow:create", "workflow:modify", "workflow:get", "workflow:list", "workflow:read", "workflow:delete", "run:create", "run:get", "run:list", "run:read"], "Resource": ["*"]}]}'
);

-- Create agent-manager role
INSERT INTO roles (name, description) VALUES
('agent-manager', 'Full access to manage agents and workflows');

-- Link role to policy
INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'agent-manager' AND p.name = 'AgentManagement';

-- Grant aegis_app access to new tables
GRANT SELECT, INSERT, UPDATE, DELETE ON agents TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON workflows TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_runs TO aegis_app;

-- ============================================
-- ENHANCED AGENT CAPABILITIES TABLES
-- ============================================

-- Agent Files Table - stores file attachments for agents
CREATE TABLE agent_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,
    content_type VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE
);

-- Custom Tools Table - stores user-defined tools
CREATE TABLE custom_tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    definition_type VARCHAR(20) NOT NULL DEFAULT 'json', -- 'python' or 'json'
    definition JSONB, -- JSON tool definition
    code_content TEXT, -- Python code content
    code_file_path TEXT, -- Path to Python file
    parameters JSONB DEFAULT '[]', -- Tool parameters schema
    return_type VARCHAR(100),
    config JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- MCP Servers Table - stores MCP server configurations
CREATE TABLE mcp_servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    server_type VARCHAR(20) NOT NULL DEFAULT 'external', -- 'external' or 'custom'
    transport_type VARCHAR(20) NOT NULL DEFAULT 'stdio', -- 'stdio', 'http', 'sse'
    endpoint_url TEXT, -- For HTTP/SSE transport
    command TEXT, -- For stdio transport (e.g., 'npx -y @modelcontextprotocol/server-filesystem')
    args JSONB DEFAULT '[]', -- Command arguments
    env_vars JSONB DEFAULT '{}', -- Environment variables
    config JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'inactive', -- 'active', 'inactive', 'error'
    last_connected_at TIMESTAMP WITH TIME ZONE,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent MCP Servers Junction Table - links agents to MCP servers
CREATE TABLE agent_mcp_servers (
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    mcp_server_id UUID REFERENCES mcp_servers(id) ON DELETE CASCADE,
    attached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    config JSONB DEFAULT '{}', -- Agent-specific MCP config overrides
    PRIMARY KEY (agent_id, mcp_server_id)
);

-- Agent Custom Tools Junction Table - links agents to custom tools
CREATE TABLE agent_custom_tools (
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    custom_tool_id UUID REFERENCES custom_tools(id) ON DELETE CASCADE,
    attached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, custom_tool_id)
);

-- Indexes for performance
CREATE INDEX idx_agent_files_agent_id ON agent_files(agent_id);
CREATE INDEX idx_agent_files_owner_id ON agent_files(owner_id);
CREATE INDEX idx_custom_tools_owner_id ON custom_tools(owner_id);
CREATE INDEX idx_custom_tools_name ON custom_tools(name);
CREATE INDEX idx_mcp_servers_owner_id ON mcp_servers(owner_id);
CREATE INDEX idx_mcp_servers_status ON mcp_servers(status);
CREATE INDEX idx_agent_mcp_servers_agent_id ON agent_mcp_servers(agent_id);
CREATE INDEX idx_agent_custom_tools_agent_id ON agent_custom_tools(agent_id);

-- Triggers for updated_at
CREATE TRIGGER update_custom_tools_updated_at
    BEFORE UPDATE ON custom_tools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mcp_servers_updated_at
    BEFORE UPDATE ON mcp_servers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE agent_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_mcp_servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_custom_tools ENABLE ROW LEVEL SECURITY;

-- Force RLS
ALTER TABLE agent_files FORCE ROW LEVEL SECURITY;
ALTER TABLE custom_tools FORCE ROW LEVEL SECURITY;
ALTER TABLE mcp_servers FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_mcp_servers FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_custom_tools FORCE ROW LEVEL SECURITY;

-- RLS Policies for Agent Files
CREATE POLICY agent_files_read_access ON agent_files
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:read', 'agent', NULL)
    );

CREATE POLICY agent_files_insert ON agent_files
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:modify', 'agent', NULL)
    );

CREATE POLICY agent_files_delete ON agent_files
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('agent:modify', 'agent', NULL)
    );

-- RLS Policies for Custom Tools
CREATE POLICY custom_tools_read_access ON custom_tools
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('tool:read', 'tool', NULL)
    );

CREATE POLICY custom_tools_insert ON custom_tools
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('tool:create', 'tool', NULL)
    );

CREATE POLICY custom_tools_update ON custom_tools
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('tool:modify', 'tool', NULL)
    );

CREATE POLICY custom_tools_delete ON custom_tools
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('tool:delete', 'tool', NULL)
    );

-- RLS Policies for MCP Servers
CREATE POLICY mcp_servers_read_access ON mcp_servers
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('mcp:read', 'mcp', NULL)
    );

CREATE POLICY mcp_servers_insert ON mcp_servers
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('mcp:create', 'mcp', NULL)
    );

CREATE POLICY mcp_servers_update ON mcp_servers
    FOR UPDATE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('mcp:modify', 'mcp', NULL)
    );

CREATE POLICY mcp_servers_delete ON mcp_servers
    FOR DELETE
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR evaluate_policy_permission('mcp:delete', 'mcp', NULL)
    );

-- RLS Policies for Junction Tables (based on agent ownership)
CREATE POLICY agent_mcp_servers_access ON agent_mcp_servers
    FOR ALL
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.id = agent_mcp_servers.agent_id 
            AND a.owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('agent:modify', 'agent', NULL)
    );

CREATE POLICY agent_custom_tools_access ON agent_custom_tools
    FOR ALL
    USING (
        current_user_is_admin()
        OR EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.id = agent_custom_tools.agent_id 
            AND a.owner_id = current_setting('app.current_user_id', true)::uuid
        )
        OR evaluate_policy_permission('agent:modify', 'agent', NULL)
    );

-- Grant access to aegis_app
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_files TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON custom_tools TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON mcp_servers TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_mcp_servers TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_custom_tools TO aegis_app;

-- Update agents table to reference custom tools list
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS custom_tool_ids JSONB DEFAULT '[]';
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS mcp_server_ids JSONB DEFAULT '[]';
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS file_ids JSONB DEFAULT '[]';

-- Add ToolManagement policy
INSERT INTO policies (name, description, content) VALUES
(
    'ToolManagement',
    'Full access to manage custom tools and MCP servers',
    '{"Version": "2012-10-17", "Statement": [{"Sid": "ToolManagement", "Effect": "Allow", "Action": ["tool:create", "tool:modify", "tool:get", "tool:list", "tool:read", "tool:delete", "mcp:create", "mcp:modify", "mcp:get", "mcp:list", "mcp:read", "mcp:delete"], "Resource": ["*"]}]}'
);

-- Create tool-manager role
INSERT INTO roles (name, description) VALUES
('tool-manager', 'Full access to manage custom tools and MCP servers');

-- Link role to policy
INSERT INTO role_policies (role_id, policy_id)
SELECT r.id, p.id FROM roles r, policies p WHERE r.name = 'tool-manager' AND p.name = 'ToolManagement';

-- ============================================
-- AI PROVIDER & API KEYS MANAGEMENT
-- ============================================

-- API Keys Table - stores user's API keys for different AI providers
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'google', 'azure', 'groq', 'cohere', 'mistral', 'together'
    api_key_encrypted TEXT NOT NULL, -- Encrypted API key
    api_key_preview VARCHAR(20), -- Last 4 chars for display
    base_url TEXT, -- Custom base URL for Azure/custom endpoints
    organization_id VARCHAR(100), -- For OpenAI organization
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Models Table - stores available AI models configuration
CREATE TABLE ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL, -- e.g., 'gpt-4', 'claude-3-opus'
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    capabilities JSONB DEFAULT '[]', -- ['chat', 'vision', 'function_calling', 'streaming']
    context_window INTEGER DEFAULT 4096,
    max_output_tokens INTEGER,
    input_cost_per_1k DECIMAL(10, 6), -- Cost per 1000 input tokens
    output_cost_per_1k DECIMAL(10, 6), -- Cost per 1000 output tokens
    supports_streaming BOOLEAN DEFAULT TRUE,
    supports_tools BOOLEAN DEFAULT TRUE,
    supports_vision BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Topics Table - conversation flow topics (like Copilot Studio)
CREATE TABLE agent_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL DEFAULT 'phrase', -- 'phrase', 'event', 'intent', 'schedule'
    trigger_phrases JSONB DEFAULT '[]', -- Trigger words/phrases
    trigger_config JSONB DEFAULT '{}', -- Additional trigger configuration
    conversation_flow JSONB DEFAULT '[]', -- Conversation nodes and transitions
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Actions Table - external actions/connectors
CREATE TABLE agent_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    action_type VARCHAR(50) NOT NULL, -- 'http', 'webhook', 'database', 'email', 'slack', 'custom'
    config JSONB NOT NULL DEFAULT '{}', -- Action configuration
    input_schema JSONB DEFAULT '{}', -- Input parameters schema
    output_schema JSONB DEFAULT '{}', -- Expected output schema
    authentication JSONB DEFAULT '{}', -- Auth config (oauth, api_key, etc.)
    is_enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Knowledge Base Table - enhanced knowledge management
CREATE TABLE agent_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'file', 'url', 'text', 'database', 'sharepoint', 'notion'
    source_url TEXT, -- For URL-based sources
    content TEXT, -- For text content or extracted content
    content_hash VARCHAR(64), -- For detecting changes
    file_path TEXT, -- For file-based sources
    file_type VARCHAR(50),
    file_size BIGINT,
    chunk_count INTEGER DEFAULT 0,
    embedding_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    last_synced_at TIMESTAMP WITH TIME ZONE,
    sync_frequency VARCHAR(20) DEFAULT 'manual', -- 'manual', 'hourly', 'daily', 'weekly'
    is_enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_api_keys_owner_id ON api_keys(owner_id);
CREATE INDEX idx_api_keys_provider ON api_keys(provider);
CREATE INDEX idx_ai_models_provider ON ai_models(provider);
CREATE INDEX idx_ai_models_model_id ON ai_models(model_id);
CREATE INDEX idx_agent_topics_agent_id ON agent_topics(agent_id);
CREATE INDEX idx_agent_actions_agent_id ON agent_actions(agent_id);
CREATE INDEX idx_agent_knowledge_agent_id ON agent_knowledge(agent_id);

-- Triggers for updated_at
CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_topics_updated_at
    BEFORE UPDATE ON agent_topics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_actions_updated_at
    BEFORE UPDATE ON agent_actions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_knowledge_updated_at
    BEFORE UPDATE ON agent_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge ENABLE ROW LEVEL SECURITY;

-- Force RLS
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_models FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_topics FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_actions FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge FORCE ROW LEVEL SECURITY;

-- RLS Policies for API Keys (private to owner)
CREATE POLICY api_keys_read_access ON api_keys
    FOR SELECT
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY api_keys_insert ON api_keys
    FOR INSERT
    WITH CHECK (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY api_keys_update ON api_keys
    FOR UPDATE
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

CREATE POLICY api_keys_delete ON api_keys
    FOR DELETE
    USING (
        owner_id = current_setting('app.current_user_id', true)::uuid
    );

-- RLS Policies for AI Models (public read, admin write)
CREATE POLICY ai_models_read_access ON ai_models
    FOR SELECT
    USING (TRUE); -- Everyone can see available models

CREATE POLICY ai_models_admin ON ai_models
    FOR ALL
    USING (current_user_is_admin());

-- RLS Policies for Agent Topics
CREATE POLICY agent_topics_access ON agent_topics
    FOR ALL
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.id = agent_topics.agent_id 
            AND a.owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- RLS Policies for Agent Actions
CREATE POLICY agent_actions_access ON agent_actions
    FOR ALL
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.id = agent_actions.agent_id 
            AND a.owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- RLS Policies for Agent Knowledge
CREATE POLICY agent_knowledge_access ON agent_knowledge
    FOR ALL
    USING (
        current_user_is_admin()
        OR owner_id = current_setting('app.current_user_id', true)::uuid
        OR EXISTS (
            SELECT 1 FROM agents a 
            WHERE a.id = agent_knowledge.agent_id 
            AND a.owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Grant access to aegis_app
GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_models TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_topics TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_actions TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_knowledge TO aegis_app;

-- Seed popular AI models
INSERT INTO ai_models (provider, model_id, display_name, description, capabilities, context_window, max_output_tokens, supports_streaming, supports_tools, supports_vision) VALUES
-- OpenAI Models
('openai', 'gpt-4o', 'GPT-4o', 'Most capable GPT-4 model with vision', '["chat", "vision", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, TRUE),
('openai', 'gpt-4o-mini', 'GPT-4o Mini', 'Fast and affordable GPT-4 model', '["chat", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, FALSE),
('openai', 'gpt-4-turbo', 'GPT-4 Turbo', 'GPT-4 Turbo with 128k context', '["chat", "vision", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, TRUE),
('openai', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', 'Fast and efficient model', '["chat", "function_calling", "streaming"]', 16385, 4096, TRUE, TRUE, FALSE),
('openai', 'o1-preview', 'O1 Preview', 'Advanced reasoning model', '["chat", "reasoning"]', 128000, 32768, TRUE, FALSE, FALSE),
('openai', 'o1-mini', 'O1 Mini', 'Smaller reasoning model', '["chat", "reasoning"]', 128000, 65536, TRUE, FALSE, FALSE),

-- Anthropic Models
('anthropic', 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'Best balance of speed and intelligence', '["chat", "vision", "function_calling", "streaming"]', 200000, 8192, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-opus-20240229', 'Claude 3 Opus', 'Most capable Claude model', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-sonnet-20240229', 'Claude 3 Sonnet', 'Balanced performance', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-haiku-20240307', 'Claude 3 Haiku', 'Fastest Claude model', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),

-- Google Models
('google', 'gemini-2.0-flash', 'Gemini 2.0 Flash', 'Google''s latest fast model', '["chat", "vision", "function_calling", "streaming"]', 1000000, 8192, TRUE, TRUE, TRUE),
('google', 'gemini-1.5-pro', 'Gemini 1.5 Pro', 'Google''s most capable model', '["chat", "vision", "function_calling", "streaming"]', 2000000, 8192, TRUE, TRUE, TRUE),
('google', 'gemini-1.5-flash', 'Gemini 1.5 Flash', 'Fast and efficient Gemini', '["chat", "vision", "function_calling", "streaming"]', 1000000, 8192, TRUE, TRUE, TRUE),

-- Groq Models (Fast inference)
('groq', 'llama-3.3-70b-versatile', 'Llama 3.3 70B', 'Meta Llama 3.3 on Groq', '["chat", "function_calling", "streaming"]', 128000, 32768, TRUE, TRUE, FALSE),
('groq', 'llama-3.1-8b-instant', 'Llama 3.1 8B', 'Fast Llama model', '["chat", "streaming"]', 131072, 8192, TRUE, FALSE, FALSE),
('groq', 'mixtral-8x7b-32768', 'Mixtral 8x7B', 'Mixture of experts model', '["chat", "streaming"]', 32768, 32768, TRUE, FALSE, FALSE),

-- Mistral Models
('mistral', 'mistral-large-latest', 'Mistral Large', 'Most capable Mistral model', '["chat", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, FALSE),
('mistral', 'mistral-medium-latest', 'Mistral Medium', 'Balanced Mistral model', '["chat", "function_calling", "streaming"]', 32000, 4096, TRUE, TRUE, FALSE),
('mistral', 'mistral-small-latest', 'Mistral Small', 'Fast Mistral model', '["chat", "streaming"]', 32000, 4096, TRUE, FALSE, FALSE),

-- Together AI Models
('together', 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', 'Llama 3.1 70B Turbo', 'Fast Llama 70B on Together', '["chat", "function_calling", "streaming"]', 131072, 4096, TRUE, TRUE, FALSE),
('together', 'Qwen/Qwen2.5-72B-Instruct-Turbo', 'Qwen 2.5 72B', 'Alibaba Qwen model', '["chat", "function_calling", "streaming"]', 32768, 4096, TRUE, TRUE, FALSE),

-- Cohere Models
('cohere', 'command-r-plus', 'Command R+', 'Cohere''s most capable model', '["chat", "function_calling", "streaming", "rag"]', 128000, 4096, TRUE, TRUE, FALSE),
('cohere', 'command-r', 'Command R', 'Balanced Cohere model', '["chat", "function_calling", "streaming", "rag"]', 128000, 4096, TRUE, TRUE, FALSE);

-- Add model column to agents table for provider prefix support
-- Update agents to support provider/model format (e.g., 'openai/gpt-4o', 'anthropic/claude-3-opus')
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL;
