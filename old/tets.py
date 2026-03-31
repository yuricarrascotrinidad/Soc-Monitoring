import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="monitoring",
        user="postgres",
        password="yofc",
        port="5432"
    )

    print("✅ Conexión exitosa a PostgreSQL")

    conn.close()

except Exception as e:
    print("❌ Error de conexión:")
    print(e)