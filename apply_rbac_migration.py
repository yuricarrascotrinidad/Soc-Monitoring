import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.db import get_db_connection

def map_permissions(perms):
    if not isinstance(perms, dict):
        return perms
    
    # Checkbox values
    view_alarms = perms.get('view_alarms', False)
    view_batteries = perms.get('view_batteries', False)
    view_cameras = perms.get('view_cameras', False)
    export_data = perms.get('export_data', False)
    
    # Target API access
    api_access = perms.get('api_access', {})
    
    # Ensure it's a dict and update
    if not isinstance(api_access, dict):
        api_access = {}
    
    api_access['get_dashboard_state'] = view_alarms or view_batteries or view_cameras
    api_access['get_ac_data'] = view_alarms
    api_access['get_battery_history'] = view_batteries
    api_access['export_data_api'] = export_data
    
    perms['api_access'] = api_access
    return perms

def migrate():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        print("Starting migration...")
        
        # 1. Delete customer role
        cur.execute("DELETE FROM roles WHERE name = 'customer'")
        print("Role 'customer' deleted from roles table.")
        
        # 2. Update users with role 'customer' to 'viewer'
        cur.execute("UPDATE users SET role = 'viewer' WHERE role = 'customer'")
        print("Users with role 'customer' migrated to 'viewer'.")
        
        # 3. Update all roles permissions
        cur.execute("SELECT id, name, permissions FROM roles")
        roles = cur.fetchall()
        for rid, name, perms in roles:
            new_perms = map_permissions(perms)
            cur.execute("UPDATE roles SET permissions = %s WHERE id = %s", (json.dumps(new_perms), rid))
            print(f"Updated permissions for role: {name}")
            
        # 4. Update all users permissions (to apply role defaults or fix overlays)
        cur.execute("SELECT id, username, role, permissions FROM users")
        users = cur.fetchall()
        for uid, username, role, perms in users:
            # First map existing perms (in case they have an overlay)
            new_perms = map_permissions(perms)
            
            # If the user has a role, ensure they have at least the role defaults if they had nothing
            # but here we just ensure the map_permissions logic is applied to whatever they have.
            cur.execute("UPDATE users SET permissions = %s WHERE id = %s", (json.dumps(new_perms), uid))
            print(f"Updated permissions for user: {username}")
            
        conn.commit()
        print("Migration committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
