from app.utils.db import get_db_connection
import json
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT name, permissions FROM roles")
roles_data = cur.fetchall()
with open('c:/Users/ycarrasco/Documents/Project/battery/tmp_roles_output.txt', 'w', encoding='utf-8') as f:
    for name, perms in roles_data:
        f.write(f"ROLE: {name}\n")
        f.write(f"PERMS: {json.dumps(perms, indent=2)}\n\n")
conn.close()
