"""
Script Maestro para la Sincronización y Refactorización Global de la Cuenta Madre.
"""

import asyncio
import os
import re
import json
import glob
from pathlib import Path
from playwright.async_api import async_playwright

# Importamos las funciones puras de publicacion (sin dependencias engorrosas)
from publicar_anuncios import (
    obtener_email_cuenta, parsear_datos_md, listar_fotos, publicar_anuncio, PAUSA_ENTRE_ANUNCIOS, CARPETA_ANUNCIOS
)

CUENTA_MADRE = "fernandoapg00@gmail.com"
ARCHIVO_MADRE = f"publicados_en_{CUENTA_MADRE}.json"

# Orden de publicación: "DESC" = últimos primero, "ASC" = primeros primero
ORDEN_PUBLICACION = "DESC"

def extraer_id_url(url):
    match = re.search(r'-(\d+)\?', url)
    if not match:
        match = re.search(r'/item/(\d+)', url)
    if match:
        return match.group(1)
    return None

async def cargar_todos_los_ids_madre(page):
    print("⬇️  Cargando la bóveda maestra de la cuenta Madre...")
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
            print(f"  📦 {len(ids_vistos)} anuncios detectados...")
            
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        
    return list(ids_vistos)

def realizar_renombrado_global(viejo_id, nuevo_id, nueva_url):
    print(f"\n  🔄 INICIANDO REFACTORIZACIÓN GLOBAL: {viejo_id} ➔ {nuevo_id}")
    
    # 1. Renombrar la carpeta principal
    carpeta_vieja = os.path.join(CARPETA_ANUNCIOS, viejo_id)
    carpeta_nueva = os.path.join(CARPETA_ANUNCIOS, nuevo_id)
    
    try:
        os.rename(carpeta_vieja, carpeta_nueva)
        print(f"    ✅ Carpeta física renombrada a /anuncios/{nuevo_id}/")
    except Exception as e:
        print(f"    ❌ Error renombrando carpeta local: {e}")
        return # Es vital que aborte aquí para evitar destrozos
        
    # 2. Reemplazar ID dentro de datos.md
    datos_file = os.path.join(carpeta_nueva, "datos.md")
    if os.path.exists(datos_file):
        with open(datos_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Reemplazar celda especifica | **ID** | 12345 |
        content = re.sub(r'\|\s*\*\*ID\*\*\s*\|\s*' + re.escape(viejo_id) + r'\s*\|', f"| **ID** | {nuevo_id} |", content)
        # Reemplazar instancias de URLs viejas
        content = content.replace(viejo_id, nuevo_id)

        with open(datos_file, "w", encoding="utf-8") as f:
            f.write(content)
        print("    ✅ datos.md local actualizado (ID + URL integrados)")
    
    # 3. Reescribir todos los archivos JSON de TODAS las cuentas
    json_files = glob.glob("publicados_en_*.json")
    for j_file in json_files:
        try:
            with open(j_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # En la Cuenta Madre sencillamente se registra un nuevo vivo (ya que en un paso anterior borramos el viajo)
            if j_file == ARCHIVO_MADRE:
                data[nuevo_id] = {"nueva_url": nueva_url}
                with open(j_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"    ✅ Archivo Maestro Cimentado con la nueva entrada {nuevo_id}.")
            else:
                # En satélites, buscamos agresivamente si ese Viejo ID fue publicado por ellas, y lo mutamos
                if viejo_id in data:
                    valor_satelite = data.pop(viejo_id)
                    data[nuevo_id] = valor_satelite
                    with open(j_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"    ✅ Archivo Satélite {j_file}: Transformó existosamente de {viejo_id} a {nuevo_id}.")
                
        except Exception as e:
             print(f"    ⚠️  Error procesando archivo interno de cuenta madre {j_file}: {e}")

async def main():
    if not os.path.isdir(CARPETA_ANUNCIOS):
        print(f"❌ No existe la carpeta '{CARPETA_ANUNCIOS}/'")
        return

    async with async_playwright() as p:
        print("🔌 Conectando a Chrome para iniciar master-session...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conexión establecida\n")
        
        email = await obtener_email_cuenta(context)
        if email != CUENTA_MADRE:
            print(f"❌ ADVERTENCIA: Este script MASTER está bloqueado para resguardar '{CUENTA_MADRE}'.")
            print(f"   Pero Chrome parece estar navegando como: {email}")
            print("   Por favor cierra sesión y logéate como la cuenta madre antes de proceder.")
            return

        print(f"👩‍👦 Sesión Maestra Detectada Oficialmente: {email}")
        print("\n=== FASE 1: SINCRONIZACIÓN ABSOLUTA NUBE ===")
        print("📄 Navegando y recolectando tu inventario real vivo...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando carga segura (10s)...")
        await asyncio.sleep(10)
        
        vivos = await cargar_todos_los_ids_madre(page)
        
        if not vivos:
             print("❌ La cuenta madre se percibe estéril (0 anuncios detectados). Podrías tener un captcha enfrente.")
             return
             
        vivos_set = set(vivos)
        
        # Extracción y limpieza del archivo Maestro principal
        madre_dict = {}
        for c_id in vivos_set:
             madre_dict[c_id] = {"nueva_url": f"https://www.revolico.com/item/{c_id}/_/manage?action=created"}
        
        with open(ARCHIVO_MADRE, "w", encoding="utf-8") as f:
             json.dump(madre_dict, f, ensure_ascii=False, indent=2)
             
        print(f"✅ ADN Local limpiecito! Se han cimentado {len(vivos_set)} anuncios vivos.")
        
        print("\n=== FASE 2: CAZA DE HUÉRFANOS CAÍDOS ===")
        carpetas_ids = sorted(
            (d for d in os.listdir(CARPETA_ANUNCIOS)
            if d.isdigit() and os.path.isdir(os.path.join(CARPETA_ANUNCIOS, d))),
            reverse=(ORDEN_PUBLICACION == "DESC")
        )
        
        huerfanos = [c_id for c_id in carpetas_ids if c_id not in vivos_set]
        
        print(f"📂 Total carpetas físicas locales : {len(carpetas_ids)}")
        print(f"☁️  Total IDs sincronizados madre : {len(vivos_set)}")
        print(f"👻 Huérfanos detectados perdidos  : {len(huerfanos)}\n")
        
        if not huerfanos:
             print("🎉 Ecosistema perfectamente síncrono. ¡Enhorabuena!")
             return
             
        print("=== FASE 3: RESURRECCIÓN OMEGA ===")
        for i, h_id in enumerate(huerfanos):
            carpeta = os.path.join(CARPETA_ANUNCIOS, h_id)
            print(f"\n{'━'*60}")
            print(f"[{i+1}/{len(huerfanos)}] INICIANDO RESURRECCIÓN DEL HUÉRFANO (Viejo ID): {h_id}")
            
            try:
                datos = parsear_datos_md(os.path.join(carpeta, "datos.md"))
            except Exception as e:
                print(f"  ❌ Error trágico de lectura en el infante {h_id}: {e}")
                continue
                
            rutas_fotos = listar_fotos(carpeta)
            
            try:
                nueva_url = await publicar_anuncio(page, h_id, datos, rutas_fotos, preview=False)
            except Exception as e:
                print(f"  ❌ Excepción catastrófica devolviéndolo a la vida: {e}")
                continue
                
            if nueva_url:
                nuevo_id = extraer_id_url(nueva_url)
                if nuevo_id:
                    print(f"  ✨ ¡RESUCITÓ OFICIALMENTE! Su nueva y deslumbrante URL es: {nueva_url} (ID: {nuevo_id}) ✨")
                    # El disparo de las piezas clave del ecosistema
                    realizar_renombrado_global(viejo_id=h_id, nuevo_id=nuevo_id, nueva_url=nueva_url)
                else:
                    print(f"  ❌ Logré publicarlo aparentemente, PERO la Extracción de su ID falló. Deteniendo motor.")
            else:
                 print(f"  ⚠️ El huérfano {h_id} falló resarciendo en este ciclo del bot.")
                 
            if i < len(huerfanos) - 1:
                print(f"\n  ⏳ Tiempo de enfriamiento para no enfadar al BotNet ({PAUSA_ENTRE_ANUNCIOS}s)...")
                await asyncio.sleep(PAUSA_ENTRE_ANUNCIOS)
                
        print(f"\n{'='*65}")
        print("🎉 ¡SISTEMA OPERATIVO Y GLOBALMENTE REFACTORIZADO A LA NUEVA REALIDAD! 🎉")
        print(f"{'='*65}")

if __name__ == "__main__":
    asyncio.run(main())
