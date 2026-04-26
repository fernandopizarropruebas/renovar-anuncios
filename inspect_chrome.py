import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        try:
            print("Conectando a localhost:9222...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            pages_found = 0
            for context in browser.contexts:
                for page in context.pages:
                    url = page.url
                    title = await page.title()
                    print(f"\n[+] Pestaña Abierta: {title}")
                    print(f"    URL: {url}")
                    pages_found += 1
            if pages_found == 0:
                print("No se encontraron páginas abiertas.")
        except Exception as e:
            print("Error conectando o inspeccionando:", e)
            
if __name__ == "__main__":
    asyncio.run(main())
