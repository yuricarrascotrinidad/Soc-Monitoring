import psycopg2
from app.config import Config

def find_precinct_sites():
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        # 1. Get precinct_id of T2230_AN_PAUCAS
        cur.execute("SELECT sitio, precinct_id FROM alarmas_activas WHERE sitio LIKE '%T2230_AN_PAUCAS%';")
        row = cur.fetchone()
        if not row:
            print("Site T2230_AN_PAUCAS not found in alarmas_activas")
            return
            
        sitio, precinct_id = row
        print(f"Site: {sitio}, Precinct: {precinct_id}")
        
        if not precinct_id:
             print("No precinct_id found for this site.")
             return

        cur.execute("SELECT sitio, devicename, categoria, alarma FROM alarmas_activas WHERE precinct_id = %s;", (precinct_id,))
        sites = cur.fetchall()
        print(f"All sites in precinct {precinct_id} with active alarms:")
        with open("precinct_alarms.txt", "w") as f:
            for s in sites:
                line = f"Sitio: {s[0]} | Device: {s[1]} | Cat: {s[2]} | Alarma: {s[3]}"
                print(line)
                f.write(line + "\n")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_precinct_sites()
