import psycopg2
import json
from app.config import Config

def upgrade_roles_v2():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        # Seed new roles
        new_roles = [
            ('noc', {
                "view_alarms": True, "view_cameras": True, "view_batteries": True, 
                "export_data": True, "admin_users": False, "can_interact": True
            }),
            ('customer', {
                "view_alarms": False, "view_cameras": False, "view_batteries": False, 
                "export_data": False, "admin_users": False, "can_interact": False,
                "api_access": {
                    "get_dashboard_state": True,
                    "get_ac_data": False,
                    "get_battery_history": False
                }
            })
        ]

        print("Updating NOC and Customer roles...")
        for name, perms in new_roles:
            cur.execute("""
                INSERT INTO roles (name, permissions) 
                VALUES (%s, %s) 
                ON CONFLICT (name) DO UPDATE SET permissions = %s;
            """, (name, json.dumps(perms), json.dumps(perms)))

        conn.commit()
        cur.close()
        conn.close()
        print("Database roles updated.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upgrade_roles_v2()
