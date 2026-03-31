import psycopg2
import json
from app.config import Config

def upgrade_rbac_db():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        # Create roles table
        print("Creating roles table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                permissions JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Seed default roles
        default_roles = [
            ('admin', {
                "view_alarms": True, "view_cameras": True, "view_batteries": True, 
                "export_data": True, "admin_users": True, "can_interact": True
            }),
            ('soc', {
                "view_alarms": True, "view_cameras": True, "view_batteries": True, 
                "export_data": True, "admin_users": False, "can_interact": True
            }),
            ('viewer', {
                "view_alarms": True, "view_cameras": True, "view_batteries": True, 
                "export_data": False, "admin_users": False, "can_interact": False
            })
        ]

        print("Seeding default roles...")
        for name, perms in default_roles:
            cur.execute("""
                INSERT INTO roles (name, permissions) 
                VALUES (%s, %s) 
                ON CONFLICT (name) DO UPDATE SET permissions = %s;
            """, (name, json.dumps(perms), json.dumps(perms)))

        conn.commit()
        cur.close()
        conn.close()
        print("Database upgrade completed successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upgrade_rbac_db()
