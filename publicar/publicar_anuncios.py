"""
publicar_anuncios.py — Publica anuncios en Revolico desde la carpeta anuncios/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Lee los datos de la carpeta anuncios/ (generada por descargar_anuncios.py)
y los publica uno a uno en la cuenta activa de Revolico.

NOTA: Provincia, municipio y teléfono se configuran en el perfil de la cuenta
y Revolico los pre-rellena automáticamente — el script NO los toca.

Lo que rellena el script por cada anuncio:
    ✅ Fotos (hasta 10, con reintentos limitados)
    ✅ Título
    ✅ Precio y moneda
    ✅ Descripción
    ✅ Categoría (navegando el modal)

Uso:
    python3 publicar_anuncios.py                    # publica todos los pendientes
    python3 publicar_anuncios.py --id 54129284      # publica solo ese ID
    python3 publicar_anuncios.py --preview          # muestra qué haría sin publicar nada
"""

import asyncio
import os
import re
import json
import sys
import base64
from pathlib import Path
from playwright.async_api import async_playwright

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Carpeta con los anuncios descargados por descargar_anuncios.py
CARPETA_ANUNCIOS = "anuncios"

# Intentos máximos de subir fotos — si se agotan, publica sin fotos y sigue
MAX_REINTENTOS_FOTOS = 3

# Segundos a esperar tras subir fotos para que terminen de cargar
ESPERA_CARGA_FOTOS = 10

# Pausa entre anuncios (segundos) para no disparar Cloudflare
PAUSA_ENTRE_ANUNCIOS = 12

# ══════════════════════════════════════════════════════════════════════════════


# ── Identificar Cuenta y Registro ─────────────────────────────────────────────

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


# ── Parsear datos.md ──────────────────────────────────────────────────────────

def parsear_datos_md(ruta_md):
    """
    Extrae titulo, precio, moneda, categoria (lista de 2 niveles), descripcion
    del formato guardado por descargar_anuncios.py.

    Ejemplo de datos.md:
        # Espejos asimétricos
        | **Precio** | 110 USD |
        | **Categoría** | Hogar > Muebles > La Habana > Diez de Octubre |
        ## Descripción
        Espejos asimétricos en varios tamaños...
    """
    with open(ruta_md, "r", encoding="utf-8") as f:
        contenido = f.read()

    datos = {"titulo": "", "precio": "", "moneda": "USD", "categoria": [], "descripcion": ""}

    # Título
    m = re.search(r'^#\s+(.+)$', contenido, re.MULTILINE)
    if m:
        datos["titulo"] = m.group(1).strip()

    # Precio y moneda: "| **Precio** | 110 USD |"
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

    # Categoría: tomar solo los 2 primeros segmentos del breadcrumb
    # "Hogar > Muebles > La Habana > Diez de Octubre" → ["Hogar", "Muebles"]
    m = re.search(r'\|\s*\*\*Categoría\*\*\s*\|\s*([^\|]+)\s*\|', contenido)
    if m:
        segs = [s.strip() for s in m.group(1).split(">")]
        datos["categoria"] = segs[:2]

    # Descripción: limpiar líneas de fotos que el scraper pone cuando estaba vacía
    # Ojo con \n+ que puede comerse el \n de la cabecera ## Fotos si está vacío
    m = re.search(r'##\s+Descripci[oó]n(.*?)(?=\n#|\Z)', contenido, re.DOTALL)
    if m:
        # Extraemos y limpiamos
        raw_desc = m.group(1).strip()
        # Fallback de limpieza extra por si acaso capturó la sección de fotos
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
    """Rutas absolutas ordenadas de foto_*.{jpg,png,webp} en la carpeta (máx 10)."""
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


# ── Fotos ─────────────────────────────────────────────────────────────────────

async def fotos_en_formulario(page):
    """
    Cuenta cuántas fotos han cargado en el formulario.
    Revolico muestra thumbnails (imgs con blob: o elementos del área de fotos).
    """
    for sel in [
        'img[src^="blob:"]',
        'img[src^="data:image"]',
        '[class*="preview"] img',
        '[class*="thumb"] img',
        '[class*="uploaded"] img',
        '[class*="photo"] img:not([alt="logo"])',
    ]:
        try:
            items = await page.query_selector_all(sel)
            if items:
                return len(items)
        except Exception:
            pass
    return 0


async def limpiar_fotos(page):
    """Elimina las fotos del formulario para un reintento limpio."""
    for sel in [
        'button[aria-label*="liminar"]',
        'button[aria-label*="emove"]',
        'button[aria-label*="lose"]',
        '[class*="photo"] button',
        '[class*="preview"] button',
        '[class*="delete"]',
        '[class*="remove"]',
    ]:
        try:
            btns = await page.query_selector_all(sel)
            for btn in btns:
                await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(0.4)
            if btns:
                await asyncio.sleep(1)
                return
        except Exception:
            pass


async def subir_fotos(page, rutas_fotos):
    """
    Sube fotos con hasta MAX_REINTENTOS_FOTOS intentos.
    Si se agotan los reintentos, continúa publicando sin fotos (no bloquea).
    Devuelve el número de fotos que cargaron.
    """
    if not rutas_fotos:
        return 0

    for intento in range(1, MAX_REINTENTOS_FOTOS + 1):
        print(f"    📸 Fotos — intento {intento}/{MAX_REINTENTOS_FOTOS}")
        try:
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                print(f"    ❌ No se encontró input[type=file]")
                break

            await file_input.set_input_files(rutas_fotos)
            print(f"    ⏳ Esperando {ESPERA_CARGA_FOTOS}s...")
            await asyncio.sleep(ESPERA_CARGA_FOTOS)

            n = await fotos_en_formulario(page)
            print(f"    🖼️  {n}/{len(rutas_fotos)} fotos cargadas")

            if n > 0:
                return n

            # No cargó nada — limpiar y reintentar si quedan intentos
            if intento < MAX_REINTENTOS_FOTOS:
                print(f"    ⚠️  Ninguna foto cargó. Limpiando y reintentando...")
                await limpiar_fotos(page)
                await asyncio.sleep(3)
            else:
                print(f"    ❌ Reintentos agotados — se publicará sin fotos")

        except Exception as e:
            print(f"    ❌ Error subiendo fotos: {e}")
            if intento < MAX_REINTENTOS_FOTOS:
                await asyncio.sleep(3)
            else:
                print(f"    ❌ Reintentos agotados — se publicará sin fotos")

    return 0


# ── Helpers de formulario ─────────────────────────────────────────────────────

async def fill(page, selector, valor):
    try:
        el = await page.query_selector(selector)
        if el:
            await el.click()
            await asyncio.sleep(0.2)
            await el.fill(str(valor))
            return True
    except Exception:
        pass
    return False


async def seleccionar_moneda(page, moneda):
    """select[name='currency'] tiene opciones CUP / USD / MLC."""
    for metodo in [
        lambda: page.select_option('select[name="currency"]', label=moneda),
        lambda: page.select_option('select[name="currency"]', value=moneda.upper()),
    ]:
        try:
            await metodo()
            return True
        except Exception:
            pass
    return False


async def seleccionar_categoria(page, segmentos):
    """
    Selecciona la categoría en el modal de Revolico.

    El modal tiene DOS secciones:
      1. "Categoría sugerida" — Revolico infiere la categoría del título
         y muestra un botón "Aceptar". Si la sugerencia coincide con lo
         que queremos, simplemente la aceptamos.
      2. "Todas las categorías" — lista scrolleable donde las subcategorías
         aparecen DIRECTAMENTE (ej: "Muebles" aparece solo, sin necesidad
         de hacer clic en "Hogar" primero). Solo hay que hacer clic en
         el nombre de la subcategoría.

    segmentos = ["Hogar", "Muebles"]  →  buscar "Muebles" en la lista
    """
    if not segmentos:
        return False

    # La subcategoría es el último segmento: "Muebles"
    subcategoria = segmentos[-1]

    # ── Abrir modal ────────────────────────────────────────────────────────────
    for sel in ['[data-testid*="category"]', 'button:has-text("Elige una categoría")']:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(2)
                break
        except Exception:
            pass

    # ── Opción 1: usar la categoría SUGERIDA si coincide ──────────────────────
    # El modal muestra "Categoría sugerida: Muebles / Hogar" + botón "Aceptar"
    # Si la sugerencia contiene nuestra subcategoría, aceptamos directamente.
    try:
        texto_modal = await page.evaluate("""
            () => {
                const modal = document.querySelector(
                    '[role="dialog"], [class*="modal"], [class*="Modal"]'
                );
                return modal ? modal.innerText : document.body.innerText;
            }
        """)
        sugerencia_ok = subcategoria.lower() in texto_modal.lower()

        if sugerencia_ok:
            # Buscar y pulsar el botón "Aceptar" de la sugerencia
            aceptar = await page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const btn = btns.find(b => b.innerText.trim() === 'Aceptar');
                    if (btn) { btn.click(); return true; }
                    return false;
                }
            """)
            if aceptar:
                print(f"      ✅ Categoría sugerida aceptada: {subcategoria}")
                await asyncio.sleep(1.5)
                return True
    except Exception:
        pass

    # ── Opción 2: clic directo en la subcategoría de la lista ─────────────────
    # Las subcategorías aparecen directamente en "Todas las categorías",
    # sin necesidad de expandir la categoría padre.
    print(f"      → Buscando '{subcategoria}' en la lista...")

    # Intentar primero clic exacto por texto
    try:
        encontrado = await page.evaluate(f"""
            () => {{
                const todos = Array.from(document.querySelectorAll(
                    'li, [role="option"], [role="listitem"], a, span, p'
                ));
                const el = todos.find(e => e.innerText.trim() === '{subcategoria}');
                if (el) {{ e.click(); return true; }}
                return false;
            }}
        """)
        if encontrado:
            await asyncio.sleep(1.5)
            print(f"      ✅ '{subcategoria}' seleccionado (texto exacto)")
            return True
    except Exception:
        pass

    # Fallback: has-text de Playwright (coincidencia parcial)
    for sel in [
        f'li:has-text("{subcategoria}")',
        f'[role="option"]:has-text("{subcategoria}")',
        f'[role="listitem"]:has-text("{subcategoria}")',
        f'a:has-text("{subcategoria}")',
    ]:
        try:
            els = await page.query_selector_all(sel)
            # Tomar el que tenga el texto MÁS CORTO (el más específico)
            if els:
                textos = [(await e.inner_text(), e) for e in els]
                textos.sort(key=lambda x: len(x[0]))
                await page.evaluate("el => el.click()", textos[0][1])
                await asyncio.sleep(1.5)
                print(f"      ✅ '{subcategoria}' seleccionado (has-text)")
                return True
        except Exception:
            pass

    # No se encontró la subcategoría exacta — aceptar lo que la IA sugiera
    print(f"      ⚠️  '{subcategoria}' no encontrado — aceptando sugerencia de la IA")
    try:
        aceptado = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText.trim() === 'Aceptar');
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)
        if aceptado:
            await asyncio.sleep(1.5)
            print(f"      ✅ Sugerencia de la IA aceptada")
            return True
    except Exception:
        pass

    # Si ni siquiera hay sugerencia, cerrar con Escape y continuar
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)
    return False


# ── Publicar un anuncio completo ──────────────────────────────────────────────

async def publicar_anuncio(page, item_id, datos, rutas_fotos, preview=False):
    titulo      = datos["titulo"]
    precio      = datos["precio"]
    moneda      = datos["moneda"]
    descripcion = datos["descripcion"]
    categoria   = datos["categoria"]

    print(f"  📝 {titulo}")
    print(f"  💰 {precio} {moneda}  |  📁 {' > '.join(categoria)}  |  📸 {len(rutas_fotos)} fotos")

    if preview:
        return "PREVIEW"

    # 1. Abrir formulario
    await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded")
    await asyncio.sleep(4)

    # 2. Fotos
    await subir_fotos(page, rutas_fotos)

    # 3. Título
    ok = await fill(page, 'input[name="title"]', titulo[:120])
    print(f"    {'✅' if ok else '⚠️ '} Título")

    # 4. Precio
    ok = await fill(page, 'input[name="price"]', precio)
    print(f"    {'✅' if ok else '⚠️ '} Precio")

    # 5. Moneda (solo si no es USD, que es el default del form)
    if moneda != "USD":
        ok = await seleccionar_moneda(page, moneda)
        print(f"    {'✅' if ok else '⚠️ '} Moneda → {moneda}")

    # 6. Descripción
    ok = await fill(page, 'textarea[name="description"]', descripcion[:1000])
    print(f"    {'✅' if ok else '⚠️ '} Descripción")

    # 7. Categoría
    if categoria:
        ok = await seleccionar_categoria(page, categoria)
        print(f"    {'✅' if ok else '⚠️ '} Categoría: {' > '.join(categoria)}")
        await asyncio.sleep(1)

    # 8. Publicar
    url_antes = page.url
    try:
        btn = await page.query_selector('button[type="submit"]')
        if btn:
            await page.evaluate("el => el.click()", btn)
    except Exception as e:
        print(f"    ❌ Error al pulsar Publicar: {e}")
        return None

    print(f"    ⏳ Esperando confirmación...")
    try:
        await page.wait_for_url(
            lambda url: url != url_antes and "publish" not in url,
            timeout=20000
        )
    except Exception:
        pass

    nueva_url = page.url
    if nueva_url and "item" in nueva_url and "publish" not in nueva_url:
        print(f"    ✅ Publicado → {nueva_url}")
        return nueva_url

    # Buscar errores de validación
    texto = await page.evaluate("() => document.body.innerText")
    errores = [l.strip() for l in texto.split("\n") if l.strip() and
               any(k in l.lower() for k in ["error", "requerido", "obligatorio", "inválido", "falló"])]
    if errores:
        print(f"    ❌ Errores detectados:")
        for e in errores[:5]:
            print(f"       → {e}")
    else:
        print(f"    ❌ No se confirmó la publicación. URL actual: {nueva_url}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    preview  = "--preview" in sys.argv
    ids_unicos = []
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        for arg in sys.argv[idx+1:]:
            if arg.startswith("--"): break
            ids_unicos.append(arg)

    if preview:
        print("👁️  MODO PREVIEW — no se publicará nada\n")

    if not os.path.isdir(CARPETA_ANUNCIOS):
        print(f"❌ No existe la carpeta '{CARPETA_ANUNCIOS}/'")
        print(f"   Ejecuta primero descargar_anuncios.py")
        return

    todos_ids = sorted(
        d for d in os.listdir(CARPETA_ANUNCIOS)
        if d.isdigit()
        and os.path.isdir(os.path.join(CARPETA_ANUNCIOS, d))
        and os.path.exists(os.path.join(CARPETA_ANUNCIOS, d, "datos.md"))
    )

    if ids_unicos:
        todos_ids = [i for i in todos_ids if i in ids_unicos]
        if not todos_ids:
            print(f"❌ No se encontró ninguno de los IDs solicitados en '{CARPETA_ANUNCIOS}/'")
            return

    async with async_playwright() as p:
        print("🔌 Conectando a Chrome para detectar cuenta...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        email = await obtener_email_cuenta(context)
        if email:
            archivo_registro = f"publicados_en_{email}.json"
            print(f"👤 Cuenta detectada: {email}")
        else:
            archivo_registro = "publicados_en_cuenta_nueva.json"
            print("⚠️ No se pudo extraer el email. Usando registro por defecto.")

        publicados = cargar_publicados(archivo_registro)

        if ids_unicos:
            # Forzar publicación aunque esté en publicados
            pendientes = todos_ids
            print("⚠️ Modo forzado por --id: ignorando historial de publicados")
        else:
            pendientes = [i for i in todos_ids if i not in publicados]

        print(f"📂 Anuncios en carpeta  : {len(todos_ids)}")
        print(f"✅ Ya publicados        : {len(publicados)}")
        print(f"📤 Pendientes           : {len(pendientes)}")

        if not pendientes:
            print(f"\n✨ Todos los anuncios ya están publicados.")
            print(f"   Registro: {archivo_registro}")
            return

        print(f"\n{'='*65}\n")

        ok_count = 0
        fail_ids = []

        for i, item_id in enumerate(pendientes):
            carpeta = os.path.join(CARPETA_ANUNCIOS, item_id)

            print(f"{'─'*65}")
            print(f"[{i+1}/{len(pendientes)}] ID original: {item_id}")

            try:
                datos = parsear_datos_md(os.path.join(carpeta, "datos.md"))
            except Exception as e:
                print(f"  ❌ Error leyendo datos.md: {e}")
                fail_ids.append(item_id)
                continue

            rutas_fotos = listar_fotos(carpeta)

            try:
                nueva_url = await publicar_anuncio(
                    page, item_id, datos, rutas_fotos, preview=preview
                )
            except Exception as e:
                print(f"  ❌ Excepción: {e}")
                nueva_url = None

            if nueva_url:
                if not preview:
                    marcar_publicado(publicados, item_id, nueva_url, archivo_registro)
                ok_count += 1
            else:
                fail_ids.append(item_id)

            if not preview and i < len(pendientes) - 1:
                print(f"\n  ⏳ Pausa {PAUSA_ENTRE_ANUNCIOS}s...")
                await asyncio.sleep(PAUSA_ENTRE_ANUNCIOS)

    print(f"\n{'='*65}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*65}")
    if preview:
        print(f"  👁️  Preview — {ok_count} anuncios listos para publicar")
    else:
        print(f"  ✅ Publicados    : {ok_count}")
        print(f"  ❌ Fallidos      : {len(fail_ids)}")
        if fail_ids:
            print(f"     IDs: {', '.join(fail_ids)}")
        print(f"  📋 Registro en   : {archivo_registro}")
    print(f"{'='*65}")
    print("\n✅ ¡Listo!")


if __name__ == "__main__":
    asyncio.run(main())
