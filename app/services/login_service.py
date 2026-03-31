import asyncio
import os
import json
import logging
import numpy as np
import cv2
import easyocr
from playwright.async_api import async_playwright
from datetime import datetime
import threading
from app.config import Config

class LoginService:
    _instance = None
    _lock = threading.Lock()
    _region_locks = {} # threading.Lock per (segment, region)
    _tokens_cache = {} # In-memory cache of tokens
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LoginService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.reader = easyocr.Reader(['en'], gpu=False)
        from app.utils.constants import TOKENS_FILE
        self.tokens_file = TOKENS_FILE
        self._initialized = True

    async def _resolver_captcha(self, page):
        try:
            element = await page.wait_for_selector('id=authimg', timeout=10000)
            img_bytes = await element.screenshot()
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            
            # Filtro de contraste para mejorar lectura
            _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
            
            result = self.reader.readtext(img, detail=0, allowlist='0123456789')
            codigo = "".join(result).strip()
            return codigo if len(codigo) == 4 else ""
        except Exception as e:
            logging.error(f"Error resolviendo captcha: {e}")
            return ""

    async def refresh_token(self, segment, region, url_base):
        """
        Realiza el login para una región específica y actualiza el token.
        Usamos un lock de hilos (threading.Lock) para coordinar entre los diferentes
        hilos de monitoreo (access, transport, ac).
        """
        key = (segment, region)
        with self._lock:
            if key not in self._region_locks:
                self._region_locks[key] = threading.Lock()
        
        # Bloquear el hilo para que solo uno intente el login por región
        if not self._region_locks[key].acquire(blocking=False):
            logging.info(f"⏳ Ya hay una renovación en curso para {region} ({segment}). Esperando...")
            with self._region_locks[key]:
                # Cuando el otro hilo termine, ya deberíamos tener el token en el archivo/cache
                return self._get_cached_token(segment, region)

        try:
            logging.info(f"🔑 Iniciando renovación de token para {region} ({segment})...")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                try:
                    # El login está en /peim/views/login o similar
                    login_url = f"{url_base}/peim/views/login"
                    await page.goto(login_url, timeout=60000)
                    
                    success = False
                    for intento in range(10): # Hasta 10 intentos de captcha
                        await page.fill('id=tbUser', Config.PEIM_USER)
                        await page.fill('id=tbPass', Config.PEIM_PASS)
                        
                        codigo = await self._resolver_captcha(page)
                        if not codigo:
                            logging.warning(f"Intento {intento+1}: Captcha no resuelto, reintentando...")
                            await page.click('id=authimg')
                            await asyncio.sleep(2)
                            continue

                        await page.fill('id=identifyCode', codigo)
                        await page.keyboard.press("Enter")
                        
                        # Esperar a ver si entramos al dashboard o similar
                        await asyncio.sleep(5) 

                        if "login" not in page.url.lower():
                            cookies = await context.cookies()
                            token = next((c['value'] for c in cookies if c['name'] == 'PEIMWEBID'), None)
                            if token:
                                self._save_token(segment, region, url_base, token)
                                logging.info(f"✅ Token renovado exitosamente para {region} ({segment})")
                                success = True
                                return token
                        else:
                            logging.warning(f"Intento {intento+1}: Login fallido (posible captcha incorrecto), reintentando...")
                            await page.click('id=authimg')
                            await asyncio.sleep(2)
                    
                    if not success:
                        logging.error(f"❌ No se pudo renovar el token para {region} después de varios intentos.")
                        
                except Exception as e:
                    logging.error(f"⚠️ Error durante el login en {region}: {e}")
                finally:
                    await context.close()
                    await browser.close()
        finally:
            self._region_locks[key].release()
        return None

    def _get_cached_token(self, segment, region):
        """Lee el token del archivo o cache."""
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(segment, {}).get(region, {}).get("cookies", {}).get("PEIMWEBID")
            except:
                pass
        return None

    def _save_token(self, segment, region, url_base, token):
        """Guarda el token en el archivo JSON."""
        data = {}
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}
        
        if segment not in data:
            data[segment] = {}
        
        data[segment][region] = {
            "url": f"{url_base}/peim/request/alarm/queryAlarm",
            "cookies": {"PEIMWEBID": token},
            "last_renewed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(self.tokens_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        # También actualizar en RAM de forma in-place para que todos los hilos lo vean
        from app.utils.constants import CONFIG_REGIONES
        if segment in CONFIG_REGIONES and region in CONFIG_REGIONES[segment]:
            logging.info(f"🔄 Sincronizando token en memoria para {region} ({segment})")
            # Actualizamos el diccionario original in-place
            CONFIG_REGIONES[segment][region]["cookies"]["PEIMWEBID"] = token
            # Sincronizar también la URL por si acaso hubiera cambiado
            CONFIG_REGIONES[segment][region]["url"] = data[segment][region]["url"]
        else:
            logging.warning(f"⚠️ No se pudo sincronizar {region} ({segment}) en CONFIG_REGIONES (no encontrado)")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = LoginService()
