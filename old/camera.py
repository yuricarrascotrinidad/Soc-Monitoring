import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Ruta del CSV
csv_file = r"C:\Users\ycarrasco\Documents\Project\battery\data\trans.csv"

# Leer CSV
#df = pd.read_csv(csv_file, encoding='cp1252')
df = pd.read_csv(csv_file)

# Conexión a PostgreSQL
user = "postgres"
password = "yofc"
host = "localhost"
port = "5432"
database = "monitoring"

engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}')

# Subir a la tabla access_cameras (reemplaza o agrega)
df.to_sql('transport_cameras', engine, if_exists='append', index=False)

