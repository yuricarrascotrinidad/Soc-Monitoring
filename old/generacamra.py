import pandas as pd

# Ruta del archivo Excel original
file_path = r"C:\Users\ycarrasco\Documents\Project\battery\data\transport.xlsx"

# Leer el Excel
df = pd.read_excel(file_path)

# Transformar columnas en filas (melt)
df_melted = df.melt(id_vars=['site'], var_name='position', value_name='ip')

# Guardar el resultado en un nuevo archivo Excel
output_excel = r"C:\Users\ycarrasco\Documents\Project\battery\data\transport_melted.xlsx"
df_melted.to_excel(output_excel, index=False)

# Guardar también como CSV (opcional)
output_csv = r"C:\Users\ycarrasco\Documents\Project\battery\data\transport_melted.csv"
df_melted.to_csv(output_csv, index=False)

print(f"✅ Archivo guardado como:\n- Excel: {output_excel}\n- CSV: {output_csv}")