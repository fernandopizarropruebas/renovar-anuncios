#!/usr/bin/env python3
"""
eliminar_anuncios.py — Elimina anuncios publicados de una cuenta de Revolico

Solo elimina los anuncios que están marcados como "publicado" en el sistema
de estado (estado/cuentas/{email}.json). NO elimina anuncios publicados
manualmente u otros que no estén en el sistema.

Flujo:
    1. Lee estado/cuentas/{email}.json
    2. Filtra los que tienen estado "publicado"
    3. Extrae el ID de la url_revolico
    4. Navega a /item/{ID}/_/manage
    5. Hace clic en "Eliminar"
    6. Maneja los modales de confirmación (pueden ser 1 o 2)
    7. Verifica que se eliminó
    8. Actualiza el estado a "eliminado"

Uso:
    python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com
    python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com --preview
    python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com --limite 5
"""

import asyncio
import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# ══════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
ESTADO_DIR = BASE_DIR / "estado"
CUENTAS_DIR = ESTADO_DIR / "cuentas"

# Pausas (segundos)
PAUSA_ENTRE_ANUNCIOS = (3.0, 8.0)
PAUSA_CARGA_PAGINA = (4.0, 7.0)
PAUSA_ANTES_CLIC = (0.3, 0.8)
PAUSA_DESPUES_CLIC = (1.0, 2.5)
PAUSA_CLOUDFLARE = (120, 300)

# Ráfagas
DEFAULT_RAFAGA = 500
DEFAULT_DESCANSO_MIN = 30

# Reintentos
MAX_CLOUDFLARES_SEGUIDOS = 3

# URLs
URL_CUENTA = "https://www.revolico.com/account/ads"
URL_GESTIONAR = "https://www.revolico.com/item/{id}/_/manage"


# ══════════════════════════════════════════════════════════
#  UTILIDADES DE ESTADO
# ══════════════════════════════════════════════════════════

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
    datos = cargar_json(str(ruta))
    if not datos:
        print(f"❌ No se encontró el archivo de estado para {email}")
        print(f"   Ruta esperada: {ruta}")
        sys.exit(1)
    return datos


def guardar_cuenta(email, datos):
    ruta = CUENTAS_DIR / f"{email}.json"
    guardar_json(str(ruta), datos)


def obtener_publicados(cuenta):
    """Devuelve las publicaciones con estado 'publicado'."""
    return [p for p in cuenta.get("publicaciones", []) if p.get("estado") == "publicado"]


def extraer_id_de_url(url):
    """Extrae el ID numérico del anuncio de una url_revolico."""
    if not url:
        return None
    # Formatos posibles:
    # https://www.revolico.com/item/57493855/_/manage?action=created
    # https://www.revolico.com/item/slug-57493855
    # https://www.revolico.com/item/57493855/_/manage
    match = re.search(r'/item/(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'-(\d+)', url)
    if match:
        return match.group(1)
    return None


def marcar_como_eliminado(cuenta, producto):
    """Marca una publicación como eliminada en el estado."""
    for pub in cuenta.get("publicaciones", []):
        if pub["producto"] == producto and pub.get("estado") == "publicado":
            pub["estado"] = "eliminado"
            pub["fecha_eliminacion"] = datetime.now().isoformat()
            break
    return cuenta


# ══════════════════════════════════════════════════════════
#  ANTI-DETECCIÓN
# ══════════════════════════════════════════════════════════

async def limpiar_huellas(page):
    try:
        await page.evaluate("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            if (window.__playwright) delete window.__playwright;
            if (window.__pw_manual) delete window.__pw_manual;
        """)
    except Exception:
        pass


async def mover_mouse_organico(page, target_x, target_y):
    current_x = random.randint(100, 800)
    current_y = random.randint(100, 500)
    steps = random.randint(5, 12)

    for i in range(steps):
        progress = (i + 1) / steps
        ease = progress * progress * (3 - 2 * progress)
        x = current_x + (target_x - current_x) * ease + random.uniform(-5, 5)
        y = current_y + (target_y - current_y) * ease + random.uniform(-5, 5)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.04))

    await page.mouse.move(target_x, target_y)


async def clic_organico_en_elemento(page, elemento, descripcion=""):
    """Hace clic orgánico en un elemento de Playwright."""
    box = await elemento.bounding_box()
    if box:
        target_x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
        target_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)
        await asyncio.sleep(random.uniform(*PAUSA_ANTES_CLIC))
        await mover_mouse_organico(page, target_x, target_y)
        await page.mouse.click(target_x, target_y)
    else:
        await page.evaluate("el => el.click()", elemento)
    await asyncio.sleep(random.uniform(*PAUSA_DESPUES_CLIC))


# ══════════════════════════════════════════════════════════
#  DETECCIÓN DE CLOUDFLARE
# ══════════════════════════════════════════════════════════

async def detectar_cloudflare(page):
    try:
        titulo = await page.title()
        if "Just a moment" in titulo or "Un momento" in titulo:
            return True
        cf = await page.query_selector_all('#challenge-running, iframe[src*="cloudflare"], #challenge-form')
        if cf:
            return True
    except Exception:
        pass
    return False


async def manejar_cloudflare(page):
    print("\n    🚨 ¡CLOUDFLARE DETECTADO!")
    print("       Pausando para no levantar sospechas...")
    pausa = random.uniform(*PAUSA_CLOUDFLARE)
    print(f"       ⏳ Esperando {pausa/60:.1f} minutos...")
    await asyncio.sleep(pausa)

    try:
        await page.goto(URL_CUENTA, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 5))
        if not await detectar_cloudflare(page):
            print("       ✅ Cloudflare resuelto.")
            return True
    except Exception:
        pass
    print("       ❌ Cloudflare sigue activo.")
    return False


# ══════════════════════════════════════════════════════════
#  CERRAR POPUP DE DESTACADOS
# ══════════════════════════════════════════════════════════

async def cerrar_popup_destacados(page):
    selectores = [
        'button[aria-label="Close"]',
        'button[aria-label="Cerrar"]',
        '[data-slot="dialog-close"]',
        '[data-slot="dialog-portal"] button:first-child',
        'div[role="dialog"] button[aria-label="Close"]',
        'div[role="dialog"] button[aria-label="Cerrar"]',
    ]

    for sel in selectores:
        try:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await asyncio.sleep(random.uniform(0.5, 1.0))
                await clic_organico_en_elemento(page, btn, "cerrar popup")
                print("    🔒 Popup de Destacados cerrado")
                return True
        except Exception:
            continue

    # Fallback: Escape
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(random.uniform(0.5, 1.0))
        dialog = await page.query_selector('div[role="dialog"]')
        if not dialog or not await dialog.is_visible():
            print("    🔒 Popup cerrado (Escape)")
            return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════
#  ELIMINAR UN ANUNCIO
# ══════════════════════════════════════════════════════════

async def eliminar_anuncio(page, item_id):
    """
    Elimina un anuncio individual.

    Maneja 2 flujos posibles:
    - Flujo corto: Clic Eliminar → Modal "¿Estás seguro?" → Clic Eliminar rojo → Eliminado
    - Flujo largo: Clic Eliminar → Modal "¿Estás seguro?" → Clic Eliminar rojo →
                   Modal "¿A quién le vendiste?" → "Eliminar sin indicar comprador" →
                   Clic Eliminar rojo → Eliminado

    A veces se salta el primer modal y va directo al segundo, o incluso
    se elimina directamente. El script maneja todos los casos.

    Retorna:
        - True: eliminado exitosamente
        - False: falló
        - "cloudflare": se detectó Cloudflare
    """
    # 1. Navegar a la página de gestión
    url = URL_GESTIONAR.format(id=item_id)
    try:
        await page.goto(url, wait_until="domcontentloaded")
    except Exception as e:
        print(f"    ❌ Error navegando: {e}")
        return False

    await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))

    # 2. Verificar Cloudflare
    if await detectar_cloudflare(page):
        return "cloudflare"

    await limpiar_huellas(page)

    # 3. Cerrar popup de Destacados (si aparece)
    await asyncio.sleep(random.uniform(1.0, 2.0))
    await cerrar_popup_destacados(page)

    # 4. Scroll hacia abajo para que la barra de acciones sea visible
    await asyncio.sleep(random.uniform(0.5, 1.0))
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(random.uniform(1.0, 2.0))

    # 5. Buscar el botón "Eliminar" de la barra de acciones inferior
    #    Usamos JavaScript para buscar de forma más robusta
    boton_eliminar = await page.evaluate_handle("""
        () => {
            // Buscar todos los elementos que contengan exactamente "Eliminar"
            const allElements = document.querySelectorAll('button, a, div, span');
            for (const el of allElements) {
                const text = el.textContent.trim();
                // Queremos el de la barra de acciones: dice exactamente "Eliminar"
                // y NO está dentro de un dialog/modal
                if (text === 'Eliminar' && !el.closest('[role="dialog"]') && !el.closest('[data-slot="dialog-portal"]')) {
                    // Verificar que es visible
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        return el;
                    }
                }
            }
            return null;
        }
    """)

    # Verificar que se encontró
    is_null = await boton_eliminar.evaluate("el => el === null")
    if is_null:
        # Fallback: intentar con selectores de Playwright
        print("    🔍 Buscando botón Eliminar con selectores alternativos...")
        for sel in ['button:has-text("Eliminar")', 'a:has-text("Eliminar")', ':has-text("Eliminar")']:
            try:
                elementos = await page.query_selector_all(sel)
                for el in elementos:
                    if await el.is_visible():
                        texto = (await el.inner_text()).strip()
                        if texto == "Eliminar":
                            boton_eliminar = el
                            break
                if not is_null:
                    break
            except Exception:
                continue

        if is_null:
            # Debug: imprimir qué hay en la página
            debug_text = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('button, a').forEach(el => {
                        if (el.offsetParent !== null) {
                            items.push(el.tagName + ': ' + el.textContent.trim().substring(0, 50));
                        }
                    });
                    return items.join(' | ');
                }
            """)
            print(f"    ⚠️  No se encontró el botón Eliminar")
            print(f"    🔍 Debug — elementos visibles: {debug_text[:300]}")
            return False

    # 6. Hacer scroll al elemento y clic
    await boton_eliminar.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
    await asyncio.sleep(random.uniform(0.5, 1.0))

    # Obtener posición para clic orgánico
    box = await boton_eliminar.as_element().bounding_box() if hasattr(boton_eliminar, 'as_element') else await boton_eliminar.bounding_box()
    if box:
        target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
        await mover_mouse_organico(page, target_x, target_y)
        await asyncio.sleep(random.uniform(*PAUSA_ANTES_CLIC))
        await page.mouse.click(target_x, target_y)
    else:
        # Fallback: clic directo vía JS
        await boton_eliminar.evaluate("el => el.click()")

    print("    🖱️  Clic en Eliminar (barra de acciones)")
    await asyncio.sleep(random.uniform(1.5, 3.0))

    # 7. Manejar modales de confirmación
    eliminado = await _manejar_modales_eliminacion(page)

    if not eliminado:
        return False

    # 8. Verificar que realmente se eliminó
    await asyncio.sleep(random.uniform(2.0, 3.0))
    realmente_eliminado = await _verificar_eliminacion(page, item_id)

    if realmente_eliminado:
        return True
    else:
        print("    ⚠️  No se pudo confirmar la eliminación")
        return False


async def _manejar_modales_eliminacion(page):
    """
    Maneja los modales que aparecen al eliminar.

    Flujo: tras clic en "Eliminar" de la barra de acciones, puede aparecer:
    1. Modal "¿Estás seguro?" → clic "Eliminar" rojo
    2. Modal "¿A quién le vendiste?" → "Eliminar sin indicar comprador" → "Eliminar" rojo
    A veces aparece solo uno, a veces ambos, a veces ninguno.
    """
    # Intentar procesar hasta 3 modales consecutivos
    for ronda in range(3):
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # ── ¿Ya se eliminó? (redirect) ──
        if "/account" in page.url and "/manage" not in page.url:
            print("    ✅ Redirigió a cuenta — eliminado")
            return True

        # ── Debug: ver qué hay en la página ──
        debug_info = await page.evaluate("""
            () => {
                const result = { buttons: [], texts: [] };
                document.querySelectorAll('button').forEach(b => {
                    if (b.offsetParent !== null) {
                        result.buttons.push(b.textContent.trim().substring(0, 60));
                    }
                });
                // Buscar textos de modales
                const body = document.body.innerText;
                if (body.includes('seguro')) result.texts.push('seguro');
                if (body.includes('eliminar')) result.texts.push('eliminar');
                if (body.includes('vendiste')) result.texts.push('vendiste');
                if (body.includes('sin indicar')) result.texts.push('sin indicar');
                if (body.includes('Cancelar')) result.texts.push('Cancelar');
                return result;
            }
        """)
        print(f"    🔍 Debug — botones: {debug_info['buttons']}, textos clave: {debug_info['texts']}")

        # ── Caso A: Modal "¿A quién le vendiste?" ──
        if 'vendiste' in debug_info['texts'] or 'sin indicar' in debug_info['texts']:
            print("    📋 Modal: '¿A quién le vendiste?'")

            # Clic en "Eliminar sin indicar comprador"
            clicked_radio = await page.evaluate("""
                () => {
                    // Buscar el texto/label/radio de "Eliminar sin indicar comprador"
                    const allElements = document.querySelectorAll('label, span, div, p, input');
                    for (const el of allElements) {
                        if (el.textContent.includes('sin indicar comprador') && el.offsetParent !== null) {
                            el.click();
                            return true;
                        }
                    }
                    // También probar con inputs tipo radio
                    const radios = document.querySelectorAll('input[type="radio"]');
                    if (radios.length > 1) {
                        radios[radios.length - 1].click();  // El último radio suele ser "sin indicar"
                        return true;
                    }
                    return false;
                }
            """)

            if clicked_radio:
                print("    ✅ Seleccionado 'sin indicar comprador'")
                await asyncio.sleep(random.uniform(0.5, 1.0))
            else:
                print("    ⚠️  No pude clicar 'sin indicar comprador'")

            # Ahora clic en el botón rojo "Eliminar" del modal
            await asyncio.sleep(random.uniform(0.3, 0.7))
            clicked = await _clic_boton_eliminar_en_modal(page)
            if clicked:
                print("    ✅ Clic en Eliminar del modal")
                await asyncio.sleep(random.uniform(1.5, 2.5))
                continue
            else:
                print("    ❌ No encontré botón Eliminar en modal")
                return False

        # ── Caso B: Modal "¿Estás seguro?" ──
        elif 'seguro' in debug_info['texts'] or 'Cancelar' in debug_info['texts']:
            print("    📋 Modal: '¿Estás seguro?' → confirmando")

            clicked = await _clic_boton_eliminar_en_modal(page)
            if clicked:
                print("    ✅ Clic en Eliminar del modal")
                await asyncio.sleep(random.uniform(1.5, 2.5))
                continue
            else:
                print("    ❌ No encontré botón Eliminar en modal de confirmación")
                return False

        # ── No hay modal reconocido ──
        else:
            if ronda == 0:
                # Primera vez, esperar un poco más
                await asyncio.sleep(random.uniform(1.0, 2.0))
                continue
            else:
                # Ya esperamos, salir
                break

    return True


async def _clic_boton_eliminar_en_modal(page):
    """
    Busca y clica el botón rojo "Eliminar" que está DENTRO de un modal.
    Estrategia: buscar todos los botones visibles con texto "Eliminar"
    y clicar el que NO sea el de la barra de acciones inferior.
    """
    clicked = await page.evaluate("""
        () => {
            // Recopilar todos los botones visibles que digan "Eliminar"
            const eliminarBtns = [];
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text === 'Eliminar' && btn.offsetParent !== null) {
                    const rect = btn.getBoundingClientRect();
                    eliminarBtns.push({ el: btn, y: rect.y, w: rect.width, h: rect.height });
                }
            });

            if (eliminarBtns.length === 0) return false;

            // Si hay solo 1, clicarlo
            if (eliminarBtns.length === 1) {
                eliminarBtns[0].el.click();
                return true;
            }

            // Si hay varios, el del modal suele:
            // - Estar más arriba en la página (dentro del modal overlay)
            // - Ser más ancho (es un botón grande, no un icono pequeño)
            // El de la barra de acciones es pequeño (icono + texto)
            // El del modal es ancho (ocupa medio modal)

            // Ordenar por ancho descendente — el más ancho es probable el del modal
            eliminarBtns.sort((a, b) => b.w - a.w);

            // Clicar el más ancho
            eliminarBtns[0].el.click();
            return true;
        }
    """)
    return clicked


async def _verificar_eliminacion(page, item_id):
    """
    Verifica que el anuncio realmente se eliminó.
    """
    try:
        # Si la URL actual ya es /account, se eliminó
        current_url = page.url
        if "/account" in current_url and "/manage" not in current_url:
            return True

        # Navegar al anuncio para verificar
        url = URL_GESTIONAR.format(id=item_id)
        response = await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(2.0, 3.0))

        # Si redirigió a home o cuenta = eliminado
        final_url = page.url
        if final_url == "https://www.revolico.com/" or ("/account" in final_url and "/manage" not in final_url):
            return True

        # Si respuesta 404
        if response and response.status == 404:
            return True

        # Si muestra textos de "no encontrado"
        page_text = await page.evaluate("document.body.innerText")
        indicadores_borrado = [
            "este anuncio no existe",
            "anuncio no encontrado",
            "no se encontró",
            "ha sido eliminado",
            "no encontrado",
        ]
        page_text_lower = page_text.lower()
        for indicador in indicadores_borrado:
            if indicador in page_text_lower:
                return True

        # Si todavía hay botón Eliminar visible = NO se eliminó
        boton_eliminar = await page.query_selector('button:has-text("Eliminar")')
        if boton_eliminar and await boton_eliminar.is_visible():
            return False

        # Si hay botón "Gestionar anuncio" = aún existe
        gestionar = await page.query_selector('text="Gestionar anuncio"')
        if gestionar and await gestionar.is_visible():
            return False

        return True

    except Exception:
        return True


# ══════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Eliminar anuncios publicados de una cuenta de Revolico (v1.1.0)"
    )
    parser.add_argument(
        "--email", required=True,
        help="Email de la cuenta cuyos anuncios se eliminarán"
    )
    parser.add_argument(
        "--port", type=int, default=9222,
        help="Puerto de Chrome debug (default: 9222)"
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Solo mostrar qué se eliminaría, sin hacerlo"
    )
    parser.add_argument(
        "--limite", type=int, default=0,
        help="Máximo de anuncios a eliminar (default: 0 = todos)"
    )
    parser.add_argument(
        "--rafaga", type=int, default=DEFAULT_RAFAGA,
        help=f"Anuncios por ráfaga (default: {DEFAULT_RAFAGA})"
    )
    parser.add_argument(
        "--descanso", type=int, default=DEFAULT_DESCANSO_MIN,
        help=f"Minutos de descanso entre ráfagas (default: {DEFAULT_DESCANSO_MIN})"
    )

    args = parser.parse_args()

    # ── Cargar estado de la cuenta ──
    cuenta = cargar_cuenta(args.email)
    publicados = obtener_publicados(cuenta)

    if not publicados:
        print(f"\n⚠️  No hay anuncios con estado 'publicado' para {args.email}")
        print(f"   Total publicaciones en el archivo: {len(cuenta.get('publicaciones', []))}")
        sys.exit(0)

    # Aplicar límite
    if args.limite > 0:
        publicados = publicados[:args.limite]

    # Extraer IDs
    anuncios_a_eliminar = []
    for pub in publicados:
        item_id = extraer_id_de_url(pub.get("url_revolico"))
        if item_id:
            anuncios_a_eliminar.append({
                "producto": pub["producto"],
                "item_id": item_id,
                "url": pub.get("url_revolico"),
            })
        else:
            print(f"  ⚠️  No se pudo extraer ID de: {pub.get('url_revolico')} (producto: {pub['producto']})")

    # ── Header ──
    print(f"\n{'='*60}")
    print(f"  🗑️  ELIMINADOR DE ANUNCIOS — REVOLICO v1.1.0")
    print(f"{'='*60}")
    print(f"  Cuenta: {args.email}")
    print(f"  Anuncios a eliminar: {len(anuncios_a_eliminar)}")
    print(f"  Modo: {'PREVIEW (no elimina)' if args.preview else 'EJECUCIÓN REAL'}")
    print(f"{'='*60}\n")

    # ── Preview ──
    if args.preview:
        print("📋 Anuncios que se eliminarían:\n")
        for i, a in enumerate(anuncios_a_eliminar):
            print(f"  {i+1}. {a['producto']} (ID {a['item_id']})")
        print(f"\n  Total: {len(anuncios_a_eliminar)}")
        print(f"\n  Para eliminar de verdad, quita el --preview")
        return

    # ── Conectar a Chrome ──
    async with async_playwright() as p:
        print(f"🔌 Conectando a Chrome en puerto {args.port}...")
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
        except Exception as e:
            print(f"\n❌ No se pudo conectar a Chrome en el puerto {args.port}")
            print(f"   Error: {e}")
            print(f"   Asegúrate de que Chrome está abierto con:")
            print(f"   google-chrome --remote-debugging-port={args.port}")
            sys.exit(1)

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        await limpiar_huellas(page)

        # ── Navegar a cuenta para verificar sesión ──
        await page.goto(URL_CUENTA, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))

        if await detectar_cloudflare(page):
            resuelto = await manejar_cloudflare(page)
            if not resuelto:
                print("🛑 Cloudflare no se resolvió. Resuélvelo manualmente.")
                sys.exit(1)

        # ── Procesar eliminaciones ──
        eliminados = 0
        fallidos = 0
        cloudflares_seguidos = 0
        anuncios_en_rafaga = 0
        inicio = time.time()

        for i, anuncio in enumerate(anuncios_a_eliminar):
            print(f"\n  [{i+1}/{len(anuncios_a_eliminar)}] {anuncio['producto']} (ID {anuncio['item_id']})")

            resultado = await eliminar_anuncio(page, anuncio["item_id"])

            if resultado == "cloudflare":
                cloudflares_seguidos += 1
                print(f"    🚨 Cloudflare ({cloudflares_seguidos}/{MAX_CLOUDFLARES_SEGUIDOS})")

                if cloudflares_seguidos >= MAX_CLOUDFLARES_SEGUIDOS:
                    print(f"\n  🛑 {MAX_CLOUDFLARES_SEGUIDOS} Cloudflares seguidos. Deteniendo.")
                    break

                resuelto = await manejar_cloudflare(page)
                if resuelto:
                    cloudflares_seguidos = 0
                    fallidos += 1
                else:
                    print(f"\n  🛑 Cloudflare no se resolvió. Deteniendo.")
                    break

            elif resultado is True:
                print(f"    ✅ Eliminado")
                eliminados += 1
                cloudflares_seguidos = 0
                anuncios_en_rafaga += 1

                # Actualizar estado
                cuenta = marcar_como_eliminado(cuenta, anuncio["producto"])
                guardar_cuenta(args.email, cuenta)

            else:
                print(f"    ❌ Falló")
                fallidos += 1
                cloudflares_seguidos = 0

            # Pausa entre anuncios
            if i < len(anuncios_a_eliminar) - 1:
                pausa = random.uniform(*PAUSA_ENTRE_ANUNCIOS)
                print(f"    ⏳ Pausa {pausa:.0f}s...")
                await asyncio.sleep(pausa)

            # Control de ráfagas
            if anuncios_en_rafaga >= args.rafaga and i < len(anuncios_a_eliminar) - 1:
                descanso = args.descanso * 60 + random.uniform(-60, 60)
                print(f"\n  💤 Ráfaga completada. Descansando {descanso/60:.1f} min...")
                await asyncio.sleep(descanso)
                anuncios_en_rafaga = 0

        # ── Resumen ──
        duracion = time.time() - inicio

        print(f"\n{'='*55}")
        print(f"  📊 RESUMEN FINAL")
        print(f"{'='*55}")
        print(f"  ✅ Eliminados  : {eliminados}")
        print(f"  ❌ Fallidos    : {fallidos}")
        print(f"  📦 Total       : {len(anuncios_a_eliminar)}")
        print(f"  ⏱️  Duración   : {duracion/60:.1f} minutos")
        print(f"{'='*55}")
        print(f"\n🎉 ¡Proceso terminado!")

        if eliminados > 0:
            print(f"\n💡 Ahora puedes republicar con:")
            print(f"   python3 scripts-opus/publicar_v2.py --email {args.email}")


if __name__ == "__main__":
    asyncio.run(main())
