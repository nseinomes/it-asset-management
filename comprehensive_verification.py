#!/usr/bin/env python3
"""
Comprehensive RBAC verification script
Validates all aspects of the RBAC implementation
"""

import mysql.connector
import json
from datetime import datetime

class RBACVerifier:
    def __init__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="it_asset_management"
        )
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'checks': {},
            'errors': []
        }
    
    def check_tables_exist(self):
        """Verify all RBAC tables exist"""
        print("\n" + "="*70)
        print("CHECK 1: RBAC Tables Existence")
        print("="*70)
        
        cursor = self.connection.cursor()
        tables_to_check = ['roles', 'permissions', 'role_permissions', 'audit_log']
        
        try:
            cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'it_asset_management'
            """)
            
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            table_check = {}
            for table in tables_to_check:
                exists = table in existing_tables
                status = "✓ EXISTS" if exists else "✗ MISSING"
                print(f"  {table:25} {status}")
                table_check[table] = exists
            
            self.results['checks']['tables_exist'] = all(table_check.values())
            
        finally:
            cursor.close()
    
    def check_table_structure(self):
        """Verify table structures"""
        print("\n" + "="*70)
        print("CHECK 2: Table Structures")
        print("="*70)
        
        cursor = self.connection.cursor()
        tables_columns = {
            'roles': ['id', 'name', 'description', 'created_at'],
            'permissions': ['id', 'name', 'description', 'created_at'],
            'role_permissions': ['role_id', 'permission_id'],
            'audit_log': ['id', 'user_id', 'action', 'entity_type', 'entity_id', 'old_value', 'new_value', 'timestamp'],
            'users': ['id', 'username', 'name', 'email', 'password', 'role', 'role_id']
        }
        
        structure_ok = True
        try:
            for table, expected_cols in tables_columns.items():
                print(f"\n  {table}:")
                cursor.execute(f"DESCRIBE {table}")
                existing_cols = {row[0] for row in cursor.fetchall()}
                
                for col in expected_cols:
                    exists = col in existing_cols
                    status = "✓" if exists else "✗"
                    print(f"    {status} {col}")
                    if not exists:
                        structure_ok = False
                        self.results['errors'].append(f"Missing column {col} in {table}")
            
            self.results['checks']['table_structure'] = structure_ok
        finally:
            cursor.close()
    
    def check_foreign_keys(self):
        """Verify foreign key constraints"""
        print("\n" + "="*70)
        print("CHECK 3: Foreign Key Constraints")
        print("="*70)
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
            SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'it_asset_management' 
            AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, CONSTRAINT_NAME
            """)
            
            fks = cursor.fetchall()
            print(f"\n  Found {len(fks)} foreign keys:\n")
            
            for constraint, table, column, ref_table, ref_column in fks:
                print(f"    ✓ {table}.{column} → {ref_table}.{ref_column}")
                print(f"      Constraint: {constraint}")
            
            required_fks = {
                'role_permissions': ['role_id', 'permission_id'],
                'audit_log': ['user_id'],
                'users': ['role_id']
            }
            
            fk_dict = {(row[1], row[2]): row[3] for row in fks}
            
            all_present = True
            for table, columns in required_fks.items():
                for col in columns:
                    if (table, col) not in fk_dict:
                        all_present = False
                        if table == 'users' and col == 'role_id':
                            print(f"\n  ! Warning: users.role_id FK may need manual creation")
            
            self.results['checks']['foreign_keys'] = all_present
            
        finally:
            cursor.close()
    
    def check_data_integrity(self):
        """Verify data in tables"""
        print("\n" + "="*70)
        print("CHECK 4: Data Integrity")
        print("="*70)
        
        cursor = self.connection.cursor()
        
        try:
            # Check roles
            cursor.execute("SELECT COUNT(*) FROM roles")
            role_count = cursor.fetchone()[0]
            print(f"\n  Roles: {role_count} records")
            cursor.execute("SELECT id, name FROM roles ORDER BY id")
            for role_id, role_name in cursor.fetchall():
                print(f"    [{role_id}] {role_name}")
            
            # Check permissions
            cursor.execute("SELECT COUNT(*) FROM permissions")
            perm_count = cursor.fetchone()[0]
            print(f"\n  Permissions: {perm_count} records")
            
            # Check role_permissions mappings
            cursor.execute("""
            SELECT r.name, COUNT(p.id) as permission_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            GROUP BY r.id, r.name
            ORDER BY r.id
            """)
            
            print(f"\n  Role-Permission Mappings:")
            for role_name, role_perm_count in cursor.fetchall():
                print(f"    {role_name}: {role_perm_count} permissions")
            
            # Check user assignments
            cursor.execute("""
            SELECT COUNT(*) FROM users WHERE role_id IS NOT NULL
            """)
            users_with_role = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            print(f"\n  Users with role assignments: {users_with_role}/{total_users}")
            
            cursor.execute("""
            SELECT u.id, u.username, u.role, r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            ORDER BY u.id
            """)
            
            print(f"\n  User Role Details:")
            for uid, username, old_role, new_role in cursor.fetchall():
                print(f"    ID {uid}: {username:20} (old: {old_role:12} new: {new_role})")
            
            integrity_ok = (role_count >= 3 and perm_count >= 12 and users_with_role == total_users)
            self.results['checks']['data_integrity'] = integrity_ok
            
            if not integrity_ok:
                if role_count < 3:
                    self.results['errors'].append(f"Expected at least 3 roles, found {role_count}")
                if perm_count < 12:
                    self.results['errors'].append(f"Expected at least 12 permissions, found {perm_count}")
                if users_with_role != total_users:
                    self.results['errors'].append(f"Not all users have roles: {users_with_role}/{total_users}")
            
        finally:
            cursor.close()
    
    def check_indices(self):
        """Verify performance indices"""
        print("\n" + "="*70)
        print("CHECK 5: Performance Indices")
        print("="*70)
        
        cursor = self.connection.cursor()
        
        required_indices = [
            'idx_users_role_id',
            'idx_audit_user_id',
            'idx_audit_timestamp',
            'idx_audit_entity',
            'idx_role_permissions_permission_id'
        ]
        
        try:
            cursor.execute("""
            SELECT DISTINCT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = 'it_asset_management'
            AND TABLE_NAME IN ('users', 'audit_log', 'role_permissions')
            """)
            
            existing_indices = {row[0] for row in cursor.fetchall()}
            
            print(f"\n  Required indices:")
            indices_ok = True
            for idx in required_indices:
                exists = idx in existing_indices
                status = "✓" if exists else "✗"
                print(f"    {status} {idx}")
                if not exists:
                    indices_ok = False
            
            self.results['checks']['indices'] = indices_ok
            
        finally:
            cursor.close()
    
    def check_permissions_sample(self):
        """Show sample of permissions"""
        print("\n" + "="*70)
        print("CHECK 6: Sample Permissions")
        print("="*70)
        
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("SELECT id, name, description FROM permissions LIMIT 6")
            print(f"\n  Sample permissions:")
            for perm_id, perm_name, desc in cursor.fetchall():
                print(f"    [{perm_id:2}] {perm_name:30} - {desc}")
            
            self.results['checks']['permissions_sample'] = True
            
        finally:
            cursor.close()
    
    def generate_summary(self):
        """Generate final summary"""
        print("\n" + "="*70)
        print("VERIFICATION SUMMARY")
        print("="*70)
        
        passed = sum(1 for v in self.results['checks'].values() if v)
        total = len(self.results['checks'])
        
        print(f"\n  Checks passed: {passed}/{total}")
        
        for check_name, result in self.results['checks'].items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"    {status}: {check_name}")
        
        if self.results['errors']:
            print(f"\n  Errors found ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"    ! {error}")
        
        print("\n" + "="*70)
        print("✓ RBAC IMPLEMENTATION COMPLETE AND VERIFIED" if passed == total else "✗ VERIFICATION FAILED")
        print("="*70 + "\n")
        
        return passed == total
    
    def run_all_checks(self):
        """Run all verification checks"""
        try:
            self.check_tables_exist()
            self.check_table_structure()
            self.check_foreign_keys()
            self.check_data_integrity()
            self.check_indices()
            self.check_permissions_sample()
            success = self.generate_summary()
            
            # Save results to JSON
            with open('rbac_verification_results.json', 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print("Results saved to: rbac_verification_results.json\n")
            
            return success
            
        except Exception as e:
            print(f"\n✗ Verification failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.connection.close()


if __name__ == "__main__":
    verifier = RBACVerifier()
    success = verifier.run_all_checks()
    exit(0 if success else 1)
