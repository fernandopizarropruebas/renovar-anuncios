import asyncio
import random
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        print("Navegando a Revolico...")
        await page.goto("https://www.revolico.com/item/publish")
        await asyncio.sleep(4)

        test_title = f"Control Bluetooth Genérico Prueba {random.randint(1000, 9999)}"
        print(f"Publicando título único: {test_title}")

        await page.locator('input[name="title"]').fill(test_title)
        await asyncio.sleep(1)
        await page.locator('input[name="price"]').fill("15")
        await asyncio.sleep(1)
        await page.locator('textarea[name="description"]').fill("Este es un anuncio de prueba para diagnóstico de bots. " * 3)
        await asyncio.sleep(1)
        
        # Categoria Compra/Venta -> Celulares
        print("Buscando caja de categoria...")
        for sel in ['[data-testid*="category"]', 'button:has-text("Elige una categoría")']:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    break
            except Exception: pass
        
        await asyncio.sleep(2)
        # Click Celulares (o listitem celular)
        try:
            els = await page.query_selector_all('li:has-text("Celulares")')
            if els: await els[0].click()
        except:
            await page.keyboard.press("Escape")
            
        await asyncio.sleep(2)
        
        # Publish
        print("Clic en Publicar...")
        btn = await page.query_selector('button[type="submit"]')
        if btn:
            await btn.click()
            
        print("Esperando resolucion de publicación...")
        try:
            await page.wait_for_url("**/item/**", timeout=15000)
            print(f"¡Exito! URL generada: {page.url}")
        except Exception as e:
            print("Error esperando URL:", str(e))
            
if __name__ == "__main__":
    asyncio.run(main())
