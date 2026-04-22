"""
diagnostico_publicar.py — Analiza el formulario de publicar de Revolico
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Corre esto antes de publicar_anuncios.py para confirmar que los
selectores del formulario funcionan en tu versión de Revolico.

Uso:
    python3 diagnostico_publicar.py
"""

import asyncio
from playwright.async_api import async_playwright


async def diagnostico():
    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        print("📄 Navegando al formulario de publicar...")
        await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        print(f"\n{'━'*65}")
        print("1️⃣  INPUT DE FOTOS (file input)")
        print(f"{'━'*65}")
        # Revolico usa un input[type=file] oculto activado por el botón "Añadir fotos"
        for sel in [
            'input[type="file"]',
            'input[accept*="image"]',
            'input[accept*="jpg"]',
            '[class*="upload"] input',
            '[class*="photo"] input',
            '[class*="foto"] input',
            '[class*="image"] input',
        ]:
            els = await page.query_selector_all(sel)
            if els:
                el = els[0]
                accept = await el.get_attribute("accept") or ""
                multiple = await el.get_attribute("multiple")
                name = await el.get_attribute("name") or ""
                print(f"  ✅ '{sel}' → encontrado | accept='{accept}' multiple={multiple} name='{name}'")
            else:
                print(f"  ❌ '{sel}' → no encontrado")

        print(f"\n{'━'*65}")
        print("2️⃣  CAMPOS DE TEXTO (título, precio, descripción)")
        print(f"{'━'*65}")
        campos = {
            "Título": [
                'input[name="title"]',
                'input[placeholder*="título"]',
                'input[placeholder*="Título"]',
                'input[maxlength="120"]',
                '#title',
            ],
            "Precio": [
                'input[name="price"]',
                'input[placeholder*="precio"]',
                'input[placeholder*="Precio"]',
                'input[type="number"]',
                '#price',
            ],
            "Moneda (select)": [
                'select[name*="currency"]',
                'select[name*="moneda"]',
                'button:has-text("USD")',
                '[class*="currency"]',
                'select',
            ],
            "Descripción": [
                'textarea[name="description"]',
                'textarea[placeholder*="descripción"]',
                'textarea[placeholder*="Descripción"]',
                'textarea[maxlength="1000"]',
                'textarea',
            ],
        }
        for nombre, selectores in campos.items():
            print(f"\n  [{nombre}]")
            for sel in selectores:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        tag = await el.evaluate("el => el.tagName")
                        name_attr = await el.get_attribute("name") or ""
                        ph = await el.get_attribute("placeholder") or ""
                        ml = await el.get_attribute("maxlength") or ""
                        print(f"    ✅ '{sel}' → <{tag}> name='{name_attr}' placeholder='{ph}' maxlength='{ml}'")
                        break
                    else:
                        print(f"    ❌ '{sel}'")
                except Exception as e:
                    print(f"    ❌ '{sel}' → error: {e}")

        print(f"\n{'━'*65}")
        print("3️⃣  SELECTOR DE CATEGORÍA")
        print(f"{'━'*65}")
        for sel in [
            'button:has-text("Elige una categoría")',
            'button:has-text("categoría")',
            '[class*="category"] button',
            '[class*="categoria"] button',
            'button[class*="select"]',
            '[data-testid*="category"]',
            '[placeholder*="categoría"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    texto = (await el.inner_text()).strip()[:60]
                    print(f"  ✅ '{sel}' → texto: '{texto}'")
                else:
                    print(f"  ❌ '{sel}'")
            except Exception as e:
                print(f"  ❌ '{sel}' → error: {e}")

        print(f"\n{'━'*65}")
        print("4️⃣  SELECTORES DE UBICACIÓN (provincia / municipio)")
        print(f"{'━'*65}")
        for sel in [
            'select[name*="province"]',
            'select[name*="provincia"]',
            'select[name*="municipality"]',
            'select[name*="municipio"]',
            '[class*="province"] select',
            '[class*="location"] select',
            '[class*="ubicacion"] select',
            'select',                          # todos los selects de la página
        ]:
            try:
                els = await page.query_selector_all(sel)
                if els:
                    for el in els[:3]:
                        name_attr = await el.get_attribute("name") or ""
                        # Ver opciones disponibles
                        opciones = await el.evaluate(
                            "el => Array.from(el.options).slice(0,5).map(o => o.text)"
                        )
                        print(f"  ✅ '{sel}' → name='{name_attr}' opciones: {opciones}")
                else:
                    print(f"  ❌ '{sel}'")
            except Exception as e:
                print(f"  ❌ '{sel}' → error: {e}")

        print(f"\n{'━'*65}")
        print("5️⃣  CAMPOS DE TELÉFONO")
        print(f"{'━'*65}")
        for sel in [
            'input[name*="phone"]',
            'input[name*="telefono"]',
            'input[name*="tel"]',
            'input[type="tel"]',
            'input[placeholder*="teléfono"]',
            'input[placeholder*="Teléfono"]',
            'input[placeholder*="número"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    name_attr = await el.get_attribute("name") or ""
                    ph = await el.get_attribute("placeholder") or ""
                    print(f"  ✅ '{sel}' → name='{name_attr}' placeholder='{ph}'")
                else:
                    print(f"  ❌ '{sel}'")
            except Exception as e:
                print(f"  ❌ '{sel}' → error: {e}")

        print(f"\n{'━'*65}")
        print("6️⃣  BOTÓN PUBLICAR")
        print(f"{'━'*65}")
        for sel in [
            'button:has-text("Publicar anuncio")',
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Publicar")',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    texto = (await el.inner_text()).strip()
                    tipo = await el.get_attribute("type") or ""
                    print(f"  ✅ '{sel}' → texto='{texto}' type='{tipo}'")
                else:
                    print(f"  ❌ '{sel}'")
            except Exception as e:
                print(f"  ❌ '{sel}' → error: {e}")

        print(f"\n{'━'*65}")
        print("7️⃣  TODO EL TEXTO VISIBLE EN EL FORMULARIO")
        print(f"{'━'*65}")
        texto = await page.evaluate("() => document.body.innerText")
        for linea in texto.split("\n"):
            if linea.strip():
                print(f"  |  {linea.strip()}")

        print(f"\n{'━'*65}")
        print("8️⃣  TODOS LOS INPUTS Y SELECTS DE LA PÁGINA")
        print(f"{'━'*65}")
        inputs_info = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input, select, textarea, button[type=submit]'))
                .map(el => ({
                    tag: el.tagName,
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    placeholder: el.placeholder || '',
                    class: el.className.toString().slice(0, 60)
                }))
        """)
        for info in inputs_info:
            if info['type'] != 'hidden':
                print(f"  <{info['tag']}> type={info['type']} name='{info['name']}' "
                      f"id='{info['id']}' placeholder='{info['placeholder']}'")


asyncio.run(diagnostico())
