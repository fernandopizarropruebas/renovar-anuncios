"""
publicar-antiduplicados.py — Publicador Supremo (Anti-Bot + Anti-Duplicados MD5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hereda todas las funciones de camuflaje biológico (Jitter y type_human).
PERO añade la capa de evasión 'Hash-Busting' matemática:

1. FOTOS: Recorta 1 o 2 píxeles aleatoriamente, cambia el brillo en un 1%, 
   altera el nivel de compresión JPGE, y cambia 1 píxel al azar en la esquina.
   La foto se verá 100% igual al ojo humano, pero el Servidor verá un archivo NUEVO.
   
2. TEXTO: Inyecta espacios Unicode "Zero-Width" (invisibles) al azar en el Título 
   y la Descripción. Modifica drásticamente la estructura criptográfica original,
   rompiendo el análisis de coincidencia de cadenas al 100% en la red.
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

try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

CARPETA_ANUNCIOS = "anuncios"
MAX_REINTENTOS_FOTOS = 3
ESPERA_CARGA_FOTOS = 10
PAUSA_RANGO = (25.0, 48.0) 

# Orden de publicación: "DESC" = últimos primero, "ASC" = primeros primero
ORDEN_PUBLICACION = "DESC"

# ── CAPA ANTI-DUPLICADOS (HASH-BUSTING) ──────────────────────────────────────

def hashbust_image(input_path, output_path):
    """Genera una imagen visualmente idéntica pero matemáticamente distinta."""
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 1. Micro alteración de color/contraste impreceptible (Rango muy sutil)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(random.uniform(0.97, 1.03))
            
            # 2. Recorte de píxeles fantasmas (0 a 2 píxeles de ancho y alto)
            w, h = img.size
            if w > 10 and h > 10:  # validar seguridad
                recorte_w = random.randint(0, 2)
                recorte_h = random.randint(0, 2)
                img = img.crop((0, 0, w - recorte_w, h - recorte_h))
            
            # 3. Mancha cuántica (1 pixel al azar de un color modificado en una esquina)
            try:
                px = random.randint(0, 3)
                py = random.randint(0, 3)
                fake_color = random.randint(20, 240)
                img.putpixel((px, py), (fake_color, fake_color, fake_color))
            except Exception:
                pass
                 
            # 4. Guardado con recomprecion JPG dinámica
            img.save(output_path, "JPEG", quality=random.randint(89, 98))
            return True
    except Exception as e:
        print(f"    ⚠️ Error de camuflaje en foto: {e}")
        return False

def hashbust_text(text):
    """
    Inyecta secuencias Unicode invisisbles (Zero-Width Space \u200B) 
    para que el texto sea distinto para los servidores anti-Spam.
    """
    if not text: return text
    zero_width_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
    
    # Inyectamos el ruido invisible generalemente al FINAL del titulo
    invisible_tail = "".join(random.choices(zero_width_chars, k=random.randint(3, 10)))
    
    # A veces podemos meter uno microscopico en el medio (solo 50% chance)
    if len(text) > 5 and random.random() > 0.5:
        mitad = len(text) // 2
        invisible_mid = random.choice(zero_width_chars)
        text = text[:mitad] + invisible_mid + text[mitad:]
        
    return text + invisible_tail

def hashbust_description(desc):
    """Igual pero para multilinea en descripciones largas."""
    if not desc: return desc
    zero_width_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
    lineas = desc.split('\n')
    nuevas_lineas = []
    
    for l in lineas:
        if l.strip():
            # Inyecta polvo invisible al final de cada frase
            polvo = "".join(random.choices(zero_width_chars, k=random.randint(1, 4)))
            nuevas_lineas.append(l + polvo)
        else:
            nuevas_lineas.append(l)
    return "\n".join(nuevas_lineas)

# ══════════════════════════════════════════════════════════════════════════════

async def obtener_email_cuenta(context):
    cookies = await context.cookies("https://www.revolico.com")
    for c in cookies:
        if c['name'] == 'st-access-token':
            try:
                parts = c['value'].split('.')
                payload = parts[1] + '=' * (-len(parts[1]) % 4)
                data = json.loads(base64.b64decode(payload).decode('utf-8'))
                return data.get("user_email") or data.get("user_name")
            except Exception: pass
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

# ── Capa Interacción ────────────────────────────────────────────────────────

async def fotos_en_formulario(page):
    for sel in ['img[src^="blob:"]', 'img[src^="data:image"]', '[class*="preview"] img', '[class*="photo"] img:not([alt="logo"])']:
        try:
            items = await page.query_selector_all(sel)
            if items: return len(items)
        except: pass
    return 0

async def limpiar_fotos(page):
    for sel in ['button[aria-label*="liminar"]', 'button[aria-label*="emove"]', '[class*="photo"] button', '[class*="preview"] button']:
        try:
            btns = await page.query_selector_all(sel)
            for btn in btns:
                await btn.click(force=True, delay=random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.3, 0.7))
            if btns:
                await asyncio.sleep(1)
                return
        except: pass

async def subir_fotos(page, rutas_fotos):
    if not rutas_fotos: return 0
    
    # === RUTINA DE HASH-BUSTING EN IMÁGENES ===
    print("    🎨 Camuflando y reescribiendo pixeles de fotos al vuelo...")
    temp_dir = tempfile.mkdtemp()
    rutas_busted = []
    for idx, original_file in enumerate(rutas_fotos):
        busted_file = os.path.join(temp_dir, f"hacked_{idx}_{random.randint(100,999)}.jpg")
        if hashbust_image(original_file, busted_file):
            rutas_busted.append(busted_file)
        else:
            rutas_busted.append(original_file)
            
    for intento in range(1, MAX_REINTENTOS_FOTOS + 1):
        print(f"    📸 Subiendo Fotos Evadidas — intento {intento}/{MAX_REINTENTOS_FOTOS}")
        try:
            file_input = await page.query_selector('input[type="file"]')
            if not file_input: break
            
            await file_input.set_input_files(rutas_busted)
            await asyncio.sleep(ESPERA_CARGA_FOTOS + random.uniform(0.5, 2.0))

            n = await fotos_en_formulario(page)
            print(f"    🖼️  {n}/{len(rutas_busted)} fotos cargadas firmemente")
            
            if n > 0: return n

            if intento < MAX_REINTENTOS_FOTOS:
                await limpiar_fotos(page)
                await asyncio.sleep(3)
        except Exception:
            if intento < MAX_REINTENTOS_FOTOS: await asyncio.sleep(3)
            
    return 0

async def type_human(page, selector, valor):
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click(delay=random.randint(80, 180))
            await asyncio.sleep(random.uniform(0.2, 0.6))
            await el.type(str(valor), delay=random.randint(25, 70))
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
            await asyncio.sleep(random.uniform(0.4, 0.9))
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
                await btn.click(force=True, delay=random.randint(100, 220))
                await asyncio.sleep(random.uniform(1.5, 2.2))
                break
        except: pass

    try:
        texto_modal = await page.evaluate("() => document.body.innerText")
        if subcategoria.lower() in texto_modal.lower():
            btns = await page.query_selector_all('button:has-text("Aceptar")')
            for btn in btns:
                await btn.click(force=True, delay=random.randint(100, 220))
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return True
    except: pass

    for sel in [f'li:has-text("{subcategoria}")', f'[role="option"]:has-text("{subcategoria}")', f'a:has-text("{subcategoria}")']:
        try:
            els = await page.query_selector_all(sel)
            if els:
                await els[0].click(force=True, delay=random.randint(80, 200))
                await asyncio.sleep(random.uniform(1.0, 1.5))
                return True
        except: pass

    await page.keyboard.press("Escape")
    return False


async def publicar_anuncio(page, item_id, datos, rutas_fotos, preview=False):
    # === APLICAR POLVO INVISIBLE (Hash-Busting Textual) ===
    titulo      = hashbust_text(datos["titulo"])
    descripcion = hashbust_description(datos["descripcion"])
    
    precio      = datos["precio"]
    moneda      = datos["moneda"]
    categoria   = datos["categoria"]

    print(f"  📝 {datos['titulo']}")
    if preview: return "PREVIEW"

    await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded", referer="https://www.revolico.com/account")
    await asyncio.sleep(random.uniform(3.5, 5.0))

    await subir_fotos(page, rutas_fotos)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    ok = await type_human(page, 'input[name="title"]', titulo[:120])
    print(f"    {'✅' if ok else '⚠️ '} Título (Ofuscado MD5 + Humano)")

    ok = await type_human(page, 'input[name="price"]', precio)
    print(f"    {'✅' if ok else '⚠️ '} Precio")

    if moneda != "USD":
        ok = await seleccionar_moneda(page, moneda)

    await page.evaluate("window.scrollTo(0, 300)")
    await asyncio.sleep(random.uniform(0.5, 1.2))
    ok = await type_human(page, 'textarea[name="description"]', descripcion[:1000])
    print(f"    {'✅' if ok else '⚠️ '} Descripción (Ofuscada MD5 + Humana)")

    if categoria:
        ok = await seleccionar_categoria(page, categoria)

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(random.uniform(1.0, 2.5))

    url_antes = page.url
    try:
        btn = await page.query_selector('button[type="submit"]')
        if btn:
            await btn.click(delay=random.randint(200, 450)) 
    except: return None

    print(f"    ⏳ Esperando verificación del Backend...")
    try: await page.wait_for_url(lambda u: u != url_antes and "publish" not in u, timeout=25000)
    except: pass

    nueva_url = page.url
    if nueva_url and "item" in nueva_url and "publish" not in nueva_url:
        print(f"    ✅ Desplegado indetectablemente → {nueva_url}")
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
        (d for d in os.listdir(CARPETA_ANUNCIOS) if d.isdigit()
        and os.path.exists(os.path.join(CARPETA_ANUNCIOS, d, "datos.md"))),
        reverse=(ORDEN_PUBLICACION == "DESC")
    )
    if ids_unicos: todos_ids = [i for i in todos_ids if i in ids_unicos]

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        
        if stealth_async:
            await stealth_async(page)
            print("🥷  Modo Stealth WebActivado (Anti-Fingerprint)")

        email = await obtener_email_cuenta(context)
        archivo_registro = f"publicados_en_{email}.json" if email else "publicados_en_cuenta_nueva.json"
        publicados = cargar_publicados(archivo_registro)

        pendientes = todos_ids if ids_unicos else [i for i in todos_ids if i not in publicados]

        print(f"📂 Anuncios locales      : {len(todos_ids)}")
        print(f"⭐ Protocolo Activo     : Anti-Bots y Hash-Busting de Contenido Activo")
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
                print(f"  ❌ Excepción crítica: {e}")
                nueva_url = None

            if nueva_url:
                if not preview: marcar_publicado(publicados, item_id, nueva_url, archivo_registro)
                ok_count += 1
            else:
                fail_ids.append(item_id)

            if not preview and i < len(pendientes) - 1:
                espera = random.uniform(PAUSA_RANGO[0], PAUSA_RANGO[1])
                print(f"\n  ⏱️ Pausa anti-detección: Reestructurando patrones... ({espera:.1f}s)")
                await asyncio.sleep(espera)

    print("\n✅ ¡Escuadrón Supremo de Publicación Finalizado!")

if __name__ == "__main__":
    asyncio.run(main())
