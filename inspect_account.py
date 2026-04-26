import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        print(f"Inspeccionando {page.url}...")
        text = await page.evaluate("() => document.body.innerText")
        print("TEXTO EN PANTALLA (primeros 500 chars):")
        print(text[:500])
            
        print("---")
        print("Buscando elementos bloqueados o advertencias...")
        warnings = await page.query_selector_all('text="bot" | text="bloqueado" | text="Advertencia"')
        
        for w in warnings:
            t = await w.inner_text()
            print("WARNING:", t)
            
if __name__ == "__main__":
    asyncio.run(main())
