"""
diagnostico_visitas_v2.py — Busca el contador de visitas en la página PÚBLICA del anuncio
"""

import asyncio
import re
from playwright.async_api import async_playwright

async def diagnostico():
    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # ── Obtener el href completo del primer anuncio ──────────────────────
        print("📄 Cargando cuenta...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        await asyncio.sleep(8)

        links = await page.query_selector_all('a:has-text("Gestionar")')
        if not links:
            print("❌ No se encontraron anuncios.")
            return

        # El href tiene el slug completo: /item/titulo-del-producto-54938179?token=_
        href = await links[0].get_attribute("href")
        print(f"   href encontrado: {href}")

        # Construir URL pública (sin ?token=_)
        slug_match = re.search(r'/item/([^?#]+)', href)
        if not slug_match:
            print(f"❌ No se pudo extraer slug de: {href}")
            return
        slug = slug_match.group(1)
        public_url = f"https://www.revolico.com/item/{slug}"

        # También la URL de gestión para comparar
        id_match = re.search(r'-(\d{7,9})$', slug)
        item_id = id_match.group(1) if id_match else slug
        manage_url = f"https://www.revolico.com/item/{item_id}/_/manage"

        print(f"\n🔍 Anuncio ID: {item_id}")
        print(f"   URL pública:  {public_url}")
        print(f"   URL gestión:  {manage_url}")

        # ════════════════════════════════════════════════════════════════════
        # ANALIZAR PÁGINA PÚBLICA
        # ════════════════════════════════════════════════════════════════════
        print(f"\n{'━'*60}")
        print("📄  ANALIZANDO PÁGINA PÚBLICA")
        print(f"{'━'*60}")

        await page.goto(public_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # 1. Todo el texto visible
        texto = await page.evaluate("() => document.body.innerText")
        print("\n📋 TEXTO COMPLETO VISIBLE EN LA PÁGINA:")
        print("─"*60)
        # Mostrar líneas no vacías
        for linea in texto.split("\n"):
            if linea.strip():
                print(f"  |  {linea.strip()}")
        print("─"*60)

        # 2. Buscar números y posibles contadores
        print("\n🔢 LÍNEAS QUE CONTIENEN NÚMEROS:")
        for linea in texto.split("\n"):
            if linea.strip() and re.search(r'\d', linea):
                print(f"  →  {linea.strip()}")

        # 3. Buscar en el HTML cualquier patrón que parezca un contador
        html = await page.evaluate("() => document.body.innerHTML")

        print(f"\n{'━'*60}")
        print("🔍  BUSCANDO PATRONES DE CONTADOR EN EL HTML")
        print(f"{'━'*60}")

        patrones = {
            "visita/s":      r'(\d+)\s*visitas?',
            "vista/s":       r'(\d+)\s*vistas?',
            "view/s":        r'(\d+)\s*views?',
            "JSON visits":   r'"visits?"\s*:\s*(\d+)',
            "JSON visitas":  r'"visitas?"\s*:\s*(\d+)',
            "JSON views":    r'"views?"\s*:\s*(\d+)',
            "data-visits":   r'data-visits?=.?(\d+)',
        }
        encontrado = False
        for nombre, patron in patrones.items():
            m = re.search(patron, html, re.IGNORECASE)
            if m:
                print(f"  ✅ [{nombre}] → valor: {m.group(1)}")
                encontrado = True
            else:
                print(f"  ❌ [{nombre}] → no encontrado")

        # 4. Dump del HTML completo de la sección principal (para inspección manual)
        print(f"\n{'━'*60}")
        print("📝  HTML DE LA SECCIÓN PRINCIPAL (primeros 4000 chars)")
        print(f"{'━'*60}")
        # Intentar solo el main/article
        try:
            html_main = await page.evaluate("""
                () => {
                    const el = document.querySelector('main, article, [class*=detail], [class*=Detail]');
                    return el ? el.innerHTML : document.body.innerHTML;
                }
            """)
            print(html_main[:4000])
        except Exception as e:
            print(f"Error: {e}")
            print(html[:4000])

        # ════════════════════════════════════════════════════════════════════
        # ANALIZAR PÁGINA DE GESTIÓN TAMBIÉN
        # ════════════════════════════════════════════════════════════════════
        print(f"\n{'━'*60}")
        print("📄  TEXTO COMPLETO EN PÁGINA DE GESTIÓN (/_/manage)")
        print(f"{'━'*60}")

        await page.goto(manage_url, wait_until="domcontentloaded")
        await asyncio.sleep(4)
        # Cerrar popup
        for sel in ['[data-slot="dialog-portal"] button', 'button[aria-label="Close"]', 'button[aria-label="Cerrar"]']:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(1)
                break

        texto_m = await page.evaluate("() => document.body.innerText")
        print("\n📋 TODO EL TEXTO VISIBLE EN GESTIÓN:")
        print("─"*60)
        for linea in texto_m.split("\n"):
            if linea.strip():
                print(f"  |  {linea.strip()}")
        print("─"*60)

asyncio.run(diagnostico())
