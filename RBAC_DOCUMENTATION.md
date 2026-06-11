# RBAC (Role-Based Access Control) Implementation

## Overview

The IT Asset Management application now includes a complete Role-Based Access Control (RBAC) system that replaces the simple string-based role field in the users table. This enables fine-grained permission management and audit logging.

## Database Schema

### 1. Roles Table

```sql
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Default Roles:**
- **Admin (ID: 1)**: Full access to all features including user management
- **Technician (ID: 2)**: Access to asset and intervention management
- **User (ID: 3)**: Read-only access to assets and interventions

### 2. Permissions Table

```sql
CREATE TABLE permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Available Permissions:**
- `asset.view` - View assets
- `asset.create` - Create new assets
- `asset.edit` - Edit existing assets
- `asset.delete` - Delete assets
- `intervention.view` - View interventions
- `intervention.create` - Create new interventions
- `intervention.edit` - Edit existing interventions
- `intervention.delete` - Delete interventions
- `technician.manage` - Manage technicians
- `user.manage` - Manage users and roles
- `audit.view` - View audit logs
- `category.manage` - Manage asset categories

### 3. Role-Permissions Junction Table

```sql
CREATE TABLE role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);
```

This many-to-many table defines which permissions are granted to each role.

### 4. Audit Log Table

```sql
CREATE TABLE audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INT,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

Tracks all user actions for audit and compliance purposes.

### 5. Updated Users Table

The existing `users` table has been updated with:
- New `role_id` column (INT, FK to roles.id)
- Foreign key constraint: `fk_users_role_id`
- Index on role_id for faster lookups

```sql
ALTER TABLE users ADD COLUMN role_id INT DEFAULT NULL;
ALTER TABLE users ADD CONSTRAINT fk_users_role_id 
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL;
CREATE INDEX idx_users_role_id ON users(role_id);
```

## Permission Matrix

### Admin Role
- ✓ All permissions (12 total)

### Technician Role
- ✓ asset.view
- ✓ asset.create
- ✓ asset.edit
- ✓ intervention.view
- ✓ intervention.create
- ✓ intervention.edit
- ✓ technician.manage
- Total: 7 permissions

### User Role
- ✓ asset.view
- ✓ intervention.view
- Total: 2 permissions

## Implementation Files

### 1. Migration File
**File**: `database/migration_002_add_roles_permissions.sql`

Idempotent migration that:
- Creates all required tables
- Inserts default roles and permissions
- Assigns permissions to roles
- Migrates existing users from string roles to role_id
- Creates necessary indices

**Usage**:
```bash
# Execute migration (can be run multiple times safely)
python execute_migration.py
```

### 2. RBAC Manager Module
**File**: `rbac.py`

Python module providing:
- `RBACManager` class for permission/role management
- Methods for checking permissions
- Audit logging functionality
- Decorators for route protection

**Key Methods**:
```python
from rbac import RBACManager, require_permission, require_role
from database import get_connection

# Get user permissions
connection = get_connection()
rbac = RBACManager(connection)
user_permissions = rbac.get_user_permissions(user_id)
has_perm = rbac.has_permission(user_id, 'asset.edit')

# Assign role
rbac.assign_role_to_user(user_id, RBACManager.ROLE_TECHNICIAN)

# Log action
rbac.audit_log(user_id, 'CREATE', 'asset', asset_id, None, json_data)

# Get audit logs
logs = rbac.get_audit_logs(limit=100, user_id=user_id)
```

## Usage Examples

### 1. Check User Permissions

```python
from rbac import RBACManager
from database import get_connection

connection = get_connection()
rbac = RBACManager(connection)

# Get all permissions for a user
user_permissions = rbac.get_user_permissions(user_id=1)
print(user_permissions)

# Check specific permission
if rbac.has_permission(user_id=1, permission='asset.create'):
    print("User can create assets")
else:
    print("User cannot create assets")

connection.close()
```

### 2. Protect Routes with Decorators

```python
from flask import Flask
from rbac import require_permission, require_role, RBACManager

app = Flask(__name__)

# Require specific permission
@app.route('/api/assets', methods=['POST'])
@require_permission(RBACManager.PERM_ASSET_CREATE)
def create_asset():
    return {"message": "Asset created"}

# Require specific role
@app.route('/admin/users')
@require_role(RBACManager.ROLE_ADMIN)
def manage_users():
    return {"message": "User management"}
```

### 3. Log User Actions

```python
from rbac import RBACManager
from database import get_connection

connection = get_connection()
rbac = RBACManager(connection)

# Log asset creation
rbac.audit_log(
    user_id=1,
    action='CREATE',
    entity_type='asset',
    entity_id=123,
    old_value=None,
    new_value='{"name": "New Asset", "status": "Active"}'
)

# Log asset update
rbac.audit_log(
    user_id=1,
    action='UPDATE',
    entity_type='asset',
    entity_id=123,
    old_value='{"status": "Active"}',
    new_value='{"status": "Inactive"}'
)

connection.close()
```

### 4. Retrieve Audit Logs

```python
from rbac import RBACManager
from database import get_connection

connection = get_connection()
rbac = RBACManager(connection)

# Get recent logs
logs = rbac.get_audit_logs(limit=20, offset=0)

# Get logs for specific user
user_logs = rbac.get_audit_logs(user_id=1)

# Get logs for specific entity type
asset_logs = rbac.get_audit_logs(entity_type='asset')

for log in logs:
    print(f"{log['timestamp']} - User {log['user_id']}: {log['action']} on {log['entity_type']} #{log['entity_id']}")

connection.close()
```

## Migration and Data

All existing users have been automatically migrated:
- Users with `role = 'admin'` → `role_id = 1` (Admin)
- Users with `role = 'technician'` → `role_id = 2` (Technician)
- All other users → `role_id = 3` (User)

## Verification

To verify the RBAC system is properly installed:

```bash
# Run verification script
python verify_rbac.py
```

This will check:
- All tables exist with correct structure
- Foreign keys are in place
- Default roles and permissions are inserted
- User role assignments are correct
- Role-permission mappings are valid

## Backwards Compatibility

The old `role` VARCHAR(50) column in the users table is still present for backwards compatibility. The system now uses `role_id` as the primary reference, but the string role can be maintained for legacy code.

To completely migrate legacy code:
1. Update application logic to use `role_id` instead of `role`
2. Use the RBAC manager for permission checks
3. Once fully migrated, the legacy `role` column can be dropped in a future migration

## Future Enhancements

1. **Custom Roles**: Add UI for creating custom roles
2. **Role Hierarchy**: Implement role inheritance (e.g., Technician inherits User permissions)
3. **Time-based Permissions**: Add expiration dates for role assignments
4. **Audit Reports**: Generate compliance reports from audit logs
5. **API Endpoints**: Add REST endpoints for RBAC management

## Database Indices

Created indices for performance:
- `idx_users_role_id` - Fast user role lookups
- `idx_role_permissions_permission_id` - Fast permission lookups
- `idx_audit_user_id` - Fast audit log filtering by user
- `idx_audit_timestamp` - Fast audit log filtering by time
- `idx_audit_entity` - Fast audit log filtering by entity

## Files Modified/Created

- **Created**: `database/migration_002_add_roles_permissions.sql`
- **Created**: `rbac.py`
- **Created**: `execute_migration.py`
- **Created**: `verify_rbac.py`
- **Created**: `RBAC_DOCUMENTATION.md`
- **Modified**: `database/it_asset_management.sql` (base schema)

## Rollback

To rollback the RBAC implementation:

```sql
-- Drop the new tables and constraints
ALTER TABLE users DROP FOREIGN KEY fk_users_role_id;
ALTER TABLE users DROP COLUMN role_id;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS audit_log;
```

However, this is not recommended as the role data will be lost.
