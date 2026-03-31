import psycopg2
from werkzeug.security import generate_password_hash
from app.config import Config

def setup_db():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        # Create users table
        print("Creating users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                permissions JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Add initial admin user
        username = 'admin'
        password = 'admin_password123'
        password_hash = generate_password_hash(password)
        role = 'admin'
        permissions = '{"can_view_sensitive": true, "can_edit": true}'

        print(f"Creating initial admin user: {username}")
        cur.execute("""
            INSERT INTO users (username, password_hash, role, permissions)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
        """, (username, password_hash, role, permissions))

        conn.commit()
        cur.close()
        conn.close()
        print("Database setup completed successfully.")
    except Exception as e:
        print(f"Error setting up database: {e}")

if __name__ == "__main__":
    setup_db()
