import asyncio
from playwright.async_api import async_playwright

async def diagnostico():
    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # Navegar directamente — así Playwright controla la navegación
        print("📄 Navegando a tu cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        
        print("⏳ Esperando que se estabilice la página (10 segundos)...")
        await asyncio.sleep(10)
        
        print(f"📄 URL actual: {page.url}")

        # Scroll gradual
        print("⬇️  Scrolleando para cargar anuncios...")
        for i in range(8):
            try:
                await page.evaluate(f"window.scrollTo(0, {(i+1) * 600})")
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"  scroll error ignorado: {e}")
                await asyncio.sleep(2)

        print("\n🔍 Buscando botones 'Gestionar' con distintos selectores:")
        
        selectores = [
            'a[href*="/_/manage"]',
            'a[href*="/manage"]',
            'a[href*="item"]',
            'button:has-text("Gestionar")',
            'a:has-text("Gestionar")',
        ]
        
        for sel in selectores:
            try:
                elementos = await page.query_selector_all(sel)
                if elementos:
                    print(f"  ✅ '{sel}' → {len(elementos)} encontrados")
                    el = elementos[0]
                    href = await el.get_attribute("href")
                    texto = await el.inner_text()
                    tag = await el.evaluate("el => el.tagName")
                    print(f"     Ejemplo: <{tag}> href='{href}' texto='{texto.strip()[:60]}'")
                else:
                    print(f"  ❌ '{sel}' → 0 encontrados")
            except Exception as e:
                print(f"  ❌ '{sel}' → error: {e}")

        print("\n📝 HTML zona central de la página (chars 3000-6000):")
        try:
            html = await page.evaluate("() => document.body.innerHTML")
            print(html[3000:6000])
        except Exception as e:
            print(f"Error obteniendo HTML: {e}")

asyncio.run(diagnostico())
