-- Migration script to update existing policies to use new action names
-- Actions: create, modify, get, list, read, delete (replacing: write, update, add, remove)

-- This script updates policies that may have been created with old action names
-- Run this if you have existing policies in your database that need updating

-- Migration script to update existing policies and roles to professional naming conventions
-- This script updates policies and roles that may have been created with old names

-- Update policy names to PascalCase
UPDATE policies SET name = 'AdministratorAccess' WHERE name = 'FullAccess';
UPDATE policies SET name = 'TeamManagement' WHERE name = 'TeamManage';
UPDATE policies SET name = 'ReadOnlyAccess' WHERE name = 'ReadOnly';
UPDATE policies SET name = 'DeploymentManagement' WHERE name = 'DeployAccess';
UPDATE policies SET name = 'WorkspaceManagement' WHERE name = 'WorkspaceManager';
UPDATE policies SET name = 'UserManagement' WHERE name = 'UserManager';
UPDATE policies SET name = 'RoleAndPolicyViewer' WHERE name = 'RoleViewer';

-- Update role names to kebab-case
UPDATE roles SET name = 'administrator' WHERE name = 'admin';
UPDATE roles SET name = 'team-manager' WHERE name = 'editor';
UPDATE roles SET name = 'read-only-viewer' WHERE name = 'viewer';
UPDATE roles SET name = 'deployment-manager' WHERE name = 'deployer';
-- workspace-manager, user-manager, role-viewer already follow convention

-- Update policy Statement Sids to match new policy names
UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"AdministratorAccess"'::jsonb
)
WHERE name = 'AdministratorAccess';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"TeamManagement"'::jsonb
)
WHERE name = 'TeamManagement';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"ReadOnlyAccess"'::jsonb
)
WHERE name = 'ReadOnlyAccess';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"DeploymentManagement"'::jsonb
)
WHERE name = 'DeploymentManagement';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"WorkspaceManagement"'::jsonb
)
WHERE name = 'WorkspaceManagement';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"UserManagement"'::jsonb
)
WHERE name = 'UserManagement';

UPDATE policies 
SET content = jsonb_set(
    content,
    '{Statement,0,Sid}',
    '"RoleAndPolicyViewer"'::jsonb
)
WHERE name = 'RoleAndPolicyViewer';

-- Generic update: Replace old action names with new ones in any policy
-- This handles custom policies that may have been created

-- Replace "write" with "create" and "modify"
UPDATE policies
SET content = jsonb_set(
    content,
    '{Statement}',
    (
        SELECT jsonb_agg(
            CASE 
                WHEN statement->'Action' IS NOT NULL THEN
                    jsonb_set(
                        statement,
                        '{Action}',
                        (
                            SELECT jsonb_agg(
                                CASE 
                                    WHEN action_text LIKE '%:write' THEN 
                                        jsonb_build_array(
                                            replace(action_text, ':write', ':create'),
                                            replace(action_text, ':write', ':modify')
                                        )
                                    WHEN action_text LIKE '%:update' THEN 
                                        replace(action_text, ':update', ':modify')
                                    WHEN action_text LIKE '%:add' THEN 
                                        replace(action_text, ':add', ':create')
                                    WHEN action_text LIKE '%:remove' THEN 
                                        replace(action_text, ':remove', ':delete')
                                    ELSE 
                                        jsonb_build_array(action_text)
                                END
                            )
                            FROM jsonb_array_elements_text(statement->'Action') AS action_text
                        )
                    )
                ELSE statement
            END
        )
        FROM jsonb_array_elements(content->'Statement') AS statement
    )
)
WHERE content::text LIKE '%:write%' 
   OR content::text LIKE '%:update%'
   OR content::text LIKE '%:add%'
   OR content::text LIKE '%:remove%';

-- Note: The above generic update is complex and may need manual verification
-- For safety, you may want to update policies individually

-- Verify updates
SELECT name, description, content 
FROM policies 
ORDER BY name;

