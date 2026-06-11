-- Migration: Add RBAC (Role-Based Access Control) system
-- Description: Implement roles, permissions, and audit logging for comprehensive access control

USE it_asset_management;

-- 1. Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create role_permissions junction table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

-- 4. Create audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_audit_user_id (user_id),
    INDEX idx_audit_timestamp (timestamp),
    INDEX idx_audit_entity (entity_type, entity_id)
);

-- 5. Update users table: add role_id column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INT DEFAULT NULL;

-- 6. Add foreign key constraint for role_id if it doesn't exist
-- Note: This will be added via separate script if needed
-- ALTER TABLE users ADD CONSTRAINT fk_users_role_id 
--     FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL;

-- Insert default roles
INSERT IGNORE INTO roles (id, name, description) VALUES
(1, 'Admin', 'Administrator with full access to all features and user management'),
(2, 'Technician', 'Technician with access to asset management and interventions'),
(3, 'User', 'Regular user with limited read-only access to assets');

-- Insert permissions
INSERT IGNORE INTO permissions (name, description) VALUES
('asset.view', 'View assets'),
('asset.create', 'Create new assets'),
('asset.edit', 'Edit existing assets'),
('asset.delete', 'Delete assets'),
('intervention.view', 'View interventions'),
('intervention.create', 'Create new interventions'),
('intervention.edit', 'Edit existing interventions'),
('intervention.delete', 'Delete interventions'),
('technician.manage', 'Manage technicians'),
('user.manage', 'Manage users and roles'),
('audit.view', 'View audit logs'),
('category.manage', 'Manage asset categories');

-- Assign permissions to Admin role (all permissions)
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions;

-- Assign permissions to Technician role
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT 2, id FROM permissions WHERE name IN (
    'asset.view', 'asset.create', 'asset.edit',
    'intervention.view', 'intervention.create', 'intervention.edit',
    'technician.manage'
);

-- Assign permissions to User role
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT 3, id FROM permissions WHERE name IN (
    'asset.view', 'intervention.view'
);

-- 7. Migrate existing users from string role to role_id
UPDATE users u
SET u.role_id = CASE
    WHEN LOWER(u.role) = 'admin' THEN 1
    WHEN LOWER(u.role) = 'technician' THEN 2
    ELSE 3
END
WHERE u.role_id IS NULL;

-- Set default role_id to User (3) for any remaining NULL values
UPDATE users SET role_id = 3 WHERE role_id IS NULL;

-- Create index for faster role lookups
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);
