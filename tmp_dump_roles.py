import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.db import get_db_connection
import json

def check_roles():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name, permissions FROM roles")
        roles = cur.fetchall()
        result = []
        for role in roles:
            result.append({
                "name": role[0],
                "permissions": role[1]
            })
        with open('roles_dump.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("Roles dumped to roles_dump.json")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_roles()
