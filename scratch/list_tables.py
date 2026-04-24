import psycopg2
conn = psycopg2.connect('host=localhost port=5432 dbname=monitoring user=postgres password=yofc')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
for row in cur.fetchall():
    print(row[0])
conn.close()
