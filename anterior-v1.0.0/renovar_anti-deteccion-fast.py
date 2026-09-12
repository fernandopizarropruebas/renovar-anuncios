import asyncio
import re
import sys
import os
import json
import random
from playwright.async_api import async_playwright

MAX_RONDAS = 5
ESTADO_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_progreso(correo):
    path = os.path.join(ESTADO_DIR, f"estado_renovacion_{correo}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_progreso(correo, lista_ids):
    path = os.path.join(ESTADO_DIR, f"estado_renovacion_{correo}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lista_ids, f)

def limpiar_progreso(correo):
    path = os.path.join(ESTADO_DIR, f"estado_renovacion_{correo}.json")
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass

async def cerrar_popup(page):
    try:
        for sel in ['button[aria-label="Close"]', 'button[aria-label="Cerrar"]',
                    '[data-slot="dialog-close"]', '[data-slot="dialog-portal"] button']:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                return True
        return False
    except Exception:
        return False

async def detectar_cloudflare_y_salir(page):
    try:
        titulo = await page.title()
        if "Just a moment" in titulo or "Un momento" in titulo:
            print("\n🚨 ¡ALERTA DE CLOUDFLARE DETECTADA! 🚨")
            print("Revolico está pidiendo verificación manual de seguridad.")
            print("El bot se ha detenido inmediatamente para proteger tu cuenta de un baneo.")
            print("Por favor, ve a la ventana de Chrome, resuelve el Captcha y luego vuelve a correr el bot.\n")
            sys.exit(1)
            
        cf_elements = await page.query_selector_all('#challenge-running, iframe[src*="cloudflare"]')
        if cf_elements:
            print("\n🚨 ¡ALERTA DE CLOUDFLARE DETECTADA! 🚨")
            print("El sitio está pidiendo verificación manual de seguridad.")
            print("El bot se ha detenido inmediatamente para proteger tu cuenta.")
            print("Resuélvelo en tu navegador y reinicia el script.\n")
            sys.exit(1)
    except Exception:
        pass

async def intentar_renovar(page):
    botones = await page.query_selector_all('button:has-text("Renovar anuncio")')
    if not botones:
        botones = await page.query_selector_all('a:has-text("Renovar anuncio")')
    if not botones:
        return None  # Ya renovado hoy

    # Pausa de reacción humana antes de hacer clic
    await asyncio.sleep(random.uniform(0.5, 1.2))
    await page.evaluate("el => el.click()", botones[0])
    
    # Esperar dinámicamente al resultado sin sleep fijo
    try:
        await page.wait_for_selector(
            'text="Tu anuncio fue renovado.", text="La verificación falló"',
            timeout=15000
        )
    except Exception:
        pass

    if await page.query_selector('text="Tu anuncio fue renovado."'):
        await asyncio.sleep(random.uniform(0.3, 0.8))
        entendido = await page.query_selector('button:has-text("Entendido")')
        if entendido:
            await page.evaluate("el => el.click()", entendido)
        return True

    if await page.query_selector('text="La verificación falló"'):
        print(f"  ⚠️  Cloudflare falló")
        return False

    return False

async def extraer_correo_pagina(page):
    try:
        # Extraer todo el texto visible del body
        texto = await page.evaluate("document.body.innerText")
        match = re.search(r'[\w\.-]+@[\w\.-]+', texto)
        if match:
            return match.group(0)
    except:
        pass
    return None

async def cargar_todos_los_ids(page):
    print("⬇️  Cargando todos los anuncios (scrolleando)...")
    ids_vistos = set()
    sin_cambios = 0
    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()
        for el in links:
            href = await el.get_attribute("href")
            if href:
                match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
                if match:
                    ids_actuales.add(match.group(1))
        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
            print(f"  📦 {len(ids_vistos)} anuncios cargados...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1) # Pequeño sleep solo para dar tiempo a renderizar nuevos elementos tras scroll
    return list(ids_vistos)

async def procesar_lista(page, ids, total_global, correo_activo):
    """Procesa una lista de IDs saltando los ya renovados."""
    fallidos = []
    renovados = 0
    ya_renovados = 0
    
    # Cargar progreso
    ids_procesados = cargar_progreso(correo_activo)

    for i, item_id in enumerate(ids):
        print(f"  [{i+1}/{len(ids)}] ID {item_id}", end="")
        
        if item_id in ids_procesados:
            print(f" -> ⏭️  Saltado (Ya procesado en sesión anterior)")
            continue
            
        print() # salto de linea si no fue saltado
        
        try:
            # Enviar referer para simular navegación desde account
            await page.goto(
                f"https://www.revolico.com/item/{item_id}/_/manage",
                wait_until="domcontentloaded",
                referer="https://www.revolico.com/account"
            )
            await detectar_cloudflare_y_salir(page)
            
            # Espera dinámica a que cargue algo relevante en lugar de sleep fijo de 3s
            try:
                await page.wait_for_selector('button:has-text("Renovar anuncio"), a:has-text("Renovar anuncio"), button[aria-label="Close"], button[aria-label="Cerrar"]', timeout=5000)
            except:
                pass

            popup_cerrado = await cerrar_popup(page)
            if popup_cerrado:
                print(f"    🔒 Popup cerrado")

            resultado = await intentar_renovar(page)

            if resultado is True:
                print(f"    ✅ Renovado")
                renovados += 1
                ids_procesados.append(item_id)
                guardar_progreso(correo_activo, ids_procesados)
            elif resultado is None:
                print(f"    ⚠️  Ya renovado hoy")
                ya_renovados += 1
                ids_procesados.append(item_id)
                guardar_progreso(correo_activo, ids_procesados)
            else:
                print(f"    ❌ Falló — se reintentará")
                fallidos.append(item_id)

        except Exception as e:
            print(f"    ❌ Error: {e}")
            fallidos.append(item_id)

    return renovados, ya_renovados, fallidos

async def renovar_anuncios():
    puerto = 9222
    correo_cli = None
    
    for arg in sys.argv:
        if arg.startswith("--port="):
            try:
                puerto = int(arg.split("=")[1])
            except ValueError:
                pass
        if arg.startswith("--email="):
            correo_cli = arg.split("=")[1]

    async with async_playwright() as p:
        print(f"🔌 Conectando a Chrome en el puerto {puerto}...")
        browser = await p.chromium.connect_over_cdp(f"http://localhost:{puerto}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        print("📄 Cargando cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        await detectar_cloudflare_y_salir(page)
        
        # Espera dinámica a que cargue la lista de anuncios (o un enlace)
        try:
            await page.wait_for_selector('a:has-text("Gestionar"), .user-email, h1', timeout=10000)
        except:
            pass

        correo_activo = correo_cli
        if not correo_activo:
            correo_activo = await extraer_correo_pagina(page)
            
        if not correo_activo:
            correo_activo = f"puerto_{puerto}_desconocido"
            print(f"⚠️  No se pudo detectar el correo. Usando estado: {correo_activo}")
        else:
            print(f"📧 Cuenta detectada: {correo_activo}")

        todos_los_ids = await cargar_todos_los_ids(page)
        total = len(todos_los_ids)
        print(f"\n📦 Total de anuncios encontrados: {total}")

        if total == 0:
            print("⚠️  No se encontraron anuncios. ¿Estás logueado en Revolico?")
            return

        # De abajo hacia arriba
        ids_a_procesar = list(reversed(todos_los_ids))

        total_renovados = 0
        total_ya_renovados = 0
        fallidos = []

        # ── Ronda 1: todos ──
        print(f"\n{'='*55}")
        print(f"  RONDA 1 — {len(ids_a_procesar)} anuncios")
        print(f"{'='*55}")
        renovados, ya_renovados, fallidos = await procesar_lista(page, ids_a_procesar, total, correo_activo)
        total_renovados += renovados
        total_ya_renovados += ya_renovados

        # ── Rondas 2 a MAX_RONDAS: solo los fallidos ──
        for ronda in range(2, MAX_RONDAS + 1):
            if not fallidos:
                print(f"\n✨ Sin fallidos — no se necesitan más rondas")
                break

            print(f"\n{'='*55}")
            print(f"  RONDA {ronda} — {len(fallidos)} fallidos a reintentar")
            print(f"{'='*55}")
            
            # En reintentos sí es prudente una pequeña pausa general
            await asyncio.sleep(3)

            renovados, ya_renovados, fallidos = await procesar_lista(page, fallidos, total, correo_activo)
            total_renovados += renovados
            total_ya_renovados += ya_renovados

        # ── Resumen final ──
        print("\n" + "="*55)
        print("📊 RESUMEN FINAL")
        print("="*55)
        print(f"  ✅ Renovados           : {total_renovados}")
        print(f"  ⚠️  Ya renovados hoy   : {total_ya_renovados}")
        print(f"  ❌ Fallidos definitivos: {len(fallidos)}")
        if fallidos:
            print(f"     IDs: {', '.join(fallidos)}")
        print(f"  📦 Total anuncios      : {total}")
        print("="*55)
        
        if not fallidos:
            limpiar_progreso(correo_activo)
            print("🧹 Estado de progreso limpiado (todo completado).")
            
        print("\n🎉 ¡Proceso terminado!")

if __name__ == "__main__":
    asyncio.run(renovar_anuncios())
