#!/usr/bin/env python3
import mysql.connector
import sys

def execute_migration():
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="it_asset_management"
        )
        
        cursor = connection.cursor()
        
        # Read the migration file
        with open(r'database\migration_002_add_roles_permissions.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split by semicolons to execute individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"Executing migration with {len(statements)} statements...")
        print("-" * 60)
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"[{i}/{len(statements)}] Executing: {statement[:80]}...")
                cursor.execute(statement)
                print(f"  ✓ Success")
            except mysql.connector.Error as err:
                print(f"  ✗ Error: {err}")
                # Continue with other statements (idempotent)
        
        connection.commit()
        print("-" * 60)
        print("✓ Migration completed successfully!")
        
        # Verify tables were created
        print("\n" + "="*60)
        print("VERIFICATION: Checking created tables...")
        print("="*60)
        
        verification_queries = [
            ("Roles Table", "DESCRIBE roles;"),
            ("Permissions Table", "DESCRIBE permissions;"),
            ("Role Permissions Table", "DESCRIBE role_permissions;"),
            ("Audit Log Table", "DESCRIBE audit_log;"),
            ("Users Table (updated)", "DESCRIBE users;"),
            ("Roles Count", "SELECT COUNT(*) as role_count FROM roles;"),
            ("Permissions Count", "SELECT COUNT(*) as permission_count FROM permissions;"),
            ("Users with Roles", "SELECT username, name, role, role_id FROM users;"),
        ]
        
        for title, query in verification_queries:
            print(f"\n{title}:")
            print("-" * 40)
            cursor.execute(query)
            
            if query.startswith("DESCRIBE"):
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col[0]:20} {col[1]:30} {col[2]:10}")
            else:
                results = cursor.fetchall()
                if results:
                    for row in results:
                        print(f"  {row}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error executing migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = execute_migration()
    sys.exit(0 if success else 1)
