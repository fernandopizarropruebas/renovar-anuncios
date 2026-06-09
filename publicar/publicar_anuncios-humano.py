"""
publicar_anuncios-humano.py — Bot Nativo y Definitivo Anti-Baneos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funcionalidades:
 1. Emulación React-Friendly: Usa .fill() que Chrome interpreta como Autocompletado,
    lo que históricamente nos evitó las alertas rojas de Cloudflare.
 2. Image Hash-Busting: Pillow altera 1 píxel y recompresa la foto para evadir
    las detecciones de clonación.
 3. Descriptive Organic Hash-Busting: Inyecta textos de cierre humanos del fichero externo
    en vez de caracteres mágicos invisibles de Black-Hat.
 4. Ráfagas Dinámicas: Publica 10 (con margen) anuncios y duerme por largo tiempo.
"""

import asyncio
import os
import re
import json
import sys
import base64
import random
import tempfile
from pathlib import Path
from PIL import Image, ImageEnhance
from playwright.async_api import async_playwright

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN (Puntos Modificables del Sistema)
# ══════════════════════════════════════════════════════════════════════════════

CARPETA_ANUNCIOS = "anuncios"
MAX_REINTENTOS_FOTOS = 3
ESPERA_CARGA_FOTOS = 10
ORDEN_PUBLICACION = "DESC"

# === MECÁNICA DE RÁFAGAS ===
# Pausa estandar entre 2 anuncios de la misma ráfaga (segundos)
PAUSA_ENTRE_ANUNCIOS = (10.0, 18.0)

# Configuraciones de Ráfaga
ANUNCIOS_POR_RAFAGA_BASE = 10
ESPERA_RAFAGA_MINUTOS = 20

# Diccionario de ofuscación de frases (Ataque al motor de duplicados)
ARCHIVO_FRASES = "documentacion/frases_despedida.md"
frases_diccionario = []
if os.path.exists(ARCHIVO_FRASES):
    with open(ARCHIVO_FRASES, "r", encoding="utf-8") as f:
        for linea in f:
            l = linea.strip()
            if l and not l.startswith("#") and not l.startswith("-"):
                frases_diccionario.append(l)

# ══════════════════════════════════════════════════════════════════════════════

def inyectar_frase(descripcion):
    if not frases_diccionario: return descripcion
    frases = random.sample(frases_diccionario, k=random.randint(1, 2))
    inyeccion = "\n" + " ".join(frases)
    return (descripcion + inyeccion).strip()

def hashbust_image(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(random.uniform(0.97, 1.03))
            
            w, h = img.size
            if w > 10 and h > 10:
                recorte_w = random.randint(0, 2)
                recorte_h = random.randint(0, 2)
                img = img.crop((0, 0, w - recorte_w, h - recorte_h))
            img.save(output_path, "JPEG", quality=random.randint(89, 98))
            return True
    except Exception:
        return False

# ── IDENTIFICACIÓN Y LOGEO ──────────────────────────────────────────────────

async def obtener_email_cuenta(context):
    cookies = await context.cookies("https://www.revolico.com")
    for c in cookies:
        if c['name'] == 'st-access-token':
            try:
                parts = c['value'].split('.')
                payload = parts[1] + '=' * (-len(parts[1]) % 4)
                data = json.loads(base64.b64decode(payload).decode('utf-8'))
                return data.get("user_email") or data.get("user_name")
            except: pass
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
    if m: datos["titulo"] = m.group(1).strip()

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

    m = re.search(r'##\s+Descripci[oó]n(.*?)(?=\n#|\Z)', contenido, re.DOTALL)
    if m:
        raw_desc = m.group(1).strip()
        if "## Fotos" in raw_desc:
            raw_desc = raw_desc.split("## Fotos")[0].strip()
        lineas = raw_desc.split("\n")
        lineas_reales = [ l for l in lineas if not re.match(r'\s*-\s*`foto_\d+\.\w+`', l) and l.strip() not in ("_Sin descripción_", "") ]
        datos["descripcion"] = "\n".join(lineas_reales).strip()
    return datos

def listar_fotos(carpeta):
    fotos = []
    vistas = set()
    for patron in ("foto_*.jpg", "foto_*.jpeg", "foto_*.png", "foto_*.webp", "foto_*.JPG", "foto_*.JPEG", "foto_*.PNG", "foto_*.WEBP"):
        for f in Path(carpeta).glob(patron):
            key = f.name.lower()
            if key not in vistas:
                vistas.add(key)
                fotos.append(str(f.resolve()))
    return sorted(fotos, key=os.path.basename)[:10]

# ── INTERACTUADORES DEL FRONT-END ──────────────────────────────────────────

async def fill(page, selector, valor):
    # Mecánica ORIGINAL del publicar_anuncios.py (Instant fill natural al DOM, super inocente para Cloudflare)
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click()
            await asyncio.sleep(0.2)
            await el.fill(str(valor))
            return True
    except: pass
    return False

async def seleccionar_moneda(page, moneda):
    for metodo in [
        lambda: page.select_option('select[name="currency"]', label=moneda),
        lambda: page.select_option('select[name="currency"]', value=moneda.upper()),
    ]:
        try:
            await metodo()
            return True
        except: pass
    return False

async def seleccionar_categoria(page, segmentos):
    if not segmentos: return False
    subcategoria = segmentos[-1]

    for sel in ['[data-testid*="category"]', 'button:has-text("Elige una categoría")']:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(2)
                break
        except: pass

    try:
        texto_modal = await page.evaluate("() => document.body.innerText")
        if subcategoria.lower() in texto_modal.lower():
            aceptar = await page.evaluate("() => { const btns = Array.from(document.querySelectorAll('button')); const btn = btns.find(b => b.innerText.trim() === 'Aceptar'); if (btn) { btn.click(); return true; } return false; }")
            if aceptar:
                await asyncio.sleep(1.5)
                return True
    except: pass

    try:
        encontrado = await page.evaluate(f"() => {{ const todos = Array.from(document.querySelectorAll('li, [role=\"option\"], [role=\"listitem\"], a, span, p')); const el = todos.find(e => e.innerText.trim() === '{subcategoria}'); if (el) {{ el.click(); return true; }} return false; }}")
        if encontrado:
            await asyncio.sleep(1.5)
            return True
    except: pass

    for sel in [f'li:has-text("{subcategoria}")', f'[role="option"]:has-text("{subcategoria}")', f'[role="listitem"]:has-text("{subcategoria}")', f'a:has-text("{subcategoria}")']:
        try:
            els = await page.query_selector_all(sel)
            if els:
                textos = [(await e.inner_text(), e) for e in els]
                textos.sort(key=lambda x: len(x[0]))
                await page.evaluate("el => el.click()", textos[0][1])
                await asyncio.sleep(1.5)
                return True
        except: pass

    await page.keyboard.press("Escape")
    return False

async def fotos_en_formulario(page):
    for sel in ['img[src^="blob:"]', 'img[src^="data:image"]', '[class*="preview"] img', '[class*="thumb"] img', '[class*="uploaded"] img', '[class*="photo"] img:not([alt="logo"])']:
        try:
            items = await page.query_selector_all(sel)
            if items: return len(items)
        except: pass
    return 0

async def limpiar_fotos(page):
    for sel in ['button[aria-label*="liminar"]', 'button[aria-label*="emove"]', 'button[aria-label*="lose"]', '[class*="photo"] button', '[class*="preview"] button', '[class*="delete"]', '[class*="remove"]']:
        try:
            btns = await page.query_selector_all(sel)
            for btn in btns:
                await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(0.4)
            if btns:
                await asyncio.sleep(1)
                return
        except: pass

async def subir_fotos(page, rutas_fotos):
    if not rutas_fotos: return 0
    
    # === HASH-BUSTING FOTOS ===
    temp_dir = tempfile.mkdtemp()
    rutas_busted = []
    print("    🎨 Reconfigurando fotos (Anti-Clonación MD5)...")
    for idx, original_file in enumerate(rutas_fotos):
        busted_file = os.path.join(temp_dir, f"hacked_{idx}_{random.randint(100,999)}.jpg")
        if hashbust_image(original_file, busted_file):
            rutas_busted.append(busted_file)
        else:
            rutas_busted.append(original_file)

    for intento in range(1, MAX_REINTENTOS_FOTOS + 1):
        print(f"    📸 Fotos — intento {intento}/{MAX_REINTENTOS_FOTOS}")
        try:
            file_input = await page.query_selector('input[type="file"]')
            if not file_input: break
            await file_input.set_input_files(rutas_busted)
            await asyncio.sleep(ESPERA_CARGA_FOTOS)
            n = await fotos_en_formulario(page)
            if n > 0: return n
            if intento < MAX_REINTENTOS_FOTOS:
                await limpiar_fotos(page)
                await asyncio.sleep(3)
        except Exception:
            if intento < MAX_REINTENTOS_FOTOS: await asyncio.sleep(3)
    return 0

# ── LOGICA CENTRAL PUBLICACIÓN ──────────────────────────────────────────────

async def publicar_anuncio(page, item_id, datos, rutas_fotos, preview=False):
    titulo      = datos["titulo"]
    precio_original = datos["precio"]
    moneda      = datos["moneda"]
    categoria   = datos["categoria"]
    
    # Inyectar texto Genuinamente! (Anti-Clon)
    descripcion = inyectar_frase(datos["descripcion"])

    # === Lógica dinámica de incremento de precio y mensajería ===
    precio_final = precio_original
    try:
        precio_num = int(precio_original)
        incremento = (int(precio_num / 50) + 1) * 5
        precio_final = str(precio_num + incremento)
        
        if incremento >= 20:
            descripcion += "\n\nmensajeria gratis en toda la habana"
        elif incremento >= 10:
            descripcion += "\n\nmensajeria gratis para casi toda la habana"
    except (ValueError, TypeError):
        pass # Si el precio no era un número válido, lo dejamos intacto

    print(f"  📝 {titulo} (Precio final: {precio_final} {moneda})")
    if preview: return "PREVIEW"

    # Mecánica originaria directa sin Headers raros (SPA Native-Friendly)
    await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded")
    await asyncio.sleep(4)

    await subir_fotos(page, rutas_fotos)
    ok = await fill(page, 'input[name="title"]', titulo[:120])
    ok = await fill(page, 'input[name="price"]', precio_final)
    if moneda != "USD": await seleccionar_moneda(page, moneda)
    ok = await fill(page, 'textarea[name="description"]', descripcion[:1000])

    if categoria:
        await seleccionar_categoria(page, categoria)

    url_antes = page.url
    try:
        btn = await page.query_selector('button[type="submit"]')
        if btn: await page.evaluate("el => el.click()", btn)
    except: pass

    print(f"    ⏳ Esperando confirmación...")
    try:
        await page.wait_for_url(lambda url: url != url_antes and "publish" not in url, timeout=20000)
    except: pass

    nueva_url = page.url
    if nueva_url and "item" in nueva_url and "publish" not in nueva_url:
        print(f"    ✅ Publicado → {nueva_url}")
        return nueva_url

    return None

# ══════════════════════════════════════════════════════════════════════════════
async def main():
    preview = "--preview" in sys.argv
    ids_unicos = []
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        for arg in sys.argv[idx+1:]:
            if arg.startswith("--"): break
            ids_unicos.append(arg)

    if not os.path.isdir(CARPETA_ANUNCIOS): return

    todos_ids = sorted(
        (d for d in os.listdir(CARPETA_ANUNCIOS) if d.isdigit() and os.path.exists(os.path.join(CARPETA_ANUNCIOS, d, "datos.md"))),
        reverse=(ORDEN_PUBLICACION == "DESC")
    )
    if ids_unicos: todos_ids = [i for i in todos_ids if i in ids_unicos]

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        email = await obtener_email_cuenta(context)
        archivo_registro = f"publicados_en_{email}.json" if email else "publicados_en_cuenta_nueva.json"
        publicados = cargar_publicados(archivo_registro)

        pendientes = todos_ids if ids_unicos else [i for i in todos_ids if i not in publicados]

        print(f"📂 Anuncios locales      : {len(todos_ids)}")
        print(f"📤 Pendientes de publicar: {len(pendientes)}\n{'='*65}\n")

        if not pendientes: return

        ok_count = 0
        fail_ids = []
        
        # Estado de Ráfaga
        anuncios_en_esta_rafaga = 0
        limite_rafaga_actual = random.randint(ANUNCIOS_POR_RAFAGA_BASE - 2, ANUNCIOS_POR_RAFAGA_BASE + 3)

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
                anuncios_en_esta_rafaga += 1
            else:
                fail_ids.append(item_id)

            if not preview and i < len(pendientes) - 1:
                # Comprobar si hemos quemado la ráfaga actual
                if anuncios_en_esta_rafaga >= limite_rafaga_actual:
                    descanso = random.uniform(ESPERA_RAFAGA_MINUTOS - 5, ESPERA_RAFAGA_MINUTOS + 5)
                    print(f"\n  ☕ [RÁFAGA COMPLETADA] Bot yendo a descansar {descanso:.1f} minutos para parecer humano...")
                    await asyncio.sleep(descanso * 60)
                    
                    # Reiniciar ráfaga para el siguiente bloque
                    anuncios_en_esta_rafaga = 0
                    limite_rafaga_actual = random.randint(ANUNCIOS_POR_RAFAGA_BASE - 2, ANUNCIOS_POR_RAFAGA_BASE + 3)
                    print(f"  ☕ Bot regresó. Nueva tolerancia de ráfaga: {limite_rafaga_actual} anuncios.\n")
                else:
                    # Pausa normal entre anuncios de la misma ráfaga
                    espera = random.uniform(PAUSA_ENTRE_ANUNCIOS[0], PAUSA_ENTRE_ANUNCIOS[1])
                    print(f"\n  ⏳ Pausa entre anuncios: {espera:.1f}s...")
                    await asyncio.sleep(espera)

    print("\n✅ ¡Escuadrón Biológico Frontal Finalizado!")

if __name__ == "__main__":
    asyncio.run(main())
