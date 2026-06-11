#!/usr/bin/env python3
import mysql.connector

def check_foreign_keys_and_fix():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="it_asset_management"
        )
        
        cursor = connection.cursor()
        
        print("="*60)
        print("CHECKING FOREIGN KEYS AND CONSTRAINTS")
        print("="*60)
        
        # Check if foreign key exists
        print("\n1. Checking if foreign key fk_users_role_id exists...")
        cursor.execute("""
        SELECT CONSTRAINT_NAME, TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'role_id'
        AND REFERENCED_TABLE_NAME IS NOT NULL;
        """)
        
        fk_results = cursor.fetchall()
        if fk_results:
            print(f"   ✓ Foreign key exists: {fk_results}")
        else:
            print("   ✗ Foreign key does not exist. Creating it...")
            try:
                cursor.execute("""
                ALTER TABLE users 
                ADD CONSTRAINT fk_users_role_id 
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL;
                """)
                connection.commit()
                print("   ✓ Foreign key created successfully")
            except mysql.connector.Error as err:
                print(f"   ✗ Error creating foreign key: {err}")
        
        # Check role_permissions foreign keys
        print("\n2. Checking role_permissions foreign keys...")
        cursor.execute("""
        SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = 'role_permissions' AND REFERENCED_TABLE_NAME IS NOT NULL;
        """)
        
        fk_results = cursor.fetchall()
        for row in fk_results:
            print(f"   ✓ {row[0]}: {row[2]} -> {row[3]}")
        
        # Check all indices
        print("\n3. Checking indices...")
        cursor.execute("""
        SELECT DISTINCT INDEX_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_NAME IN ('users', 'roles', 'permissions', 'role_permissions', 'audit_log')
        ORDER BY TABLE_NAME, INDEX_NAME;
        """)
        
        indices = cursor.fetchall()
        current_table = None
        for idx_name, col_name in indices:
            if current_table != idx_name:
                print(f"   {idx_name}:")
                current_table = idx_name
            print(f"      - {col_name}")
        
        # Check role assignments
        print("\n4. Checking user role assignments...")
        cursor.execute("""
        SELECT u.id, u.username, u.role, r.name as role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        ORDER BY u.id;
        """)
        
        users = cursor.fetchall()
        for user in users:
            print(f"   User ID {user[0]}: {user[1]:20} | String Role: {user[2]:15} | Assigned Role: {user[3]}")
        
        # Show role permissions
        print("\n5. Role Permissions Summary...")
        cursor.execute("""
        SELECT r.name as role_name, COUNT(p.id) as permission_count
        FROM roles r
        LEFT JOIN role_permissions rp ON r.id = rp.role_id
        LEFT JOIN permissions p ON rp.permission_id = p.id
        GROUP BY r.id, r.name
        ORDER BY r.id;
        """)
        
        role_perms = cursor.fetchall()
        for role_name, perm_count in role_perms:
            print(f"   {role_name}: {perm_count} permissions")
        
        # List all permissions
        print("\n6. All Permissions in System...")
        cursor.execute("SELECT id, name FROM permissions ORDER BY id;")
        
        perms = cursor.fetchall()
        for perm_id, perm_name in perms:
            print(f"   [{perm_id:2}] {perm_name}")
        
        print("\n" + "="*60)
        print("✓ VERIFICATION COMPLETE")
        print("="*60)
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_foreign_keys_and_fix()
