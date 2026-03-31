import psycopg2
from app.config import Config

def find_deletion_logs():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        # 1. List all tables to find the log table
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Tables: {tables}")
        
        log_table = next((t for t in tables if 'deleted' in t or 'history' in t and 'battery' in t), None)
        print(f"Likely log table: {log_table}")
        
        if log_table:
            # 2. Get table structure
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{log_table}';")
            cols = [row[0] for row in cur.fetchall()]
            print(f"Columns: {cols}")
            
            # 3. Read last 10 entries
            cur.execute(f"SELECT * FROM {log_table} ORDER BY 1 DESC LIMIT 10;")
            rows = cur.fetchall()
            for r in rows:
                print(r)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_deletion_logs()
