import pandas as pd
import io
import logging
from datetime import datetime, timedelta
from app.utils.db import get_db_connection
from app.services.monitoring_service import MonitoringService

class ExportService:
    @staticmethod
    def generar_excel(tipo):
        """
        Genera un archivo Excel con:
        - Hoja 1: Las mismas anomalías que muestra la pantalla (últimas 24h, >5 repeticiones)
        - Hoja 2: Todos los registros individuales que conforman esas anomalías
        """
        try:
            # Obtener EXACTAMENTE las mismas anomalías que muestra la pantalla
            datos = MonitoringService.obtener_datos_completos_v2(tipo, include_anomalias=True)
            anomalias = datos.get("anomalias", [])

            # --- Hoja 1: Resumen de Anomalías (igual que pantalla) ---
            anomalias_rows = []
            for a in anomalias:
                anomalias_rows.append({
                    "Sitio": a.get("sitio", ""),
                    "Categoría": a.get("categoria", ""),
                    "Alarma": a.get("alarmameta", ""),
                    "Repeticiones (24h)": a.get("veces", 0),
                    "Última vez": a.get("ultima_vez", ""),
                })
            df_anomalias = pd.DataFrame(anomalias_rows) if anomalias_rows else pd.DataFrame(
                columns=["Sitio", "Categoría", "Alarma", "Repeticiones (24h)", "Última vez"]
            )

            # --- Hoja 2: Registros individuales que conforman esas anomalías ---
            df_detalle = pd.DataFrame(columns=["Tipo", "Región", "Hora", "Sitio", "Alarma", "Categoría", "Dispositivo", "Estado"])

            if anomalias:
                conn = get_db_connection()
                try:
                    cur = conn.cursor()
                    ahora = datetime.now()
                    limite_str = (ahora - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

                    # Construir filtro exacto de (sitio, alarma, categoria) de cada anomalía
                    filtros = [(a.get("sitio"), a.get("alarmameta"), a.get("categoria")) for a in anomalias]
                    placeholders = " OR ".join(["(a.sitio = %s AND a.alarma = %s AND a.categoria = %s)"] * len(filtros))
                    params_filtro = [p for par in filtros for p in par]

                    query = f"""
                        SELECT a.tipo, a.region, a.hora, a.sitio, a.alarma, a.categoria, a.devicename, a.estado
                        FROM (
                            SELECT tipo, region, hora, sitio, alarma, categoria, devicename, estado FROM alarmas_activas
                            UNION ALL
                            SELECT tipo, region, hora, sitio, alarma, categoria, devicename, estado FROM alarmas_historicas
                        ) a
                        WHERE a.tipo = %s AND a.hora >= %s AND ({placeholders})
                        ORDER BY a.hora DESC
                    """
                    cur.execute(query, [tipo, limite_str] + params_filtro)
                    rows = cur.fetchall()

                    detalle_rows = []
                    for row in rows:
                        tipo_r, region, hora, sitio, alarma, categoria, devicename, estado = row
                        detalle_rows.append({
                            "Tipo": tipo_r,
                            "Región": region,
                            "Hora": hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else hora,
                            "Sitio": sitio,
                            "Alarma": alarma,
                            "Categoría": categoria,
                            "Dispositivo": devicename,
                            "Estado": estado,
                        })
                    df_detalle = pd.DataFrame(detalle_rows) if detalle_rows else df_detalle
                finally:
                    conn.close()

            # --- Generar Excel ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_anomalias.to_excel(writer, sheet_name='Anomalías', index=False)
                df_detalle.to_excel(writer, sheet_name='Registros Individuales', index=False)

                # Ajustar ancho de columnas
                for sheet_name, df in [('Anomalías', df_anomalias), ('Registros Individuales', df_detalle)]:
                    ws = writer.sheets[sheet_name]
                    for i, col in enumerate(df.columns):
                        max_len = max(len(str(col)), max((len(str(v)) for v in df[col] if v), default=0))
                        ws.column_dimensions[chr(65 + i)].width = min(max_len + 4, 60)

            output.seek(0)
            return output

        except Exception as e:
            logging.error(f"Error generando Excel para {tipo}: {e}")
            raise e
    @staticmethod
    def generar_excel_desconexion(filtro_region=None, filtro_tipo=None):
        """
        Genera un archivo Excel con las alarmas de baterías desconectadas.
        
        Args:
            filtro_region (str, optional): Filtrar por región
            filtro_tipo (str, optional): Filtrar por tipo ('access' o 'transport')
        
        Returns:
            io.BytesIO: Archivo Excel en memoria
        """
        try:
            # Obtener los datos con los filtros aplicados
            datos = MonitoringService.obtener_datos_desconexion(filtro_region, filtro_tipo)
            
            # Filtrar para eliminar device_id de cada registro
            datos_filtrados = []
            for record in datos:
                # Crear un nuevo diccionario sin device_id
                record_sin_device = {
                    "tipo": record.get("tipo"),
                    "region": record.get("region"),
                    "hora": record.get("hora"),
                    "duracion": record.get("duracion"),
                    "sitio": record.get("sitio"),
                    "alarma": record.get("alarma"),
                    "devicename": record.get("devicename")
                }
                datos_filtrados.append(record_sin_device)
            
            # Crear DataFrame con los datos ya filtrados
            if datos_filtrados:
                df = pd.DataFrame(datos_filtrados)
            else:
                df = pd.DataFrame(columns=["tipo", "region", "hora", "duracion", "sitio", "alarma", "devicename"])
            
            # Renombrar columnas para el Excel (en español)
            df = df.rename(columns={
                "tipo": "Tipo",
                "region": "Región",
                "hora": "Fecha/Hora",
                "duracion": "Duración",
                "sitio": "Sitio",
                "alarma": "Alarma",
                "devicename": "Dispositivo"
            })
            
            # Generar Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Baterías Desconectadas', index=False)
                
                # Ajustar ancho de columnas
                ws = writer.sheets['Baterías Desconectadas']
                for i, col in enumerate(df.columns):
                    max_len = max(len(str(col)), max((len(str(v)) for v in df[col] if v), default=0))
                    ws.column_dimensions[chr(65 + i)].width = min(max_len + 4, 60)
            
            output.seek(0)
            return output
            
        except Exception as e:
            logging.error(f"Error generando Excel de desconexion: {e}")
            raise e