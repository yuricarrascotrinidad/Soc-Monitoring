import sqlite3
import logging

def migrate():
    conn = sqlite3.connect('monitoring.db')
    try:
        cur = conn.cursor()
        print("Adding 'valor' column to 'alarmas' table...")
        cur.execute("ALTER TABLE alarmas ADD COLUMN valor REAL")
        conn.commit()
        print("Migration successful.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'valor' already exists.")
        else:
            print(f"Operational error: {e}")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
