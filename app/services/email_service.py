import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import io
import zipfile
import logging
from datetime import datetime
from app.config import Config

class EmailService:
    @staticmethod
    def crear_zip_con_imagenes(imagenes_dict, sitio, tipo_evento):
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for posicion, imagen_bytes in imagenes_dict.items():
                    if imagen_bytes:
                        nombre_archivo = f"{sitio}_{posicion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        zip_file.writestr(nombre_archivo, imagen_bytes)
            zip_buffer.seek(0)
            return zip_buffer.read()
        except Exception as e:
            logging.error(f"Error creando ZIP: {e}")
            return None

    @staticmethod
    def crear_html_con_imagenes_incrustadas(cuerpo_base, imagenes_dict, sitio, tipo_evento, email_ts=None):
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not email_ts:
            email_ts = datetime.now().strftime('%Y%p%S')
            
        imagenes_validas = {k: v for k, v in (imagenes_dict or {}).items() if v is not None}
        total_imagenes = len(imagenes_validas)
        es_transport = tipo_evento and "transport" in str(tipo_evento).lower()
        
        seccion_imagenes = ""
        
        if total_imagenes > 0:
            if es_transport and total_imagenes >= 4:
                # Layout para transport (grid)
                seccion_imagenes = f"""
                <div style="margin: 25px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="font-size: 20px; margin-right: 10px;">📸</span>
                        <h3 style="margin: 0; color: #343a40;">Capturas de Cámara en Tiempo Real</h3>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 20px;">
                """
                
                posiciones_ordenadas = ["principal", "patio", "equipo", "generador"]
                for idx, posicion in enumerate(posiciones_ordenadas):
                    if posicion in imagenes_validas:
                        cid = f"captura_{sitio}_{posicion}_{email_ts}_{idx}"
                        nombre_display = posicion.capitalize()
                        
                        seccion_imagenes += f"""
                        <div style="text-align: center; background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h4 style="margin: 0 0 10px 0; color: #495057; font-size: 14px;">{nombre_display}</h4>
                            <img src="cid:{cid}" alt="{nombre_display}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                            <p style="margin: 8px 0 0 0; font-size: 12px; color: #6c757d;">{ahora}</p>
                        </div>
                        """
                seccion_imagenes += "</div></div>"
            else:
                # Layout estándar (lista vertical)
                seccion_imagenes = f"""
                <div style="margin: 25px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <span style="font-size: 20px; margin-right: 10px;">📸</span>
                        <h3 style="margin: 0; color: #343a40;">Capturas de Cámara en Tiempo Real</h3>
                    </div>
                """
                for idx, (posicion, _) in enumerate(imagenes_validas.items()):
                    cid = f"captura_{sitio}_{posicion}_{email_ts}_{idx}"
                    nombre_display = posicion.capitalize()
                    
                    seccion_imagenes += f"""
                    <div style="margin-bottom: 20px; text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #495057; text-align: left;">{nombre_display}</h4>
                        <img src="cid:{cid}" alt="{nombre_display}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;">
                        <p style="margin: 5px 0; color: #6c757d; font-size: 12px; text-align: left;">{ahora} | {posicion}</p>
                    </div>
                    """
                seccion_imagenes += "</div>"
        
        if "<!-- EVENTOS DETECTADOS -->" in cuerpo_base:
            return cuerpo_base.replace("<!-- EVENTOS DETECTADOS -->", seccion_imagenes)
        return cuerpo_base + seccion_imagenes

    @staticmethod
    def enviar_alerta_email(asunto, cuerpo, imagenes_dict=None, sitio=None, tipo_evento=None):
        try:
            msg = MIMEMultipart("related")
            msg['From'] = Config.EMAIL_ADDRESS
            msg['To'] = Config.EMAIL_DESTIANTION
            msg['Subject'] = asunto

            # Parte HTML
            html_part = MIMEMultipart("alternative")
            msg.attach(html_part)
            
            # Procesar el HTML para incluir referencias a imágenes
            # Generamos un timestamp único para este correo para mantener CIDs consistentes
            email_ts = datetime.now().strftime('%Y%p%S') 
            cuerpo_html = EmailService.crear_html_con_imagenes_incrustadas(cuerpo, imagenes_dict, sitio, tipo_evento, email_ts)
            html_part.attach(MIMEText(cuerpo_html, 'html'))

            # Adjuntar imágenes inline
            if imagenes_dict:
                imagenes_validas = {k: v for k, v in imagenes_dict.items() if v is not None}
                for idx, (posicion, imagen_bytes) in enumerate(imagenes_validas.items()):
                    if imagen_bytes:
                        img = MIMEImage(imagen_bytes)
                        # El CID DEBE coincidir exactamente con el generado en el HTML
                        cid = f"captura_{sitio}_{posicion}_{email_ts}_{idx}"
                        img.add_header('Content-ID', f'<{cid}>')
                        img.add_header('Content-Disposition', 'inline')
                        msg.attach(img)
                
                # Adjuntar ZIP
                zip_bytes = EmailService.crear_zip_con_imagenes(imagenes_validas, sitio, tipo_evento)
                if zip_bytes:
                    zip_part = MIMEBase('application', 'zip')
                    zip_part.set_payload(zip_bytes)
                    encoders.encode_base64(zip_part)
                    zip_part.add_header('Content-Disposition', 'attachment', 
                                      filename=f'capturas_{sitio}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
                    msg.attach(zip_part)

            # Enviar
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            logging.debug(f"Email enviado: {asunto}")
            return True
        except Exception as e:
            logging.error(f"Error enviando email: {e}")
            return False
