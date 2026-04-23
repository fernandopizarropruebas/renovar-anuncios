import asyncio
import re
from playwright.async_api import async_playwright

async def cerrar_popup(page):
    try:
        selectores_cierre = [
            'button[aria-label="Close"]',
            'button[aria-label="Cerrar"]',
            '[data-slot="dialog-close"]',
            '[data-slot="dialog-portal"] button',
        ]
        for sel in selectores_cierre:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(1)
                return True
        return False
    except Exception:
        return False

async def intentar_renovar(page):
    MAX_INTENTOS = 3
    for intento in range(1, MAX_INTENTOS + 1):
        if intento > 1:
            print(f"  🔄 Reintentando ({intento}/{MAX_INTENTOS})...")

        botones = await page.query_selector_all('button:has-text("Renovar anuncio")')
        if not botones:
            botones = await page.query_selector_all('a:has-text("Renovar anuncio")')
        if not botones:
            return None  # Ya renovado hoy

        await page.evaluate("el => el.click()", botones[0])
        await asyncio.sleep(2)

        try:
            await page.wait_for_selector(
                'text="Tu anuncio fue renovado.", text="La verificación falló"',
                timeout=20000
            )
        except Exception:
            pass

        if await page.query_selector('text="Tu anuncio fue renovado."'):
            entendido = await page.query_selector('button:has-text("Entendido")')
            if entendido:
                await page.evaluate("el => el.click()", entendido)
            await asyncio.sleep(1)
            return True

        if await page.query_selector('text="La verificación falló"'):
            print(f"  ⚠️  Cloudflare falló, reintentando...")
            reintentar = await page.query_selector('text="Reintentar"')
            if reintentar:
                await page.evaluate("el => el.click()", reintentar)
                await asyncio.sleep(3)
            continue

        await asyncio.sleep(2)
    return False

async def cargar_todos_los_ids(page):
    """Scrollea hasta el fondo hasta que no aparezcan más anuncios nuevos."""
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
                break  # 3 scrolls sin nuevos = llegamos al final
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
            print(f"  📦 {len(ids_vistos)} anuncios cargados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return list(ids_vistos)

async def renovar_anuncios():
    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        print("📄 Cargando cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando que cargue la página (10 segundos)...")
        await asyncio.sleep(10)

        todos_los_ids = await cargar_todos_los_ids(page)
        total = len(todos_los_ids)
        print(f"\n📦 Total de anuncios encontrados: {total}")

        if total == 0:
            print("⚠️  No se encontraron anuncios. ¿Estás logueado en Revolico?")
            return

        # De abajo hacia arriba — los últimos de la lista suben primero
        ids_en_orden = list(reversed(todos_los_ids))
        print(f"🔃 Procesando de abajo hacia arriba\n")

        renovados = 0
        no_disponibles = 0
        errores = 0

        for i, item_id in enumerate(ids_en_orden):
            url_manage = f"https://www.revolico.com/item/{item_id}/_/manage"
            print(f"[{i+1}/{total}] Anuncio ID {item_id}")

            try:
                await page.goto(url_manage, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                popup_cerrado = await cerrar_popup(page)
                if popup_cerrado:
                    print(f"  🔒 Popup cerrado")
                    await asyncio.sleep(1)

                print(f"  ⏳ Renovando...")
                resultado = await intentar_renovar(page)

                if resultado is True:
                    print(f"  ✅ ¡Renovado!")
                    renovados += 1
                elif resultado is None:
                    print(f"  ⚠️  Ya renovado hoy")
                    no_disponibles += 1
                else:
                    print(f"  ❌ No se pudo renovar tras 3 intentos")
                    errores += 1

                await asyncio.sleep(2)

            except Exception as e:
                print(f"  ❌ Error: {e}")
                errores += 1
                continue

        print("\n" + "="*50)
        print("📊 RESUMEN")
        print("="*50)
        print(f"  ✅ Renovados       : {renovados}")
        print(f"  ⚠️  Ya renovados   : {no_disponibles}")
        print(f"  ❌ Fallidos        : {errores}")
        print(f"  📦 Total           : {total}")
        print("="*50)
        print("\n🎉 ¡Proceso terminado!")

asyncio.run(renovar_anuncios())
