import psycopg2
import json
from app.config import Config

def update_admin():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        new_perms = {
            "view_alarms": True,
            "view_cameras": True,
            "view_batteries": True,
            "export_data": True,
            "admin_users": True,
            "can_view_sensitive": True,
            "can_edit": True
        }
        
        print("Updating admin permissions...")
        cur.execute("UPDATE users SET permissions = %s WHERE username = 'admin'", (json.dumps(new_perms),))
        conn.commit()
        print("Admin permissions updated successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_admin()
