"""
publicar_v2.py — Publicador Mejorado con Sistema de Estado
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Basado en publicar_anuncios_precio_original-fast.py pero integrado
con el sistema de estado de preparar_cuentas.py.

Mejoras sobre el original:
  1. Lee qué publicar desde estado/cuentas/<email>.json
  2. Usa las imágenes ya mutadas (no necesita hashbust en tiempo real)
  3. Publica TODAS las fotos del set (multi-foto)
  4. Marca como publicado/fallido en el estado
  5. Pausas más largas y aleatorias (anti-detección)
  6. Movimiento de mouse orgánico antes de clics
  7. Pausa inteligente ante Cloudflare (no mata el script)
  8. Ráfagas: publica N anuncios y descansa

Uso:
  # Publicar los pendientes de una cuenta
  python3 publicar_v2.py --email tucuenta@gmail.com

  # Preview (no publica, solo muestra qué haría)
  python3 publicar_v2.py --email tucuenta@gmail.com --preview

  # Limitar cantidad de anuncios por sesión
  python3 publicar_v2.py --email tucuenta@gmail.com --limite 5

  # Usar un puerto de Chrome distinto
  python3 publicar_v2.py --email tucuenta@gmail.com --port 9223

  # Publicar con ráfagas (5 anuncios, descansa 30 min, repite)
  python3 publicar_v2.py --email tucuenta@gmail.com --rafaga 5 --descanso 30
"""

import asyncio
import os
import sys
import json
import random
import re
import base64
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import argparse

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
PRODUCTOS_DIR = BASE_DIR / "productos"
ESTADO_DIR = BASE_DIR / "estado"
CUENTAS_DIR = ESTADO_DIR / "cuentas"

# Pausas anti-detección (en segundos)
PAUSA_ENTRE_ANUNCIOS = (3.0, 10.0)    # Más lento que el original (era 10-18)
PAUSA_CARGA_PAGINA = (4.0, 7.0)        # Espera tras goto
PAUSA_CARGA_FOTOS = 8                  # Espera a que suban las fotos
MAX_REINTENTOS_FOTOS = 3
PAUSA_CLOUDFLARE = (120, 300)           # 2-5 min si detecta Cloudflare

# Ráfagas
ANUNCIOS_POR_RAFAGA = 100
DESCANSO_RAFAGA_MINUTOS = 1


# ══════════════════════════════════════════════════════════════════════════════
# ── UTILIDADES DE ESTADO
# ══════════════════════════════════════════════════════════════════════════════

def cargar_json(ruta, default=None):
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def guardar_json(ruta, datos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cargar_cuenta(email):
    ruta = CUENTAS_DIR / f"{email}.json"
    return cargar_json(str(ruta))


def guardar_cuenta(email, datos):
    ruta = CUENTAS_DIR / f"{email}.json"
    guardar_json(str(ruta), datos)


def obtener_pendientes(cuenta):
    """Devuelve solo las publicaciones pendientes."""
    return [p for p in cuenta.get("publicaciones", []) if p.get("estado") == "pendiente"]


def marcar_publicacion(cuenta, producto, estado, url_revolico=None):
    """Marca una publicación como publicada o fallida."""
    for pub in cuenta.get("publicaciones", []):
        if pub["producto"] == producto and pub.get("estado") == "pendiente":
            pub["estado"] = estado
            pub["url_revolico"] = url_revolico
            pub["fecha_publicacion"] = datetime.now().isoformat()
            break
    return cuenta


def resolver_rutas_imagenes(producto, imagenes_usadas):
    """Convierte las rutas relativas de imágenes a rutas absolutas."""
    carpeta_imgs = PRODUCTOS_DIR / producto / "imagenes"
    rutas = []
    for img in imagenes_usadas:
        ruta = carpeta_imgs / img
        if ruta.exists():
            rutas.append(str(ruta.resolve()))
        else:
            print(f"    ⚠️  Imagen no encontrada: {ruta}")
    return rutas


def cargar_descripcion(producto, desc_archivo):
    """Carga el contenido de una variante de descripción."""
    # Primero buscar en descripciones/
    ruta = PRODUCTOS_DIR / producto / "descripciones" / desc_archivo
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()

    # Si es descripcion_base.txt, buscar en la raíz del producto
    ruta = PRODUCTOS_DIR / producto / desc_archivo
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""


def cargar_producto(producto):
    """Carga los datos del producto."""
    ruta = PRODUCTOS_DIR / producto / "producto.json"
    return cargar_json(str(ruta))


# ══════════════════════════════════════════════════════════════════════════════
# ── ANTI-DETECCIÓN
# ══════════════════════════════════════════════════════════════════════════════

async def limpiar_huellas(page):
    """Elimina rastros de automatización del navegador."""
    try:
        await page.evaluate("""
            // Eliminar navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Eliminar la propiedad que Playwright inyecta
            delete window.__playwright;
            delete window.__pw_manual;
        """)
    except Exception:
        pass


async def mover_mouse_organico(page, x, y):
    """Mueve el mouse de forma orgánica hacia un punto."""
    try:
        # Posición actual aleatoria (simula que el mouse ya estaba en algún lado)
        start_x = random.randint(100, 800)
        start_y = random.randint(100, 500)
        steps = random.randint(5, 12)

        for i in range(steps):
            progress = (i + 1) / steps
            # Movimiento con curva + ruido
            cx = start_x + (x - start_x) * progress + random.uniform(-5, 5)
            cy = start_y + (y - start_y) * progress + random.uniform(-5, 5)
            await page.mouse.move(cx, cy)
            await asyncio.sleep(random.uniform(0.01, 0.04))
    except Exception:
        pass


async def pausa_humana(minima=0.5, maxima=2.0):
    """Pausa aleatoria que simula tiempo humano de reacción."""
    await asyncio.sleep(random.uniform(minima, maxima))


# ══════════════════════════════════════════════════════════════════════════════
# ── DETECCIÓN DE CLOUDFLARE
# ══════════════════════════════════════════════════════════════════════════════

async def detectar_cloudflare(page):
    """Detecta si Cloudflare está pidiendo verificación. Retorna True si detectado."""
    try:
        titulo = await page.title()
        if "Just a moment" in titulo or "Un momento" in titulo:
            return True

        cf_elements = await page.query_selector_all(
            '#challenge-running, iframe[src*="cloudflare"], #challenge-form'
        )
        if cf_elements:
            return True
    except Exception:
        pass
    return False


async def manejar_cloudflare(page, intentos_restantes):
    """
    Maneja un challenge de Cloudflare.
    En vez de matar el script, PAUSA y espera.
    Retorna True si se resolvió, False si hay que abortar.
    """
    pausa = random.uniform(PAUSA_CLOUDFLARE[0], PAUSA_CLOUDFLARE[1])
    print(f"\n    🚨 CLOUDFLARE DETECTADO")
    print(f"    ⏸️  Pausando {pausa/60:.1f} minutos...")
    print(f"    💡 Si puedes, ve a Chrome y resuelve el captcha manualmente.")
    print(f"    📊 Intentos restantes después de esta pausa: {intentos_restantes}\n")

    await asyncio.sleep(pausa)

    # Intentar navegar de nuevo
    try:
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        if await detectar_cloudflare(page):
            print("    🔴 Cloudflare sigue activo después de la pausa.")
            return False
        else:
            print("    ✅ Cloudflare resuelto. Continuando...")
            return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ── IDENTIFICACIÓN DE CUENTA
# ══════════════════════════════════════════════════════════════════════════════

async def obtener_email_cuenta(context):
    """Obtiene el email de la sesión activa en Revolico."""
    cookies = await context.cookies("https://www.revolico.com")
    for c in cookies:
        if c['name'] == 'st-access-token':
            try:
                parts = c['value'].split('.')
                payload = parts[1] + '=' * (-len(parts[1]) % 4)
                data = json.loads(base64.b64decode(payload).decode('utf-8'))
                return data.get("user_email") or data.get("user_name")
            except Exception:
                pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ── INTERACCIÓN CON EL FORMULARIO
# ══════════════════════════════════════════════════════════════════════════════

async def fill(page, selector, valor):
    """Llena un campo del formulario de forma natural."""
    try:
        el = await page.query_selector(selector)
        if el:
            # Mover mouse al elemento antes de interactuar
            box = await el.bounding_box()
            if box:
                await mover_mouse_organico(page, box["x"] + box["width"]/2,
                                           box["y"] + box["height"]/2)
            await el.click()
            await pausa_humana(0.2, 0.5)
            await el.fill(str(valor))
            await pausa_humana(0.3, 0.8)
            return True
    except Exception:
        pass
    return False


async def seleccionar_moneda(page, moneda):
    """Selecciona la moneda en el formulario."""
    for metodo in [
        lambda: page.select_option('select[name="currency"]', label=moneda),
        lambda: page.select_option('select[name="currency"]', value=moneda.upper()),
    ]:
        try:
            await metodo()
            await pausa_humana(0.3, 0.6)
            return True
        except Exception:
            pass
    return False


async def seleccionar_categoria(page, segmentos):
    """Selecciona la categoría en el formulario."""
    if not segmentos:
        return False
    subcategoria = segmentos[-1]

    for sel in ['[data-testid*="category"]', 'button:has-text("Elige una categoría")']:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(2)
                break
        except Exception:
            pass

    # Intentar con Aceptar si la categoría ya está seleccionada
    try:
        texto_modal = await page.evaluate("() => document.body.innerText")
        if subcategoria.lower() in texto_modal.lower():
            aceptar = await page.evaluate(
                "() => { const btns = Array.from(document.querySelectorAll('button')); "
                "const btn = btns.find(b => b.innerText.trim() === 'Aceptar'); "
                "if (btn) { btn.click(); return true; } return false; }"
            )
            if aceptar:
                await asyncio.sleep(1.5)
                return True
    except Exception:
        pass

    # Buscar la subcategoría por texto
    try:
        encontrado = await page.evaluate(
            f"() => {{ const todos = Array.from(document.querySelectorAll("
            f"'li, [role=\"option\"], [role=\"listitem\"], a, span, p')); "
            f"const el = todos.find(e => e.innerText.trim() === '{subcategoria}'); "
            f"if (el) {{ el.click(); return true; }} return false; }}"
        )
        if encontrado:
            await asyncio.sleep(1.5)
            return True
    except Exception:
        pass

    # Fallback con selectores de Playwright
    for sel in [
        f'li:has-text("{subcategoria}")',
        f'[role="option"]:has-text("{subcategoria}")',
        f'[role="listitem"]:has-text("{subcategoria}")',
        f'a:has-text("{subcategoria}")',
    ]:
        try:
            els = await page.query_selector_all(sel)
            if els:
                textos = [(await e.inner_text(), e) for e in els]
                textos.sort(key=lambda x: len(x[0]))
                await page.evaluate("el => el.click()", textos[0][1])
                await asyncio.sleep(1.5)
                return True
        except Exception:
            pass

    await page.keyboard.press("Escape")
    return False


async def fotos_en_formulario(page):
    """Cuenta las fotos ya subidas en el formulario."""
    for sel in [
        'img[src^="blob:"]', 'img[src^="data:image"]',
        '[class*="preview"] img', '[class*="thumb"] img',
        '[class*="uploaded"] img', '[class*="photo"] img:not([alt="logo"])',
    ]:
        try:
            items = await page.query_selector_all(sel)
            if items:
                return len(items)
        except Exception:
            pass
    return 0


async def limpiar_fotos(page):
    """Limpia las fotos del formulario."""
    for sel in [
        'button[aria-label*="liminar"]', 'button[aria-label*="emove"]',
        'button[aria-label*="lose"]', '[class*="photo"] button',
        '[class*="preview"] button', '[class*="delete"]', '[class*="remove"]',
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
    """Sube las fotos al formulario. Las imágenes ya vienen mutadas."""
    if not rutas_fotos:
        return 0

    for intento in range(1, MAX_REINTENTOS_FOTOS + 1):
        print(f"    📸 Subiendo {len(rutas_fotos)} foto(s) — intento {intento}/{MAX_REINTENTOS_FOTOS}")
        try:
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                break
            await file_input.set_input_files(rutas_fotos)
            await asyncio.sleep(PAUSA_CARGA_FOTOS)
            n = await fotos_en_formulario(page)
            if n > 0:
                print(f"    ✅ {n} foto(s) subidas correctamente")
                return n
            if intento < MAX_REINTENTOS_FOTOS:
                await limpiar_fotos(page)
                await asyncio.sleep(3)
        except Exception as e:
            print(f"    ⚠️  Error subiendo fotos: {e}")
            if intento < MAX_REINTENTOS_FOTOS:
                await asyncio.sleep(3)
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# ── LÓGICA CENTRAL DE PUBLICACIÓN
# ══════════════════════════════════════════════════════════════════════════════

async def publicar_anuncio(page, datos_producto, descripcion, rutas_fotos, preview=False):
    """Publica un anuncio individual en Revolico."""
    titulo = datos_producto.get("nombre", "Sin título")
    precio = datos_producto.get("precio", "")
    moneda = datos_producto.get("moneda", "USD")
    categoria = datos_producto.get("categoria", [])

    print(f"  📝 {titulo} ({precio} {moneda}) — {len(rutas_fotos)} foto(s)")

    if preview:
        return "PREVIEW"

    # Navegar al formulario de publicar
    await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded")
    espera = random.uniform(PAUSA_CARGA_PAGINA[0], PAUSA_CARGA_PAGINA[1])
    await asyncio.sleep(espera)

    # Verificar Cloudflare
    if await detectar_cloudflare(page):
        resuelto = await manejar_cloudflare(page, 2)
        if not resuelto:
            return None
        # Re-navegar al formulario
        await page.goto("https://www.revolico.com/item/publish", wait_until="domcontentloaded")
        await asyncio.sleep(espera)

    # Limpiar huellas de automatización
    await limpiar_huellas(page)

    # Mover mouse aleatoriamente (simular presencia humana)
    await mover_mouse_organico(page, random.randint(200, 600), random.randint(200, 400))
    await pausa_humana(0.5, 1.5)

    # Subir fotos
    await subir_fotos(page, rutas_fotos)
    await pausa_humana(0.5, 1.0)

    # Llenar campos
    await fill(page, 'input[name="title"]', titulo[:120])
    await fill(page, 'input[name="price"]', precio)
    if moneda != "USD":
        await seleccionar_moneda(page, moneda)
    await fill(page, 'textarea[name="description"]', descripcion[:1000])

    if categoria:
        await seleccionar_categoria(page, categoria)

    await pausa_humana(1.0, 2.0)

    # Hacer clic en publicar
    url_antes = page.url
    try:
        btn = await page.query_selector('button[type="submit"]')
        if btn:
            box = await btn.bounding_box()
            if box:
                await mover_mouse_organico(page, box["x"] + box["width"]/2,
                                           box["y"] + box["height"]/2)
            await page.evaluate("el => el.click()", btn)
    except Exception:
        pass

    print(f"    ⏳ Esperando confirmación...")
    try:
        await page.wait_for_url(
            lambda url: url != url_antes and "publish" not in url,
            timeout=25000
        )
    except Exception:
        pass

    nueva_url = page.url
    if nueva_url and "item" in nueva_url and "publish" not in nueva_url:
        print(f"    ✅ Publicado → {nueva_url}")
        return nueva_url

    # Verificar si Cloudflare intervino
    if await detectar_cloudflare(page):
        print(f"    🚨 Cloudflare intervino durante la publicación")
        return None

    print(f"    ❌ No se pudo confirmar la publicación")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Publicador v2 — Integrado con sistema de estado",
    )
    parser.add_argument("--email", "-e", required=True, help="Email de la cuenta a publicar")
    parser.add_argument("--preview", action="store_true", help="Solo mostrar, no publicar")
    parser.add_argument("--limite", "-l", type=int, default=0, help="Máximo de anuncios (0=todos)")
    parser.add_argument("--orden", choices=["aleatorio", "alfabetico"], default="aleatorio",
                       help="Orden de publicación de los pendientes (default: aleatorio)")
    parser.add_argument("--port", "-p", type=int, default=9222, help="Puerto de Chrome debug")
    parser.add_argument("--rafaga", type=int, default=ANUNCIOS_POR_RAFAGA,
                       help=f"Anuncios por ráfaga (default: {ANUNCIOS_POR_RAFAGA})")
    parser.add_argument("--descanso", type=int, default=DESCANSO_RAFAGA_MINUTOS,
                       help=f"Minutos de descanso entre ráfagas (default: {DESCANSO_RAFAGA_MINUTOS})")

    args = parser.parse_args()

    # Verificar que la cuenta existe en el sistema
    ruta_cuenta = CUENTAS_DIR / f"{args.email}.json"
    if not ruta_cuenta.exists():
        print(f"❌ No existe la cuenta {args.email} en el sistema.")
        print(f"   Usa: python3 scripts-gemini/preparar_cuentas.py asignar --email {args.email}")
        return

    cuenta = cargar_cuenta(args.email)
    pendientes = obtener_pendientes(cuenta)

    if not pendientes:
        print(f"✅ No hay productos pendientes para {args.email}")
        return

    # Ordenar o barajar pendientes
    if args.orden == "aleatorio":
        random.shuffle(pendientes)
    elif args.orden == "alfabetico":
        pendientes.sort(key=lambda p: p["producto"].lower())

    if args.limite > 0:
        pendientes = pendientes[:args.limite]

    print(f"\n{'═' * 65}")
    print(f"  🚀 PUBLICADOR v2 — {args.email}")
    print(f"  ({cuenta.get('alias', '?')})")
    print(f"{'═' * 65}")
    print(f"  Pendientes a procesar: {len(pendientes)}")
    print(f"  Orden:                 {args.orden.upper()}")
    print(f"  Ráfaga:                {args.rafaga} anuncios, descanso {args.descanso} min")
    print(f"  Puerto Chrome:         {args.port}")
    print(f"  Modo:                  {'PREVIEW (sin publicar)' if args.preview else 'PUBLICACIÓN REAL'}")
    print(f"{'═' * 65}\n")

    if not args.preview:
        # Conectar a Chrome
        async with async_playwright() as p:
            print(f"🔌 Conectando a Chrome en puerto {args.port}...")
            try:
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            except Exception as e:
                print(f"❌ No se pudo conectar a Chrome: {e}")
                print(f"   Asegúrate de abrir Chrome con: google-chrome --remote-debugging-port={args.port}")
                return

            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()

            # Verificar sesión
            email_real = await obtener_email_cuenta(context)
            if email_real:
                print(f"📧 Sesión activa: {email_real}")
                if email_real != args.email:
                    print(f"⚠️  ADVERTENCIA: La sesión es de {email_real} pero se va a publicar para {args.email}")
                    print(f"   Si esto no es correcto, cambia de cuenta en Chrome.")
            else:
                print(f"⚠️  No se pudo detectar la sesión. Asegúrate de estar logueado en Revolico.")

            # Limpiar huellas inicialmente
            await limpiar_huellas(page)

            ok_count = 0
            fail_count = 0
            cloudflare_count = 0

            for i, pub in enumerate(pendientes):
                # Ráfagas
                if i > 0 and i % args.rafaga == 0:
                    descanso = args.descanso * 60 + random.uniform(-60, 60)
                    print(f"\n  💤 DESCANSO DE RÁFAGA: {descanso/60:.1f} minutos")
                    print(f"     Publicados: {ok_count} | Fallidos: {fail_count}")
                    print(f"     Reanudando en {descanso/60:.1f} min...\n")
                    await asyncio.sleep(descanso)

                producto = pub["producto"]
                imagenes = pub.get("imagenes_usadas", [pub.get("imagen_usada", "")])
                desc_archivo = pub.get("descripcion_usada", "descripcion_base.txt")

                print(f"{'─' * 65}")
                print(f"[{i+1}/{len(pendientes)}] {producto}")

                # Cargar datos
                datos_producto = cargar_producto(producto)
                if not datos_producto:
                    print(f"  ❌ No se encontraron datos del producto")
                    cuenta = marcar_publicacion(cuenta, producto, "fallido")
                    guardar_cuenta(args.email, cuenta)
                    fail_count += 1
                    continue

                # Resolver rutas de imágenes
                rutas_fotos = resolver_rutas_imagenes(producto, imagenes)
                if not rutas_fotos:
                    print(f"  ❌ No se encontraron imágenes")
                    cuenta = marcar_publicacion(cuenta, producto, "fallido")
                    guardar_cuenta(args.email, cuenta)
                    fail_count += 1
                    continue

                # Cargar descripción
                descripcion = cargar_descripcion(producto, desc_archivo)

                # Publicar
                try:
                    nueva_url = await publicar_anuncio(page, datos_producto, descripcion, rutas_fotos)
                except Exception as e:
                    print(f"  ❌ Excepción: {e}")
                    nueva_url = None

                if nueva_url:
                    cuenta = marcar_publicacion(cuenta, producto, "publicado", nueva_url)
                    ok_count += 1
                else:
                    cuenta = marcar_publicacion(cuenta, producto, "fallido")
                    fail_count += 1

                    # Si fue Cloudflare, verificar si debemos parar
                    if await detectar_cloudflare(page):
                        cloudflare_count += 1
                        if cloudflare_count >= 3:
                            print(f"\n  🛑 3 Cloudflares seguidos. Deteniendo para proteger la cuenta.")
                            guardar_cuenta(args.email, cuenta)
                            break
                        resuelto = await manejar_cloudflare(page, len(pendientes) - i - 1)
                        if not resuelto:
                            print(f"\n  🛑 Cloudflare no se resolvió. Deteniendo.")
                            guardar_cuenta(args.email, cuenta)
                            break
                    else:
                        cloudflare_count = 0  # Reset si no es Cloudflare

                # Guardar estado después de cada publicación
                guardar_cuenta(args.email, cuenta)

                # Pausa entre anuncios
                if i < len(pendientes) - 1:
                    espera = random.uniform(PAUSA_ENTRE_ANUNCIOS[0], PAUSA_ENTRE_ANUNCIOS[1])
                    print(f"\n  ⏳ Pausa: {espera:.0f}s")
                    await asyncio.sleep(espera)

    else:
        # Modo preview
        ok_count = 0
        fail_count = 0
        for i, pub in enumerate(pendientes):
            producto = pub["producto"]
            imagenes = pub.get("imagenes_usadas", [])
            desc_archivo = pub.get("descripcion_usada", "?")
            datos = cargar_producto(producto)
            nombre = datos.get("nombre", producto) if datos else producto
            precio = datos.get("precio", "?") if datos else "?"
            moneda = datos.get("moneda", "") if datos else ""

            print(f"  [{i+1:3d}] {nombre:40s} {precio} {moneda}")
            print(f"        🖼️ {len(imagenes)} foto(s)  📝 {desc_archivo}")
            ok_count += 1

        fail_count = 0

    # Resumen final
    print(f"\n{'═' * 65}")
    print(f"  📊 RESUMEN FINAL")
    print(f"{'═' * 65}")
    print(f"  ✅ Publicados: {ok_count}")
    print(f"  ❌ Fallidos:   {fail_count}")
    total_pendientes = len(obtener_pendientes(cargar_cuenta(args.email)))
    print(f"  📋 Pendientes: {total_pendientes}")
    print(f"{'═' * 65}\n")


if __name__ == "__main__":
    asyncio.run(main())
