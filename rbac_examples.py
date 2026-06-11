#!/usr/bin/env python3
"""
RBAC Usage Examples
Demonstrates real-world usage of the RBAC system
"""

from rbac import RBACManager
from database import get_connection
import json


def example_1_check_permissions():
    """Example 1: Check user permissions"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Check User Permissions")
    print("="*70)
    
    connection = get_connection()
    rbac = RBACManager(connection)
    
    user_id = 1
    print(f"\nUser ID: {user_id}")
    
    # Get user role
    user_role = rbac.get_user_role(user_id)
    print(f"Role: {user_role['name'] if user_role else 'Unknown'}")
    
    # Get all permissions
    permissions = rbac.get_user_permissions(user_id)
    print(f"Permissions ({len(permissions)}):")
    for perm in permissions:
        print(f"  ✓ {perm}")
    
    # Check specific permissions
    print("\nPermission Checks:")
    checks = [
        ('asset.create', RBACManager.PERM_ASSET_CREATE),
        ('asset.delete', RBACManager.PERM_ASSET_DELETE),
        ('user.manage', RBACManager.PERM_USER_MANAGE),
    ]
    
    for desc, perm in checks:
        has_perm = rbac.has_permission(user_id, perm)
        status = "✓ CAN" if has_perm else "✗ CANNOT"
        print(f"  {status}: {desc}")
    
    connection.close()


def example_2_role_permissions():
    """Example 2: Show what each role can do"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Role Permission Matrix")
    print("="*70)
    
    connection = get_connection()
    rbac = RBACManager(connection)
    
    roles = [
        (RBACManager.ROLE_ADMIN, 'Admin'),
        (RBACManager.ROLE_TECHNICIAN, 'Technician'),
        (RBACManager.ROLE_USER, 'User'),
    ]
    
    for role_id, role_name in roles:
        permissions = rbac.get_role_permissions(role_id)
        print(f"\n{role_name} ({len(permissions)} permissions):")
        
        # Group permissions by type
        asset_perms = [p for p in permissions if p.startswith('asset.')]
        intervention_perms = [p for p in permissions if p.startswith('intervention.')]
        other_perms = [p for p in permissions if not p.startswith('asset.') and not p.startswith('intervention.')]
        
        if asset_perms:
            print("  Asset Management:")
            for perm in asset_perms:
                print(f"    ✓ {perm}")
        
        if intervention_perms:
            print("  Intervention Management:")
            for perm in intervention_perms:
                print(f"    ✓ {perm}")
        
        if other_perms:
            print("  Administration:")
            for perm in other_perms:
                print(f"    ✓ {perm}")
    
    connection.close()


def example_3_audit_logging():
    """Example 3: Log user actions"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Audit Logging")
    print("="*70)
    
    connection = get_connection()
    rbac = RBACManager(connection)
    
    print("\nLogging sample actions...")
    
    # Log an asset creation
    asset_data = json.dumps({
        "name": "Dell Laptop XPS 15",
        "brand": "Dell",
        "model": "XPS 15",
        "status": "Active"
    })
    
    rbac.audit_log(
        user_id=1,
        action='CREATE',
        entity_type='asset',
        entity_id=1,
        new_value=asset_data
    )
    print("  ✓ Logged: Asset creation")
    
    # Log an asset update
    old_data = json.dumps({"status": "Active"})
    new_data = json.dumps({"status": "Maintenance"})
    
    rbac.audit_log(
        user_id=1,
        action='UPDATE',
        entity_type='asset',
        entity_id=1,
        old_value=old_data,
        new_value=new_data
    )
    print("  ✓ Logged: Asset status update")
    
    # Log an intervention creation
    intervention_data = json.dumps({
        "description": "Replace hard drive",
        "technician": "João Silva",
        "date": "2024-01-15"
    })
    
    rbac.audit_log(
        user_id=1,
        action='CREATE',
        entity_type='intervention',
        entity_id=1,
        new_value=intervention_data
    )
    print("  ✓ Logged: Intervention creation")
    
    # Retrieve audit logs
    print("\nRetrieving audit logs...")
    logs = rbac.get_audit_logs(limit=10)
    
    print(f"\nRecent Actions ({len(logs)}):")
    for log in logs:
        print(f"  [{log['timestamp']}] User {log['user_id']}: {log['action']} on {log['entity_type']} #{log['entity_id']}")
    
    connection.close()


def example_4_permission_checks():
    """Example 4: Real-world permission checks"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Real-World Permission Checks")
    print("="*70)
    
    connection = get_connection()
    rbac = RBACManager(connection)
    
    user_id = 1
    
    # Simulate different actions that would need permission checks
    actions = [
        {
            'action': 'View Asset List',
            'permission': RBACManager.PERM_ASSET_VIEW,
            'endpoint': 'GET /api/assets'
        },
        {
            'action': 'Create New Asset',
            'permission': RBACManager.PERM_ASSET_CREATE,
            'endpoint': 'POST /api/assets'
        },
        {
            'action': 'Edit Asset',
            'permission': RBACManager.PERM_ASSET_EDIT,
            'endpoint': 'PUT /api/assets/:id'
        },
        {
            'action': 'Delete Asset',
            'permission': RBACManager.PERM_ASSET_DELETE,
            'endpoint': 'DELETE /api/assets/:id'
        },
        {
            'action': 'Manage Users',
            'permission': RBACManager.PERM_USER_MANAGE,
            'endpoint': 'POST /admin/users'
        },
        {
            'action': 'View Audit Logs',
            'permission': RBACManager.PERM_AUDIT_VIEW,
            'endpoint': 'GET /admin/audit'
        },
    ]
    
    print(f"\nAccess Control Check for User {user_id}:")
    print("-" * 70)
    
    for action in actions:
        has_perm = rbac.has_permission(user_id, action['permission'])
        status = "✓ ALLOWED" if has_perm else "✗ DENIED"
        
        print(f"\n  {status}: {action['action']}")
        print(f"           Permission: {action['permission']}")
        print(f"           Endpoint: {action['endpoint']}")
    
    connection.close()


def example_5_role_assignment():
    """Example 5: Assign roles to users"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Role Assignment")
    print("="*70)
    
    connection = get_connection()
    rbac = RBACManager(connection)
    
    print("\nCurrent User Assignments:")
    print("-" * 70)
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
    SELECT u.id, u.username, r.id as role_id, r.name as role_name
    FROM users u
    LEFT JOIN roles r ON u.role_id = r.id
    """)
    
    for user in cursor.fetchall():
        print(f"  User {user['id']}: {user['username']:20} → {user['role_name']}")
    
    cursor.close()
    
    print("\nExample: Assigning Technician role to user 1...")
    if rbac.assign_role_to_user(1, RBACManager.ROLE_TECHNICIAN):
        print("  ✓ Role assigned successfully")
        
        # Log the action
        rbac.audit_log(
            user_id=1,
            action='UPDATE',
            entity_type='user',
            entity_id=1,
            old_value='{"role_id": 1}',
            new_value='{"role_id": 2}'
        )
        print("  ✓ Action logged")
    else:
        print("  ✗ Failed to assign role")
    
    # Restore original role
    rbac.assign_role_to_user(1, RBACManager.ROLE_ADMIN)
    
    connection.close()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "RBAC SYSTEM - USAGE EXAMPLES" + " "*26 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        example_1_check_permissions()
        example_2_role_permissions()
        example_3_audit_logging()
        example_4_permission_checks()
        example_5_role_assignment()
        
        print("\n" + "="*70)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
