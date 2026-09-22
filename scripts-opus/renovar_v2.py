#!/usr/bin/env python3
"""
renovar_v2.py — Script de Renovación de Anuncios en Revolico v1.1.0

Automatiza la renovación de todos los anuncios de una cuenta de Revolico.
Se conecta a un Chrome existente vía CDP (Chrome DevTools Protocol).

Uso:
    python3 scripts-opus/renovar_v2.py
    python3 scripts-opus/renovar_v2.py --port 9222 --rafaga 5 --descanso 30 --limite 50

Requisitos:
    - Chrome abierto con --remote-debugging-port=9222
    - Sesión de Revolico activa (logueado)
    - pip install playwright
"""

import asyncio
import argparse
import random
import re
import sys
import time
from datetime import datetime

from playwright.async_api import async_playwright

# ══════════════════════════════════════════════════════════
#  CONFIGURACIÓN (editable)
# ══════════════════════════════════════════════════════════

# Pausas entre acciones (segundos)
PAUSA_ENTRE_ANUNCIOS = (3.0, 9.0)      # Entre un anuncio y el siguiente
PAUSA_CARGA_PAGINA = (4.0, 7.0)          # Después de navegar a una página
PAUSA_ANTES_CLIC = (0.3, 0.8)            # Antes de hacer clic en un botón
PAUSA_DESPUES_CLIC = (1.0, 2.5)          # Después de hacer clic
PAUSA_SCROLL = (0.8, 1.5)                # Entre cada scroll para cargar anuncios
PAUSA_CLOUDFLARE = (120, 300)             # Pausa cuando se detecta Cloudflare (2-5 min)

# Ráfagas
DEFAULT_RAFAGA = 500                        # Anuncios por ráfaga
DEFAULT_DESCANSO_MIN = 30                 # Minutos de descanso entre ráfagas

# Reintentos
DEFAULT_MAX_RONDAS = 5                    # Rondas máximas de reintentos
MAX_CLOUDFLARES_SEGUIDOS = 3              # Cloudflares consecutivos antes de parar

# Scroll
MAX_SCROLLS_SIN_CAMBIO = 4               # Scrolls sin nuevos anuncios = fin de carga

# URLs
URL_CUENTA = "https://www.revolico.com/account/ads"
URL_GESTIONAR = "https://www.revolico.com/item/{id}/_/manage"


# ══════════════════════════════════════════════════════════
#  UTILIDADES ANTI-DETECCIÓN
# ══════════════════════════════════════════════════════════

async def limpiar_huellas(page):
    """Limpia rastros de automatización del navegador."""
    try:
        await page.evaluate("""
            // Eliminar flag de webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // Eliminar rastros de Playwright
            if (window.__playwright) delete window.__playwright;
            if (window.__pw_manual) delete window.__pw_manual;
        """)
    except Exception:
        pass


async def mover_mouse_organico(page, target_x, target_y):
    """
    Mueve el mouse de forma orgánica hacia un punto objetivo.
    Simula movimiento humano con curva suave + ruido aleatorio.
    """
    # Punto de origen aleatorio (simula que el mouse estaba en algún lugar)
    current_x = random.randint(100, 800)
    current_y = random.randint(100, 500)

    steps = random.randint(5, 12)

    for i in range(steps):
        progress = (i + 1) / steps
        # Interpolación con curva suave (ease-in-out)
        ease = progress * progress * (3 - 2 * progress)
        x = current_x + (target_x - current_x) * ease + random.uniform(-5, 5)
        y = current_y + (target_y - current_y) * ease + random.uniform(-5, 5)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.04))

    # Posicionar exactamente en el objetivo al final
    await page.mouse.move(target_x, target_y)


async def clic_organico(page, selector, descripcion="elemento"):
    """
    Hace clic en un elemento de forma orgánica:
    1. Lo busca
    2. Obtiene su posición
    3. Mueve el mouse orgánicamente
    4. Hace clic
    """
    el = await page.query_selector(selector)
    if not el:
        return False

    # Obtener posición del elemento
    box = await el.bounding_box()
    if not box:
        # Fallback: clic directo vía JS
        await page.evaluate("el => el.click()", el)
        return True

    # Punto dentro del elemento (con variación)
    target_x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
    target_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)

    # Pausa antes del clic
    await asyncio.sleep(random.uniform(*PAUSA_ANTES_CLIC))

    # Mover mouse orgánicamente
    await mover_mouse_organico(page, target_x, target_y)

    # Clic
    await page.mouse.click(target_x, target_y)

    # Pausa después del clic
    await asyncio.sleep(random.uniform(*PAUSA_DESPUES_CLIC))

    return True


async def scroll_suave(page):
    """Hace scroll de forma suave, como un humano."""
    scroll_amount = random.randint(400, 800)
    await page.evaluate(f"""
        window.scrollBy({{
            top: {scroll_amount},
            behavior: 'smooth'
        }});
    """)
    await asyncio.sleep(random.uniform(*PAUSA_SCROLL))


# ══════════════════════════════════════════════════════════
#  DETECCIÓN DE CLOUDFLARE
# ══════════════════════════════════════════════════════════

async def detectar_cloudflare(page):
    """
    Detecta si Cloudflare está mostrando un challenge.
    Retorna True si se detecta Cloudflare.
    """
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


async def manejar_cloudflare(page, contador_cf):
    """
    Maneja una detección de Cloudflare.
    En vez de sys.exit(), pausa y espera resolución.

    Retorna:
        - True si se resolvió y se puede continuar
        - False si no se resolvió después de esperar
    """
    print("\n🚨 ¡CLOUDFLARE DETECTADO! 🚨")
    print("   El script se pausará para no levantar sospechas.")
    print("   Si estás cerca, resuelve el captcha manualmente en Chrome.")

    pausa = random.uniform(*PAUSA_CLOUDFLARE)
    minutos = pausa / 60
    print(f"   ⏳ Esperando {minutos:.1f} minutos...")

    await asyncio.sleep(pausa)

    # Intentar navegar a /account/ads para ver si se resolvió
    try:
        await page.goto(URL_CUENTA, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 5))

        if not await detectar_cloudflare(page):
            print("   ✅ Cloudflare resuelto. Continuando...")
            return True
        else:
            print("   ❌ Cloudflare sigue activo.")
            return False
    except Exception as e:
        print(f"   ❌ Error al verificar: {e}")
        return False


# ══════════════════════════════════════════════════════════
#  CERRAR POPUPS
# ══════════════════════════════════════════════════════════

async def cerrar_popup_destacados(page):
    """
    Cierra el popup de "Anuncios Destacados" / "Más ventajas con Destacados".
    Maneja ambas variantes visuales (Ubuntu y Windows).
    """
    # Intentar con cada selector posible del botón ✕
    selectores_cierre = [
        'button[aria-label="Close"]',
        'button[aria-label="Cerrar"]',
        '[data-slot="dialog-close"]',
        '[data-slot="dialog-portal"] button:first-child',
        # Selectores basados en la estructura del modal
        'div[role="dialog"] button[aria-label="Close"]',
        'div[role="dialog"] button[aria-label="Cerrar"]',
    ]

    for sel in selectores_cierre:
        try:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await asyncio.sleep(random.uniform(0.5, 1.0))
                box = await btn.bounding_box()
                if box:
                    await mover_mouse_organico(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    await btn.click()
                else:
                    await page.evaluate("el => el.click()", btn)
                await asyncio.sleep(random.uniform(0.5, 1.5))
                print("    🔒 Popup de Destacados cerrado")
                return True
        except Exception:
            continue

    # Fallback: clic fuera del modal (en el backdrop/overlay)
    try:
        overlay = await page.query_selector('[data-slot="dialog-overlay"]')
        if overlay:
            await overlay.click(position={"x": 5, "y": 5})
            await asyncio.sleep(random.uniform(0.5, 1.0))
            print("    🔒 Popup cerrado (clic en overlay)")
            return True
    except Exception:
        pass

    # Último recurso: presionar Escape
    try:
        await page.keyboard.press("Escape")
        await asyncio.sleep(random.uniform(0.5, 1.0))
        # Verificar si se cerró
        dialog = await page.query_selector('div[role="dialog"]')
        if not dialog or not await dialog.is_visible():
            print("    🔒 Popup cerrado (Escape)")
            return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════
#  CARGAR TODOS LOS ANUNCIOS (SCROLL)
# ══════════════════════════════════════════════════════════

async def cargar_todos_los_anuncios(page):
    """
    Hace scroll completo en /account/ads para cargar TODOS los anuncios
    (Revolico usa lazy loading).

    Retorna una lista de IDs de anuncios.
    """
    print("⬇️  Cargando todos los anuncios (scroll)...")

    ids_vistos = set()
    sin_cambios = 0

    while True:
        # Buscar todos los links de "Gestionar"
        links = await page.query_selector_all('a:has-text("Gestionar")')

        ids_actuales = set()
        for el in links:
            try:
                href = await el.get_attribute("href")
                if href:
                    # Extraer ID del href: /item/slug-{ID}?token=_ o /item/{ID}/_/manage
                    match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
                    if match:
                        ids_actuales.add(match.group(1))
            except Exception:
                continue

        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= MAX_SCROLLS_SIN_CAMBIO:
                break
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
            print(f"  📦 {len(ids_vistos)} anuncios cargados...")

        await scroll_suave(page)

    print(f"  ✅ Total cargados: {len(ids_vistos)}")
    return list(ids_vistos)


# ══════════════════════════════════════════════════════════
#  RENOVAR UN ANUNCIO
# ══════════════════════════════════════════════════════════

async def renovar_anuncio(page, item_id):
    """
    Renueva un anuncio individual.

    Retorna:
        - True: renovado exitosamente
        - False: falló (Cloudflare, error, etc.)
        - None: ya estaba renovado hoy (no se encontró botón)
    """
    # 1. Navegar a la página de gestión
    url = URL_GESTIONAR.format(id=item_id)
    try:
        await page.goto(url, wait_until="domcontentloaded")
    except Exception as e:
        print(f"    ❌ Error navegando: {e}")
        return False

    # Pausa de carga
    await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))

    # 2. Verificar Cloudflare
    if await detectar_cloudflare(page):
        return "cloudflare"

    # 3. Limpiar huellas
    await limpiar_huellas(page)

    # 4. Cerrar popup de Destacados (si aparece)
    await asyncio.sleep(random.uniform(1.0, 2.0))
    await cerrar_popup_destacados(page)

    # 5. Buscar el botón de Renovar
    # En la nueva UI, "Renovar" es un icono en la barra de acciones inferior
    selectores_renovar = [
        'button:has-text("Renovar")',
        'a:has-text("Renovar")',
        # Selector más específico: botón que contiene exactamente "Renovar" (no "Renovar anuncio")
        'button:text-is("Renovar")',
        # Por el icono de renovar (si tiene un data attribute)
        '[data-testid*="renew"]',
        '[data-testid*="renovar"]',
    ]

    boton_renovar = None
    for sel in selectores_renovar:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                boton_renovar = el
                break
        except Exception:
            continue

    if not boton_renovar:
        # No se encontró botón — posiblemente ya renovado hoy
        # Verificar si existe texto que indique ya renovado
        ya_renovado = await page.query_selector('text="Ya renovaste este anuncio"')
        if ya_renovado:
            return None

        # Otra verificación: si el botón existe pero está deshabilitado
        for sel in selectores_renovar[:2]:
            try:
                el = await page.query_selector(sel)
                if el:
                    disabled = await el.get_attribute("disabled")
                    if disabled is not None:
                        return None
            except Exception:
                continue

        # Si realmente no se encontró nada
        print("    ⚠️  No se encontró el botón Renovar")
        return None

    # 6. Hacer clic orgánico en Renovar
    box = await boton_renovar.bounding_box()
    if box:
        await mover_mouse_organico(
            page,
            box["x"] + box["width"] * random.uniform(0.3, 0.7),
            box["y"] + box["height"] * random.uniform(0.3, 0.7),
        )
        await asyncio.sleep(random.uniform(*PAUSA_ANTES_CLIC))
        await boton_renovar.click()
    else:
        await page.evaluate("el => el.click()", boton_renovar)

    await asyncio.sleep(random.uniform(2.0, 4.0))

    # 7. Esperar confirmación
    try:
        await page.wait_for_selector(
            'text="Tu anuncio fue renovado.", text="La verificación falló"',
            timeout=15000,
        )
    except Exception:
        # Timeout — intentar verificar manualmente
        pass

    # 8. Verificar resultado
    # Éxito
    confirmacion = await page.query_selector('text="Tu anuncio fue renovado."')
    if confirmacion:
        # Cerrar modal de confirmación
        try:
            entendido = await page.query_selector('button:has-text("Entendido")')
            if entendido:
                await asyncio.sleep(random.uniform(0.5, 1.0))
                await page.evaluate("el => el.click()", entendido)
                await asyncio.sleep(random.uniform(0.5, 1.0))
        except Exception:
            pass
        return True

    # Cloudflare durante la renovación
    if await detectar_cloudflare(page):
        return "cloudflare"

    # Verificación de Cloudflare falló
    verificacion_fallida = await page.query_selector('text="La verificación falló"')
    if verificacion_fallida:
        print("    ⚠️  Cloudflare: verificación falló")
        return False

    # Si llegamos aquí, no sabemos qué pasó — asumir fallo
    return False


# ══════════════════════════════════════════════════════════
#  PROCESAMIENTO DE LISTA
# ══════════════════════════════════════════════════════════

async def procesar_lista(page, ids, args, stats):
    """
    Procesa una lista de IDs de anuncios.

    Args:
        page: Playwright page
        ids: Lista de IDs a procesar
        args: Argumentos del CLI
        stats: Dict con estadísticas acumuladas

    Retorna lista de IDs fallidos.
    """
    fallidos = []
    cloudflares_seguidos = 0
    anuncios_en_rafaga = 0

    for i, item_id in enumerate(ids):
        # Verificar límite
        total_procesados = stats["renovados"] + stats["ya_renovados"] + stats["fallidos_count"]
        if args.limite > 0 and total_procesados >= args.limite:
            print(f"\n  🛑 Límite de {args.limite} anuncios alcanzado")
            break

        print(f"\n  [{i+1}/{len(ids)}] ID {item_id}")

        resultado = await renovar_anuncio(page, item_id)

        if resultado == "cloudflare":
            cloudflares_seguidos += 1
            print(f"    🚨 Cloudflare ({cloudflares_seguidos}/{MAX_CLOUDFLARES_SEGUIDOS})")

            if cloudflares_seguidos >= MAX_CLOUDFLARES_SEGUIDOS:
                print(f"\n  🛑 {MAX_CLOUDFLARES_SEGUIDOS} Cloudflares seguidos. Deteniendo.")
                print("     Resuelve el captcha en Chrome y vuelve a correr el script.")
                fallidos.extend(ids[i:])  # Los restantes como fallidos
                break

            resuelto = await manejar_cloudflare(page, cloudflares_seguidos)
            if resuelto:
                cloudflares_seguidos = 0
                fallidos.append(item_id)  # Reintentar este anuncio
            else:
                print(f"\n  🛑 Cloudflare no se resolvió. Deteniendo.")
                fallidos.extend(ids[i:])
                break

        elif resultado is True:
            print(f"    ✅ Renovado")
            stats["renovados"] += 1
            cloudflares_seguidos = 0
            anuncios_en_rafaga += 1

        elif resultado is None:
            print(f"    ⏭️  Ya renovado hoy")
            stats["ya_renovados"] += 1
            cloudflares_seguidos = 0

        else:  # False
            print(f"    ❌ Falló — se reintentará")
            stats["fallidos_count"] += 1
            fallidos.append(item_id)
            cloudflares_seguidos = 0

        # Pausa entre anuncios
        if i < len(ids) - 1:
            pausa = random.uniform(*PAUSA_ENTRE_ANUNCIOS)
            print(f"    ⏳ Pausa {pausa:.0f}s...")
            await asyncio.sleep(pausa)

        # Control de ráfagas
        if anuncios_en_rafaga >= args.rafaga and i < len(ids) - 1:
            descanso_seg = args.descanso * 60 + random.uniform(-60, 60)
            minutos_real = descanso_seg / 60
            print(f"\n  💤 Ráfaga de {args.rafaga} completada. Descansando {minutos_real:.1f} min...")
            await asyncio.sleep(descanso_seg)
            anuncios_en_rafaga = 0

            # Volver a /account/ads para "refrescar"
            try:
                await page.goto(URL_CUENTA, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))
                if await detectar_cloudflare(page):
                    resuelto = await manejar_cloudflare(page, 0)
                    if not resuelto:
                        print("  🛑 Cloudflare tras descanso. Deteniendo.")
                        fallidos.extend(ids[i+1:])
                        break
            except Exception:
                pass

    return fallidos


# ══════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════

async def main():
    # ── Parsear argumentos ──
    parser = argparse.ArgumentParser(
        description="Renovar anuncios de Revolico automáticamente (v1.1.0)"
    )
    parser.add_argument(
        "--port", type=int, default=9222,
        help="Puerto de Chrome debug (default: 9222)"
    )
    parser.add_argument(
        "--rafaga", type=int, default=DEFAULT_RAFAGA,
        help=f"Anuncios por ráfaga (default: {DEFAULT_RAFAGA})"
    )
    parser.add_argument(
        "--descanso", type=int, default=DEFAULT_DESCANSO_MIN,
        help=f"Minutos de descanso entre ráfagas (default: {DEFAULT_DESCANSO_MIN})"
    )
    parser.add_argument(
        "--limite", type=int, default=0,
        help="Máximo de anuncios a renovar (default: 0 = todos)"
    )
    parser.add_argument(
        "--max-rondas", type=int, default=DEFAULT_MAX_RONDAS,
        help=f"Rondas de reintentos (default: {DEFAULT_MAX_RONDAS})"
    )

    args = parser.parse_args()

    # ── Conectar a Chrome ──
    print(f"\n{'='*60}")
    print(f"  🔄 RENOVADOR DE ANUNCIOS — REVOLICO v1.1.0")
    print(f"{'='*60}")
    print(f"  Puerto: {args.port}")
    print(f"  Ráfaga: {args.rafaga} anuncios + {args.descanso} min descanso")
    print(f"  Límite: {'sin límite' if args.limite == 0 else args.limite}")
    print(f"  Rondas máx: {args.max_rondas}")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        print(f"🔌 Conectando a Chrome en puerto {args.port}...")
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
        except Exception as e:
            print(f"\n❌ No se pudo conectar a Chrome en el puerto {args.port}")
            print(f"   Error: {e}")
            print(f"\n   Asegúrate de que Chrome está abierto con:")
            print(f"   google-chrome --remote-debugging-port={args.port}")
            sys.exit(1)

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado a Chrome\n")

        # ── Limpiar huellas ──
        await limpiar_huellas(page)

        # ── Navegar a cuenta ──
        print("📄 Navegando a la cuenta de Revolico...")
        await page.goto(URL_CUENTA, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))

        # Verificar Cloudflare
        if await detectar_cloudflare(page):
            resuelto = await manejar_cloudflare(page, 0)
            if not resuelto:
                print("🛑 No se pudo superar Cloudflare. Resuélvelo manualmente y reintenta.")
                sys.exit(1)

        # ── Cargar todos los anuncios ──
        await asyncio.sleep(random.uniform(3, 5))
        todos_los_ids = await cargar_todos_los_anuncios(page)
        total = len(todos_los_ids)

        if total == 0:
            print("\n⚠️  No se encontraron anuncios.")
            print("   ¿Estás logueado en Revolico? Verifica en Chrome.")
            sys.exit(0)

        print(f"\n📦 Total de anuncios encontrados: {total}")

        # Procesar de abajo hacia arriba (los más viejos primero)
        ids_a_procesar = list(reversed(todos_los_ids))

        # ── Estadísticas ──
        stats = {
            "renovados": 0,
            "ya_renovados": 0,
            "fallidos_count": 0,
        }
        inicio = time.time()

        # ── Ronda 1: todos ──
        print(f"\n{'='*55}")
        print(f"  RONDA 1 — {len(ids_a_procesar)} anuncios")
        print(f"{'='*55}")

        fallidos = await procesar_lista(page, ids_a_procesar, args, stats)

        # ── Rondas de reintentos ──
        for ronda in range(2, args.max_rondas + 1):
            if not fallidos:
                print(f"\n✨ Sin fallidos — no se necesitan más rondas")
                break

            print(f"\n{'='*55}")
            print(f"  RONDA {ronda} — {len(fallidos)} fallidos a reintentar")
            print(f"{'='*55}")

            # Pausa entre rondas
            pausa_ronda = random.uniform(10, 30)
            print(f"  ⏳ Pausa de {pausa_ronda:.0f}s antes de reintentar...")
            await asyncio.sleep(pausa_ronda)

            # Volver a /account/ads
            try:
                await page.goto(URL_CUENTA, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(*PAUSA_CARGA_PAGINA))
            except Exception:
                pass

            fallidos = await procesar_lista(page, fallidos, args, stats)

        # ── Resumen final ──
        duracion = time.time() - inicio
        duracion_min = duracion / 60

        print(f"\n{'='*55}")
        print(f"  📊 RESUMEN FINAL")
        print(f"{'='*55}")
        print(f"  ✅ Renovados           : {stats['renovados']}")
        print(f"  ⏭️  Ya renovados hoy   : {stats['ya_renovados']}")
        print(f"  ❌ Fallidos definitivos: {len(fallidos)}")
        if fallidos:
            # Mostrar máximo 10 IDs
            ids_muestra = fallidos[:10]
            print(f"     IDs: {', '.join(ids_muestra)}")
            if len(fallidos) > 10:
                print(f"     ... y {len(fallidos) - 10} más")
        print(f"  📦 Total anuncios      : {total}")
        print(f"  ⏱️  Duración           : {duracion_min:.1f} minutos")
        print(f"  🕐 Hora de inicio      : {datetime.fromtimestamp(inicio).strftime('%H:%M:%S')}")
        print(f"  🕐 Hora de fin         : {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*55}")
        print(f"\n🎉 ¡Proceso terminado!")


if __name__ == "__main__":
    asyncio.run(main())
