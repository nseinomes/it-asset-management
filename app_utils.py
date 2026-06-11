"""
Audit logging utility functions for IT Asset Management system.

This module provides audit trail logging capabilities to track user actions
across the system. It integrates with the audit_log database table to maintain
a complete history of asset and intervention changes.

Dependencies:
    - database.py: Database connection management
    - audit_log table: Must exist in the database (created via db-schema task)
"""

from database import get_connection
from datetime import datetime
import json


def log_action(user_id, action, entity_type, entity_id, old_value=None, new_value=None):
    """
    Log a user action to the audit trail for compliance and tracking purposes.
    
    Safely records user actions with change tracking. Handles serialization of
    complex objects and graceful error handling to prevent audit failures from
    breaking application flow.
    
    Args:
        user_id (int): The ID of the user performing the action
        action (str): The type of action: 'create', 'edit', 'delete', 'update'
        entity_type (str): Type of entity affected: 'asset', 'intervention', 'user', etc.
        entity_id (int): The ID of the affected entity
        old_value (any, optional): Previous value (for edit/update actions). Defaults to None.
        new_value (any, optional): New value after action. Defaults to None.
    
    Returns:
        bool: True if logging succeeded, False if an error occurred
    
    Example:
        >>> log_action(session['user_id'], 'create', 'asset', 123, new_value='New Asset')
        True
        >>> log_action(session['user_id'], 'edit', 'asset', 123, old_value='Old Name', new_value='New Name')
        True
    
    Note:
        - Function will not raise exceptions; errors are logged to stderr but don't break execution
        - Values are automatically serialized to JSON strings for storage
        - Timestamp is automatically added by the database
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Serialize values to JSON strings for storage
        old_value_str = _serialize_value(old_value)
        new_value_str = _serialize_value(new_value)
        
        # Insert audit log entry
        cursor.execute("""
            INSERT INTO audit_log 
            (user_id, action, entity_type, entity_id, old_value, new_value, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            action,
            entity_type,
            entity_id,
            old_value_str,
            new_value_str,
            datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to log action: {str(e)}")
        print(f"  Action: {action}, Entity: {entity_type}:{entity_id}, User: {user_id}")
        return False


def get_audit_log(user_id=None, entity_type=None, entity_id=None, action=None, limit=100, offset=0):
    """
    Retrieve audit log entries for admin viewing and compliance reporting.
    
    Fetches audit trail entries with optional filtering. Supports pagination
    for large result sets and can be used for compliance reports and user activity
    tracking.
    
    Args:
        user_id (int, optional): Filter by specific user. Defaults to None (all users).
        entity_type (str, optional): Filter by entity type (e.g., 'asset', 'intervention'). 
            Defaults to None (all types).
        entity_id (int, optional): Filter by specific entity ID. Defaults to None (all entities).
        action (str, optional): Filter by action type (e.g., 'create', 'edit'). 
            Defaults to None (all actions).
        limit (int, optional): Maximum number of results to return. Defaults to 100.
        offset (int, optional): Number of results to skip for pagination. Defaults to 0.
    
    Returns:
        list: List of dictionaries with keys:
            - id: Audit log entry ID
            - user_id: User who performed the action
            - action: Type of action
            - entity_type: Type of entity
            - entity_id: ID of affected entity
            - old_value: Previous value (JSON string)
            - new_value: New value (JSON string)
            - timestamp: When action occurred
        Empty list if no results or error occurs.
    
    Example:
        >>> # Get all actions by a specific user
        >>> logs = get_audit_log(user_id=5, limit=50)
        >>> 
        >>> # Get all asset-related changes with pagination
        >>> logs = get_audit_log(entity_type='asset', limit=100, offset=100)
        >>> 
        >>> # Get specific user's deletion actions
        >>> logs = get_audit_log(user_id=5, action='delete', limit=200)
    
    Note:
        - Results are ordered by timestamp in descending order (most recent first)
        - Returns empty list on database errors (logged to stderr)
        - Values are stored as JSON strings; parse if needed for comparison
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Build dynamic query with optional filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        
        if entity_type is not None:
            query += " AND entity_type = %s"
            params.append(entity_type)
        
        if entity_id is not None:
            query += " AND entity_id = %s"
            params.append(entity_id)
        
        if action is not None:
            query += " AND action = %s"
            params.append(action)
        
        # Add ordering and pagination
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.append(limit)
        params.append(offset)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results if results else []
        
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to retrieve audit logs: {str(e)}")
        return []


def get_audit_log_count(user_id=None, entity_type=None, entity_id=None, action=None):
    """
    Get the total count of audit log entries matching the specified filters.
    
    Useful for pagination UI to determine total pages or for generating
    compliance statistics.
    
    Args:
        user_id (int, optional): Filter by specific user. Defaults to None.
        entity_type (str, optional): Filter by entity type. Defaults to None.
        entity_id (int, optional): Filter by specific entity. Defaults to None.
        action (str, optional): Filter by action type. Defaults to None.
    
    Returns:
        int: Total count of matching entries, or 0 on error
    
    Example:
        >>> total = get_audit_log_count(user_id=5)
        >>> total_pages = (total + 99) // 100  # 100 results per page
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build count query with same filters
        query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
        params = []
        
        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)
        
        if entity_type is not None:
            query += " AND entity_type = %s"
            params.append(entity_type)
        
        if entity_id is not None:
            query += " AND entity_id = %s"
            params.append(entity_id)
        
        if action is not None:
            query += " AND action = %s"
            params.append(action)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return count
        
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to count audit logs: {str(e)}")
        return 0


def get_entity_history(entity_type, entity_id):
    """
    Get the complete change history for a specific entity.
    
    Retrieves all changes made to a specific asset or other entity,
    showing who changed what and when. Useful for understanding
    the full lifecycle of an asset.
    
    Args:
        entity_type (str): Type of entity (e.g., 'asset', 'intervention')
        entity_id (int): ID of the specific entity
    
    Returns:
        list: List of change dictionaries ordered chronologically (oldest first)
        Empty list on error.
    
    Example:
        >>> history = get_entity_history('asset', 42)
        >>> for change in history:
        ...     print(f"{change['timestamp']}: {change['action']} by user {change['user_id']}")
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM audit_log 
            WHERE entity_type = %s AND entity_id = %s
            ORDER BY timestamp ASC
        """
        
        cursor.execute(query, (entity_type, entity_id))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results if results else []
        
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to retrieve entity history: {str(e)}")
        return []


def get_user_activity(user_id, days=30):
    """
    Get summary of a user's activity over the specified time period.
    
    Returns action counts by type and entity type for a user over
    the last N days. Useful for security monitoring and user activity
    reports.
    
    Args:
        user_id (int): The user to get activity for
        days (int, optional): Number of days to look back. Defaults to 30.
    
    Returns:
        dict: Dictionary with structure:
            {
                'total_actions': int,
                'by_action': {'create': int, 'edit': int, ...},
                'by_entity': {'asset': int, 'intervention': int, ...},
                'actions': [list of full action records]
            }
        Returns empty dict on error.
    
    Example:
        >>> activity = get_user_activity(5, days=7)
        >>> print(f"User made {activity['total_actions']} actions in last 7 days")
        >>> print(f"Asset changes: {activity['by_entity'].get('asset', 0)}")
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT * FROM audit_log
            WHERE user_id = %s 
            AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY timestamp DESC
        """
        
        cursor.execute(query, (user_id, days))
        actions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not actions:
            return {
                'total_actions': 0,
                'by_action': {},
                'by_entity': {},
                'actions': []
            }
        
        # Aggregate statistics
        by_action = {}
        by_entity = {}
        
        for action_record in actions:
            action_type = action_record['action']
            entity = action_record['entity_type']
            
            by_action[action_type] = by_action.get(action_type, 0) + 1
            by_entity[entity] = by_entity.get(entity, 0) + 1
        
        return {
            'total_actions': len(actions),
            'by_action': by_action,
            'by_entity': by_entity,
            'actions': actions
        }
        
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to retrieve user activity: {str(e)}")
        return {}


# ============================================================================
# INTERNAL HELPER FUNCTIONS
# ============================================================================

def _serialize_value(value):
    """
    Serialize a value to JSON string for storage in audit log.
    
    Handles None, dictionaries, lists, and basic types. Returns string
    representation suitable for database storage.
    
    Args:
        value (any): Value to serialize
    
    Returns:
        str: JSON string representation, or "null" for None
    """
    if value is None:
        return None
    
    try:
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        elif isinstance(value, (int, float, bool)):
            return str(value)
        else:
            return str(value)
    except Exception:
        return str(value)


# ============================================================================
# INTEGRATION POINTS (to be implemented in app.py routes)
# ============================================================================
"""
The following routes should call log_action() to track changes:

1. add_asset() route:
   from app_utils import log_action
   ...
   asset_id = cursor.lastrowid
   log_action(session['user_id'], 'create', 'asset', asset_id, new_value={...})

2. edit_asset() route:
   log_action(session['user_id'], 'edit', 'asset', asset_id, 
              old_value={old_data}, new_value={new_data})

3. delete_asset() route:
   log_action(session['user_id'], 'delete', 'asset', asset_id, 
              old_value={asset_data})

4. add_intervention() route:
   log_action(session['user_id'], 'create', 'intervention', intervention_id, 
              new_value={intervention_data})

5. complete_intervention() route:
   log_action(session['user_id'], 'update', 'intervention', intervention_id,
              old_value={'status': old_status}, new_value={'status': 'completed'})

Example implementation in app.py:

from app_utils import log_action

@app.route('/add_asset', methods=['POST'])
@login_required
def add_asset():
    # ... existing code ...
    try:
        # ... asset creation logic ...
        conn.commit()
        asset_id = cursor.lastrowid
        
        # Log the action
        log_action(
            session['user_id'],
            'create',
            'asset',
            asset_id,
            new_value={
                'name': asset_name,
                'category': asset_category,
                'serial': asset_serial
            }
        )
        
        cursor.close()
        conn.close()
        return redirect('/dashboard')
    except Exception as e:
        print(f"Error: {e}")
        return render_template("add_asset.html", error=str(e))
"""
