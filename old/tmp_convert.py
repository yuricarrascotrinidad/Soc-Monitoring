import pandas as pd
import os

def convert_excel_to_sql(excel_path, table_name, output_sql_path):
    print(f"Reading {excel_path}...")
    df = pd.read_excel(excel_path)
    print(f"Columns in {excel_path}: {df.columns.tolist()}")
    
    with open(output_sql_path, 'w', encoding='utf-8') as f:
        f.write(f"-- Data from {excel_path}\n")
        f.write(f"DELETE FROM {table_name};\n\n")
        
        cols = [c.strip().lower() for c in df.columns]
        df.columns = cols

        for _, row in df.iterrows():
            if table_name == 'access_cameras':
                site = str(row.get('site', row.iloc[0])).replace("'", "''")
                ip = str(row.get('ip', row.iloc[1]))
                f.write(f"INSERT INTO access_cameras (site, ip) VALUES ('{site}', '{ip}') ON CONFLICT (site, ip) DO NOTHING;\n")
            elif table_name == 'transport_cameras':
                site = str(row.get('site', row.iloc[0])).replace("'", "''")
                positions_map = {
                    'prin': 'prin',
                    'patio': 'patio',
                    'equipo': 'equipo',
                    'generador': 'generador'
                }
                for col, pos_name in positions_map.items():
                    if col in row and pd.notna(row[col]):
                        ip = str(row[col])
                        f.write(f"INSERT INTO transport_cameras (site, position, ip) VALUES ('{site}', '{pos_name}', '{ip}') ON CONFLICT (site, position) DO NOTHING;\n")
    
    print(f"Generated {output_sql_path}")

if __name__ == "__main__":
    data_dir = "data"
    convert_excel_to_sql(os.path.join(data_dir, "access.xlsx"), "access_cameras", "access_config.sql")
    convert_excel_to_sql(os.path.join(data_dir, "transport.xlsx"), "transport_cameras", "transport_config.sql")
