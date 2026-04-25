"""
publicar_anuncios-oculta-q-soy-bots.py — Publica anuncios evitando detección Anti-Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Versión modificada del publicador original. Agrega "ruido humano":
- Tiempos de espera aleatorios entre acciones.
- Usa .type() en lugar de .fill() con demoras de milisegundos entre letras.
- Clics mecánicos naturales con duración de pulsación.
- Navegación con cabeceras `Referer` falsificadas para que parezca que entramos desde /home.
"""

import asyncio
import os
import re
import json
import sys
import base64
import random
from pathlib import Path
from playwright.async_api import async_playwright

# Intento de cargar stealth_async si está instalado
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

CARPETA_ANUNCIOS = "anuncios"
MAX_REINTENTOS_FOTOS = 3
ESPERA_CARGA_FOTOS = 10

# Pausa ALEATORIA entre anuncios (mínimo, máximo en segundos)
# Para simular distracción humana o pausas de lectura
PAUSA_RANGO = (25.0, 48.0) 

# ══════════════════════════════════════════════════════════════════════════════

async def obtener_email_cuenta(context):
    cookies = await context.cookies("https://www.revolico.com")
    for c in cookies:
        if c['name'] == 'st-access-token':
            try:
                parts = c['value'].split('.')
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += '=' * (-len(payload) % 4)
                    data = json.loads(base64.b64decode(payload).decode('utf-8'))
                    return data.get("user_email") or data.get("user_name")
            except Exception:
                pass
    return None

def cargar_publicados(archivo):
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def marcar_publicado(registro, id_original, nueva_url, archivo):
    registro[id_original] = {"nueva_url": nueva_url}
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)

def parsear_datos_md(ruta_md):
    with open(ruta_md, "r", encoding="utf-8") as f:
        contenido = f.read()

    datos = {"titulo": "", "precio": "", "moneda": "USD", "categoria": [], "descripcion": ""}

    m = re.search(r'^#\s+(.+)$', contenido, re.MULTILINE)
    if m:
        datos["titulo"] = m.group(1).strip()

    m = re.search(r'\|\s*\*\*Precio\*\*\s*\|\s*([^\|]+)\s*\|', contenido)
    if m:
        raw = m.group(1).strip()
        partes = raw.split()
        if len(partes) >= 2 and partes[-1] in ("USD", "CUP", "MLC"):
            datos["precio"] = partes[0]
            datos["moneda"] = partes[-1]
        else:
            num = re.search(r'\d+', raw)
            datos["precio"] = num.group(0) if num else raw

    m = re.search(r'\|\s*\*\*Categoría\*\*\s*\|\s*([^\|]+)\s*\|', contenido)
    if m:
        segs = [s.strip() for s in m.group(1).split(">")]
        datos["categoria"] = segs[:2]

    # Descripción parcheada
    m = re.search(r'##\s+Descripci[oó]n(.*?)(?=\n#|\Z)', contenido, re.DOTALL)
    if m:
        raw_desc = m.group(1).strip()
        if "## Fotos" in raw_desc:
            raw_desc = raw_desc.split("## Fotos")[0].strip()
            
        lineas = raw_desc.split("\n")
        lineas_reales = [
            l for l in lineas
            if not re.match(r'\s*-\s*`foto_\d+\.\w+`', l)
            and l.strip() not in ("_Sin descripción_", "")
        ]
        datos["descripcion"] = "\n".join(lineas_reales).strip()

    return datos

def listar_fotos(carpeta):
    fotos = []
    vistas = set()
    for patron in ("foto_*.jpg", "foto_*.jpeg", "foto_*.png", "foto_*.webp",
                   "foto_*.JPG", "foto_*.JPEG", "foto_*.PNG", "foto_*.WEBP"):
        for f in Path(carpeta).glob(patron):
            key = f.name.lower()
            if key not in vistas:
                vistas.add(key)
                fotos.append(str(f.resolve()))
    return sorted(fotos, key=os.path.basename)[:10]


# ── Fotos (Anti-Bot) ────────────────────────────────────────────────────────
async def fotos_en_formulario(page):
    for sel in [
        'img[src^="blob:"]', 'img[src^="data:image"]',
        '[class*="preview"] img', '[class*="thumb"] img',
        '[class*="uploaded"] img', '[class*="photo"] img:not([alt="logo"])',
    ]:
        try:
            items = await page.query_selector_all(sel)
            if items: return len(items)
        except Exception: pass
    return 0

async def limpiar_fotos(page):
    for sel in [
        'button[aria-label*="liminar"]', 'button[aria-label*="emove"]',
        'button[aria-label*="lose"]', '[class*="photo"] button',
        '[class*="preview"] button', '[class*="delete"]', '[class*="remove"]',
    ]:
        try:
            btns = await page.query_selector_all(sel)
            for btn in btns:
                await btn.click(force=True, delay=random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.3, 0.7))
            if btns:
                await asyncio.sleep(1)
                return
        except Exception: pass

async def subir_fotos(page, rutas_fotos):
    if not rutas_fotos: return 0
    for intento in range(1, MAX_REINTENTOS_FOTOS + 1):
        print(f"    📸 Fotos — intento {intento}/{MAX_REINTENTOS_FOTOS}")
        try:
            file_input = await page.query_selector('input[type="file"]')
            if not file_input: break
            
            await file_input.set_input_files(rutas_fotos)
            await asyncio.sleep(ESPERA_CARGA_FOTOS + random.uniform(0.5, 2.0))

            n = await fotos_en_formulario(page)
            print(f"    🖼️  {n}/{len(rutas_fotos)} fotos cargadas")
            if n > 0: return n

            if intento < MAX_REINTENTOS_FOTOS:
                await limpiar_fotos(page)
                await asyncio.sleep(3)
        except Exception:
            if intento < MAX_REINTENTOS_FOTOS: await asyncio.sleep(3)
    return 0


# ── Formulario Humanizado ─────────────────────────────────────────────────────

async def type_human(page, selector, valor):
    """Evita rellenar al instante. Emula el tecleo humano letra a letra."""
    try:
        el = await page.query_selector(selector)
        if el:
            # 1. Clic natural en el campo de texto (con demora de soltar botón de Mouse)
            await el.click(delay=random.randint(80, 180))
            await asyncio.sleep(random.uniform(0.2, 0.6))
            
            # 2. Tecleo humano (X ms entre pulsaciones)
            await el.type(str(valor), delay=random.randint(25, 75))
            return True
    except Exception:
        pass
    return False

async def seleccionar_moneda(page, moneda):
    for metodo in [
        lambda: page.select_option('select[name="currency"]', label=moneda),
        lambda: page.select_option('select[name="currency"]', value=moneda.upper()),
    ]:
        try:
            await metodo()
            await asyncio.sleep(random.uniform(0.4, 0.9)) # Pausa extra
            return True
        except Exception:
            pass
    return False

async def seleccionar_categoria(page, segmentos):
    if not segmentos: return False
    subcategoria = segmentos[-1]

    # Abrir categoría mediante click simulado
    for sel in ['[data-testid*="category"]', 'button:has-text("Elige una categoría")']:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click(force=True, delay=random.randint(100, 220))
                await asyncio.sleep(random.uniform(1.8, 2.5))
                break
        except Exception: pass

    # Sugerida
    try:
        texto_modal = await page.evaluate("() => document.body.innerText")
        if subcategoria.lower() in texto_modal.lower():
            btns = await page.query_selector_all('button:has-text("Aceptar")')
            for btn in btns:
                await btn.click(force=True, delay=random.randint(100, 220))
                await asyncio.sleep(random.uniform(1.0, 2.0))
                print(f"      ✅ Sugerencia aceptada: {subcategoria}")
                return True
    except Exception: pass

    print(f"      → Buscando '{subcategoria}' en la lista...")
    
    # Text Has-Text
    for sel in [
        f'li:has-text("{subcategoria}")',
        f'[role="option"]:has-text("{subcategoria}")',
        f'a:has-text("{subcategoria}")',
    ]:
        try:
            els = await page.query_selector_all(sel)
            if els:
                await els[0].click(force=True, delay=random.randint(80, 200))
                await asyncio.sleep(random.uniform(1.2, 2.0))
                print(f"      ✅ '{subcategoria}' seleccionado nativamente")
                return True
        except Exception: pass

    await page.keyboard.press("Escape")
    return False


async def publicar_anuncio(page, item_id, datos, rutas_fotos, preview=False):
    titulo      = datos["titulo"]
    precio      = datos["precio"]
    moneda      = datos["moneda"]
    descripcion = datos["descripcion"]
    categoria   = datos["categoria"]

    print(f"  📝 {titulo}")
    if preview: return "PREVIEW"

    # 1. NAVEGACIÓN HUMANIZADA: Decirle al server que venimos de /account
    # y simular un scroll inicial
    await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded", referer="https://www.revolico.com/account")
    await asyncio.sleep(random.uniform(3.5, 5.0))

    # 2. Fotos
    await subir_fotos(page, rutas_fotos)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # 3. Título (Type en vez de Fill)
    ok = await type_human(page, 'input[name="title"]', titulo[:120])
    print(f"    {'✅' if ok else '⚠️ '} Título (tecleado humano)")

    # 4. Precio
    ok = await type_human(page, 'input[name="price"]', precio)
    print(f"    {'✅' if ok else '⚠️ '} Precio")

    # 5. Moneda
    if moneda != "USD":
        ok = await seleccionar_moneda(page, moneda)

    # 6. Descripción
    # Hacemos un poco de scroll artificial antes de llenar
    await page.evaluate("window.scrollTo(0, 300)")
    await asyncio.sleep(random.uniform(0.5, 1.2))
    ok = await type_human(page, 'textarea[name="description"]', descripcion[:1000])
    print(f"    {'✅' if ok else '⚠️ '} Descripción (tecleada a velocidad humana)")

    # 7. Categoría
    if categoria:
        ok = await seleccionar_categoria(page, categoria)

    # Añadimos ruido: un scroll ciego en la página
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(random.uniform(1.0, 2.5))

    # 8. Publicar usando clic físico
    url_antes = page.url
    try:
        btn = await page.query_selector('button[type="submit"]')
        if btn:
            await btn.click(delay=random.randint(200, 450)) # Clic real sostenido
    except Exception as e:
        return None

    print(f"    ⏳ Esperando backend...")
    try: await page.wait_for_url(lambda u: u != url_antes and "publish" not in u, timeout=25000)
    except Exception: pass

    nueva_url = page.url
    if nueva_url and "item" in nueva_url and "publish" not in nueva_url:
        print(f"    ✅ Publicado → {nueva_url}")
        return nueva_url

    return None

# ══════════════════════════════════════════════════════════════════════════════
async def main():
    preview  = "--preview" in sys.argv
    id_unico = None
    for i, arg in enumerate(sys.argv):
        if arg == "--id" and i + 1 < len(sys.argv): id_unico = sys.argv[i + 1]

    if not os.path.isdir(CARPETA_ANUNCIOS): return

    todos_ids = sorted(
        d for d in os.listdir(CARPETA_ANUNCIOS) if d.isdigit()
        and os.path.exists(os.path.join(CARPETA_ANUNCIOS, d, "datos.md"))
    )
    if id_unico: todos_ids = [i for i in todos_ids if i == id_unico]

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        
        if stealth_async:
            await stealth_async(page)
            print("🥷  Modo Stealth Cargado (Anti-Fingerprint)")

        email = await obtener_email_cuenta(context)
        archivo_registro = f"publicados_en_{email}.json" if email else "publicados_en_cuenta_nueva.json"
        publicados = cargar_publicados(archivo_registro)

        pendientes = todos_ids if id_unico else [i for i in todos_ids if i not in publicados]

        print(f"📂 Anuncios locales     : {len(todos_ids)}")
        print(f"📤 Pendientes de publicar: {len(pendientes)}\n{'='*65}\n")

        if not pendientes: return

        ok_count = 0
        fail_ids = []

        for i, item_id in enumerate(pendientes):
            carpeta = os.path.join(CARPETA_ANUNCIOS, item_id)
            print(f"{'─'*65}\n[{i+1}/{len(pendientes)}] ID original: {item_id}")

            try:
                datos = parsear_datos_md(os.path.join(carpeta, "datos.md"))
                rutas_fotos = listar_fotos(carpeta)
                nueva_url = await publicar_anuncio(page, item_id, datos, rutas_fotos, preview=preview)
            except Exception as e:
                print(f"  ❌ Excepción: {e}")
                nueva_url = None

            if nueva_url:
                if not preview: marcar_publicado(publicados, item_id, nueva_url, archivo_registro)
                ok_count += 1
            else:
                fail_ids.append(item_id)

            if not preview and i < len(pendientes) - 1:
                # PAUSA ANTI-BOT CON CAOS
                espera = random.uniform(PAUSA_RANGO[0], PAUSA_RANGO[1])
                print(f"\n  ⏱️ Pausa anti-detección: Tomando {espera:.1f} segundos de descanso...")
                await asyncio.sleep(espera)

    print("\n✅ ¡Publicación con Camuflaje finalizada!")

if __name__ == "__main__":
    asyncio.run(main())
