import asyncio
import os
import re
import json
import base64
from playwright.async_api import async_playwright

async def obtener_email_cuenta(context):
    cookies = await context.cookies("https://www.revolico.com")
    for c in cookies:
        if c['name'] == 'st-access-token':
            try:
                parts = c['value'].split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += '=' * (-len(payload) % 4)
                    data = json.loads(base64.b64decode(payload).decode('utf-8'))
                    return data.get("user_email") or data.get("user_name")
            except Exception:
                pass
    return None

def extraer_id_url(url):
    """
    Extrae el ID del anuncio a partir de una URL de Revolico.
    Toma tanto URLs con -XXXXXX? como /item/XXXXX/
    """
    match = re.search(r'-(\d+)\?', url)
    if not match:
        match = re.search(r'/item/(\d+)', url)
    if match:
        return match.group(1)
    return None

async def cargar_todos_los_ids(page):
    print("⬇️  Cargando anuncios activos en Revolico (scrolleando)...")
    ids_vistos = set()
    sin_cambios = 0
    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()
        for el in links:
            href = await el.get_attribute("href")
            if href:
                id_ext = extraer_id_url(href)
                if id_ext:
                    ids_actuales.add(id_ext)
                    
        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            ids_vistos = set(ids_actuales)
            print(f"  📦 {len(ids_vistos)} anuncios encontrados...")
            
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
    return list(ids_vistos)

async def check():
    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")
        
        email = await obtener_email_cuenta(context)
        if email:
            archivo_registro = f"publicados_en_{email}.json"
            print(f"👤 Cuenta detectada: {email}")
        else:
            archivo_registro = "publicados_en_cuenta_nueva.json"
            print("⚠️ No se pudo extraer el email de las cookies. Usando registro por defecto.")

        if not os.path.exists(archivo_registro):
            print(f"❌ No existe el registro local '{archivo_registro}'. No hay nada que verificar.")
            return

        with open(archivo_registro, "r", encoding="utf-8") as f:
            try:
                publicados = json.load(f)
            except json.JSONDecodeError:
                print("❌ El archivo json está corrupto.")
                return

        if not publicados:
            print("⚠️ El registro de publicados local está vacío.")
            return

        print("📄 Navegando a tu cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando que cargue la página inicial (10 segundos)...")
        await asyncio.sleep(10)
        
        # --- SAFEGUARD: Verificar carga correcta ---
        if "/account" not in page.url:
            print(f"❌ Error Crítico: La página no es /account (URL actual: {page.url}). Posible bloqueo o sesión cerrada. Abortando limpieza.")
            return

        elementos_prueba = await page.query_selector_all('a:has-text("Gestionar")')
        if len(elementos_prueba) == 0:
            print("❌ Error Crítico: No se detectó ningún botón 'Gestionar'.")
            print("   Esto significa que la página cargó en blanco, hay un Captcha de Cloudflare, o literalmente tienes 0 anuncios.")
            print("   Abortando el proceso de verificación para proteger tu archivo JSON local de un borrado erróneo masivo.")
            return
        # -------------------------------------------
        
        vivos = await cargar_todos_los_ids(page)
        vivos_set = set(vivos)
        
        borrados_detectados = []
        elementos_original = len(publicados)

        # Chequeamos cada anuncio guardado en el JSON
        for original_id, data in list(publicados.items()):
            url_cloud = data.get("nueva_url", "")
            id_cloud = extraer_id_url(url_cloud)
            
            if not id_cloud:
                print(f"  ⚠️  No se pudo extraer ID de nube del anuncio {original_id}: {url_cloud}")
                continue

            # Si el ID con el que se publicó ya no está en la página de cuenta (nube)
            if id_cloud not in vivos_set:
                print(f"  🔍 Anuncio {id_cloud} ausente en portada. Iniciando DOBLE VERIFICACIÓN...")
                try:
                    await page.goto(url_cloud, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(4)
                    
                    base_expected = url_cloud.split('?')[0]
                    current_base = page.url.split('?')[0]
                    
                    # Revolico redirecciona al home o al account si el anuncio ya no existe
                    if base_expected == current_base:
                        # Revolico a veces carga la URL pero muestra que el anuncio fue tumbado/despublicado
                        cartel_despublicado = await page.query_selector('text="Anuncio despublicado"')
                        if cartel_despublicado:
                            print(f"    ❌ Confirmado Borrado: El anuncio {id_cloud} dice 'Anuncio despublicado'.")
                            borrados_detectados.append(original_id)
                        else:
                            print(f"    ✅ Falsa Alarma: El anuncio {id_cloud} SIGUE VIVO (la URL directa cargó correctamente sin errores).")
                    else:
                        print(f"    ❌ Confirmado Borrado: Revolico redirigió la URL de {id_cloud} a {current_base}.")
                        borrados_detectados.append(original_id)

                except Exception as e:
                    print(f"    ⚠️  Error de red en doble verificación para {id_cloud}. Asumiendo vivo temporalmente por precaución.")

        print("\n" + "━"*60)
        print("📊 RESULTADO DE VERIFICACIÓN")
        print("━"*60)
        print(f"  🔍 Anuncios en tu JSON local ({email}): {elementos_original}")
        print(f"  ☁️  Anuncios activos vivos en la nube: {len(vivos_set)}")

        if not borrados_detectados:
            print(f"  ✅ Todo en orden. Ningún anuncio de tu registro fue borrado por Revolico.")
        else:
            print(f"  🗑️  Revolico te ha borrado {len(borrados_detectados)} anuncio(s) de tu cuenta.")
            print("  Limpiando estos IDs locales del esquema para forzar resubida en el próximo ciclo:")
            
            for b in borrados_detectados:
                print(f"    - ID original borrado de JSON: {b}")
                del publicados[b]
            
            with open(archivo_registro, "w", encoding="utf-8") as f:
                json.dump(publicados, f, ensure_ascii=False, indent=2)
            
            print(f"\n  💾 Registro {archivo_registro} actualizado exitosamente.")
        print("━"*60)

if __name__ == "__main__":
    asyncio.run(check())
