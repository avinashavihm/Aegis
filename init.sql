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
