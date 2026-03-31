import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.db import get_db_connection

def diagnose():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        print(f"Connected to: {conn.dsn}")
        
        cur.execute("SELECT name FROM roles")
        roles = cur.fetchall()
        print(f"Roles found: {[r[0] for r in roles]}")
        
        cur.execute("DELETE FROM roles WHERE name = 'customer'")
        print(f"Affected rows (delete customer): {cur.rowcount}")
        
        cur.execute("SELECT name, permissions FROM roles")
        roles = cur.fetchall()
        for name, perms in roles:
            print(f"Role: {name}")
            print(f"Permissions: {json.dumps(perms)}")
            
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    diagnose()
