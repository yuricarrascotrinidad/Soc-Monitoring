import psycopg2
import json
from app.config import Config

def ensure_admin_api_access():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        # Update admin role permissions
        admin_perms = {
            "view_alarms": True, "view_cameras": True, "view_batteries": True, 
            "export_data": True, "admin_users": True, "can_interact": True,
            "api_access": {
                "get_dashboard_state": True,
                "get_ac_data": True,
                "get_battery_history": True,
                "export_data_api": True
            }
        }

        print("Updating Admin role with full API access...")
        cur.execute("""
            UPDATE roles SET permissions = %s WHERE name = 'admin';
        """, (json.dumps(admin_perms),))

        conn.commit()
        cur.close()
        conn.close()
        print("Admin role updated.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ensure_admin_api_access()
