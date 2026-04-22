import asyncio
import re
from playwright.async_api import async_playwright

MAX_RONDAS = 5

async def cerrar_popup(page):
    try:
        for sel in ['button[aria-label="Close"]', 'button[aria-label="Cerrar"]',
                    '[data-slot="dialog-close"]', '[data-slot="dialog-portal"] button']:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(1)
                return True
        return False
    except Exception:
        return False

async def intentar_renovar(page):
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
        print(f"  ⚠️  Cloudflare falló")
        # Retornamos False inmediatamente para que lo acumule en la cola de 'fallidos' para las próximas rondas
        return False

    await asyncio.sleep(2)
    return False

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
        await asyncio.sleep(2)
    return list(ids_vistos)

async def procesar_lista(page, ids, total_global):
    """Procesa una lista de IDs. Devuelve (renovados, ya_renovados, fallidos)."""
    fallidos = []
    renovados = 0
    ya_renovados = 0

    for i, item_id in enumerate(ids):
        print(f"  [{i+1}/{len(ids)}] ID {item_id}")
        try:
            await page.goto(
                f"https://www.revolico.com/item/{item_id}/_/manage",
                wait_until="domcontentloaded"
            )
            await asyncio.sleep(3)

            popup_cerrado = await cerrar_popup(page)
            if popup_cerrado:
                print(f"    🔒 Popup cerrado")
                await asyncio.sleep(1)

            resultado = await intentar_renovar(page)

            if resultado is True:
                print(f"    ✅ Renovado")
                renovados += 1
            elif resultado is None:
                print(f"    ⚠️  Ya renovado hoy")
                ya_renovados += 1
            else:
                print(f"    ❌ Falló — se reintentará")
                fallidos.append(item_id)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"    ❌ Error: {e}")
            fallidos.append(item_id)

    return renovados, ya_renovados, fallidos

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

        # De abajo hacia arriba
        ids_a_procesar = list(reversed(todos_los_ids))

        total_renovados = 0
        total_ya_renovados = 0
        fallidos = []

        # ── Ronda 1: todos ──
        print(f"\n{'='*55}")
        print(f"  RONDA 1 — {len(ids_a_procesar)} anuncios")
        print(f"{'='*55}")
        renovados, ya_renovados, fallidos = await procesar_lista(page, ids_a_procesar, total)
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
            await asyncio.sleep(5)

            renovados, ya_renovados, fallidos = await procesar_lista(page, fallidos, total)
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
        print("\n🎉 ¡Proceso terminado!")

asyncio.run(renovar_anuncios())
