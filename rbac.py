"""
RBAC (Role-Based Access Control) helper module for IT Asset Management app
Provides utilities for role and permission management
"""

import mysql.connector
from typing import List, Dict, Optional, Tuple
from functools import wraps
from flask import request, abort

class RBACManager:
    """Manager for roles and permissions"""
    
    # Role IDs
    ROLE_ADMIN = 1
    ROLE_TECHNICIAN = 2
    ROLE_USER = 3
    
    # Permission names
    PERM_ASSET_VIEW = 'asset.view'
    PERM_ASSET_CREATE = 'asset.create'
    PERM_ASSET_EDIT = 'asset.edit'
    PERM_ASSET_DELETE = 'asset.delete'
    PERM_INTERVENTION_VIEW = 'intervention.view'
    PERM_INTERVENTION_CREATE = 'intervention.create'
    PERM_INTERVENTION_EDIT = 'intervention.edit'
    PERM_INTERVENTION_DELETE = 'intervention.delete'
    PERM_TECHNICIAN_MANAGE = 'technician.manage'
    PERM_USER_MANAGE = 'user.manage'
    PERM_AUDIT_VIEW = 'audit.view'
    PERM_CATEGORY_MANAGE = 'category.manage'
    
    def __init__(self, connection):
        """Initialize RBAC manager with database connection"""
        self.connection = connection
    
    def get_user_role(self, user_id: int) -> Optional[Dict]:
        """Get user's role information"""
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute("""
            SELECT r.id, r.name, r.description
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.id = %s
            """, (user_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
            SELECT DISTINCT p.name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = %s AND p.name IS NOT NULL
            """, (user_id,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has a specific permission"""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions
    
    def get_role_permissions(self, role_id: int) -> List[str]:
        """Get all permissions for a role"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
            SELECT p.name
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = %s
            """, (role_id,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def assign_role_to_user(self, user_id: int, role_id: int) -> bool:
        """Assign a role to a user"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
            UPDATE users SET role_id = %s WHERE id = %s
            """, (role_id, user_id))
            self.connection.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"Error assigning role: {e}")
            return False
        finally:
            cursor.close()
    
    def audit_log(self, user_id: int, action: str, entity_type: str,
                  entity_id: int, old_value: Optional[str] = None,
                  new_value: Optional[str] = None) -> bool:
        """Log an action to the audit log"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, action, entity_type, entity_id, old_value, new_value))
            self.connection.commit()
            return True
        except mysql.connector.Error as e:
            print(f"Error logging audit: {e}")
            return False
        finally:
            cursor.close()
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0,
                       user_id: Optional[int] = None,
                       entity_type: Optional[str] = None) -> List[Dict]:
        """Retrieve audit logs with optional filters"""
        cursor = self.connection.cursor(dictionary=True)
        try:
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            if entity_type:
                query += " AND entity_type = %s"
                params.append(entity_type)
            
            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    
    @staticmethod
    def ensure_foreign_key():
        """Ensure the foreign key constraint exists (idempotent)"""
        from database import get_connection
        connection = get_connection()
        cursor = connection.cursor()
        try:
            # Check if foreign key exists
            cursor.execute("""
            SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'role_id'
            AND REFERENCED_TABLE_NAME IS NOT NULL;
            """)
            
            if not cursor.fetchone():
                # Add foreign key if it doesn't exist
                cursor.execute("""
                ALTER TABLE users 
                ADD CONSTRAINT fk_users_role_id 
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL;
                """)
                connection.commit()
                print("✓ Foreign key constraint added")
            else:
                print("✓ Foreign key constraint already exists")
        except mysql.connector.Error as e:
            print(f"Note: {e}")
        finally:
            cursor.close()
            connection.close()


def require_permission(permission: str):
    """Decorator to require a specific permission for a route
    
    Usage:
        @app.route('/assets/delete/<int:asset_id>', methods=['DELETE'])
        @require_permission(RBACManager.PERM_ASSET_DELETE)
        def delete_asset(asset_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from database import get_connection
            
            # Get user_id from session or JWT token
            # This assumes you have session['user_id'] or similar
            user_id = request.headers.get('X-User-ID') or getattr(request, 'user_id', None)
            
            if not user_id:
                abort(401)  # Unauthorized
            
            connection = get_connection()
            rbac = RBACManager(connection)
            
            if not rbac.has_permission(user_id, permission):
                connection.close()
                abort(403)  # Forbidden
            
            connection.close()
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_role(role_id: int):
    """Decorator to require a specific role for a route
    
    Usage:
        @app.route('/admin/users')
        @require_role(RBACManager.ROLE_ADMIN)
        def admin_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from database import get_connection
            
            user_id = request.headers.get('X-User-ID') or getattr(request, 'user_id', None)
            
            if not user_id:
                abort(401)  # Unauthorized
            
            connection = get_connection()
            rbac = RBACManager(connection)
            user_role = rbac.get_user_role(user_id)
            connection.close()
            
            if not user_role or user_role['id'] != role_id:
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
