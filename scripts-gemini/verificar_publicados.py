#!/usr/bin/env python3
"""
verificar_publicados.py — Verifica qué anuncios siguen vivos en Revolico

Estrategia (basada en verificar-antes-de-publicar.py del v1.0.0):
  1. Navega a /account/ads
  2. Hace scroll para cargar TODOS los anuncios (lazy loading)
  3. Extrae los IDs de los botones "Gestionar" (igual que el script viejo)
  4. Compara contra los IDs del sistema de estado
  5. DOBLE VERIFICACIÓN: para los que no aparecen, navega a la URL
     directa y verifica si dice "Anuncio despublicado" o redirige

Incluye SAFEGUARD: si no se encuentra ningún botón "Gestionar",
ABORTA el proceso para evitar marcar todo como borrado por error.

Uso:
    python3 scripts-opus/verificar_publicados.py --email cuenta@gmail.com
    python3 scripts-opus/verificar_publicados.py --todas
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

PAUSA_CARGA_PAGINA = (4.0, 7.0)
PAUSA_CLOUDFLARE = (120, 300)
MAX_CLOUDFLARES_SEGUIDOS = 3

URL_CUENTA = "https://www.revolico.com/account/ads"


# ══════════════════════════════════════════════════════════
#  UTILIDADES
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
    return cargar_json(str(ruta))


def guardar_cuenta(email, datos):
    ruta = CUENTAS_DIR / f"{email}.json"
    guardar_json(str(ruta), datos)


def listar_cuentas():
    if not CUENTAS_DIR.exists():
        return []
    return [f.stem for f in CUENTAS_DIR.glob("*.json")]


def obtener_publicados(cuenta):
    return [p for p in cuenta.get("publicaciones", []) if p.get("estado") == "publicado"]


def extraer_id_de_url(url):
    """Extrae el ID del anuncio. Compatible con ambos formatos de URL."""
    if not url:
        return None
    # Formato: /item/57493855/_/manage?action=created
    match = re.search(r'/item/(\d+)', url)
    if match:
        return match.group(1)
    # Formato: -57493855?
    match = re.search(r'-(\d+)\?', url)
    if match:
        return match.group(1)
    # Formato: -57493855
    match = re.search(r'-(\d+)$', url)
    if match:
        return match.group(1)
    return None


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
#  CARGAR IDs REALES (LÓGICA DEL SCRIPT VIEJO)
# ══════════════════════════════════════════════════════════

async def cargar_todos_los_ids(page):
    """
    Extrae IDs de anuncios haciendo scroll y leyendo los botones "Gestionar".
    Lógica idéntica al script viejo verificar-antes-de-publicar.py.
    """
    print("  ⬇️  Cargando anuncios activos (scrolleando)...")
    ids_vistos = set()
    sin_cambios = 0

    while True:
        # Buscar todos los links "Gestionar"
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()

        for el in links:
            href = await el.get_attribute("href")
            if href:
                id_ext = extraer_id_de_url(href)
                if id_ext:
                    ids_actuales.add(id_ext)

        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            ids_vistos = set(ids_actuales)
            print(f"    📦 {len(ids_vistos)} anuncios encontrados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return ids_vistos


# ══════════════════════════════════════════════════════════
#  DOBLE VERIFICACIÓN (DEL SCRIPT VIEJO)
# ══════════════════════════════════════════════════════════

async def doble_verificacion(page, item_id, url_revolico):
    """
    Cuando un anuncio no aparece en /account/ads, navega a su URL directa
    para confirmar si realmente fue borrado o es una falsa alarma.

    Retorna:
        - "borrado": confirmado borrado/despublicado
        - "vivo": falsa alarma, sigue vivo
        - "error": no se pudo verificar
    """
    print(f"      🔍 Doble verificación para ID {item_id}...")

    try:
        # Navegar a la URL del anuncio
        url = url_revolico or f"https://www.revolico.com/item/{item_id}/_/manage"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(random.uniform(3, 5))

        # Comparar URLs (sin query params)
        base_expected = url.split('?')[0]
        current_base = page.url.split('?')[0]

        # Si redirigió a otra URL → borrado
        if base_expected != current_base:
            print(f"      ❌ Confirmado: Revolico redirigió a {current_base}")
            return "borrado"

        # Si carga la URL pero dice "Anuncio despublicado"
        cartel_despublicado = await page.query_selector('text="Anuncio despublicado"')
        if cartel_despublicado:
            print(f"      ❌ Confirmado: Dice 'Anuncio despublicado'")
            return "borrado"

        # Si dice "no existe" o similar
        page_text = await page.evaluate("document.body.innerText")
        page_text_lower = page_text.lower()
        indicadores_borrado = [
            "anuncio despublicado",
            "este anuncio no existe",
            "anuncio no encontrado",
            "no se encontró",
            "ha sido eliminado",
        ]
        for indicador in indicadores_borrado:
            if indicador in page_text_lower:
                print(f"      ❌ Confirmado: Contiene '{indicador}'")
                return "borrado"

        # Si cargó normal sin errores → falsa alarma, sigue vivo
        print(f"      ✅ Falsa Alarma: La URL cargó correctamente. Sigue vivo.")
        return "vivo"

    except Exception as e:
        print(f"      ⚠️  Error de red en doble verificación: {e}")
        print(f"      Asumiendo vivo por precaución")
        return "vivo"  # Por precaución, no borrar


# ══════════════════════════════════════════════════════════
#  VERIFICAR UNA CUENTA
# ══════════════════════════════════════════════════════════

async def verificar_cuenta(page, email):
    cuenta = cargar_cuenta(email)
    if not cuenta:
        print(f"  ⚠️  No se encontró archivo de estado para {email}")
        return None

    publicados = obtener_publicados(cuenta)
    if not publicados:
        print(f"  ⚠️  No hay anuncios con estado 'publicado' para {email}")
        return {"vivos": 0, "borrados": 0, "total_estado": 0, "total_revolico": 0}

    print(f"\n{'='*60}")
    print(f"  🔍 VERIFICANDO — {email}")
    print(f"{'='*60}")
    print(f"  Anuncios en estado 'publicado': {len(publicados)}")

    # ── Navegar a /account/ads ──
    print("  📄 Navegando a tu cuenta de Revolico...")
    await page.goto(URL_CUENTA, wait_until="domcontentloaded")
    print("  ⏳ Esperando que cargue la página (10 segundos)...")
    await asyncio.sleep(10)

    # Cloudflare
    if await detectar_cloudflare(page):
        resuelto = await manejar_cloudflare(page)
        if not resuelto:
            print("  🛑 Cloudflare no se resolvió")
            return None

    await limpiar_huellas(page)

    # ── SAFEGUARD: verificar que la página cargó correctamente ──
    if "/account" not in page.url:
        print(f"  ❌ Error Crítico: La página no es /account (URL actual: {page.url}).")
        print(f"     Posible bloqueo o sesión cerrada. Abortando.")
        return None

    elementos_prueba = await page.query_selector_all('a:has-text("Gestionar")')
    if len(elementos_prueba) == 0:
        print("  ❌ Error Crítico: No se detectó ningún botón 'Gestionar'.")
        print("     Esto significa que la página cargó en blanco, hay un Captcha,")
        print("     o literalmente tienes 0 anuncios.")
        print("     ABORTANDO para proteger tu archivo JSON de un borrado erróneo masivo.")
        return None

    # ── Cargar todos los IDs con scroll (lógica del script viejo) ──
    ids_en_revolico = await cargar_todos_los_ids(page)
    print(f"  📊 Total anuncios activos en Revolico: {len(ids_en_revolico)}")

    # ── Comparar con el estado ──
    vivos = 0
    borrados = 0
    productos_borrados = []
    ausentes_para_verificar = []

    # Primer paso: marcar los que están presentes
    for pub in publicados:
        producto = pub["producto"]
        url = pub.get("url_revolico")
        item_id = extraer_id_de_url(url)

        if not item_id:
            print(f"    ⚠️  {producto} — Sin ID válido")
            continue

        if item_id in ids_en_revolico:
            vivos += 1
        else:
            # No está en /account/ads — necesita doble verificación
            ausentes_para_verificar.append({
                "producto": producto,
                "item_id": item_id,
                "url": url,
            })

    print(f"\n  📊 Presentes en /account/ads: {vivos}")
    print(f"  🔍 Ausentes (necesitan doble verificación): {len(ausentes_para_verificar)}")

    # ── Doble verificación de los ausentes ──
    if ausentes_para_verificar:
        print(f"\n  {'─'*50}")
        print(f"  🔍 DOBLE VERIFICACIÓN")
        print(f"  {'─'*50}")

        for i, item in enumerate(ausentes_para_verificar):
            print(f"\n    [{i+1}/{len(ausentes_para_verificar)}] {item['producto']} (ID {item['item_id']})")

            resultado = await doble_verificacion(page, item["item_id"], item["url"])

            if resultado == "borrado":
                borrados += 1
                productos_borrados.append({"producto": item["producto"], "id": item["item_id"]})

                # Actualizar estado
                for p in cuenta.get("publicaciones", []):
                    if p["producto"] == item["producto"] and p.get("estado") == "publicado":
                        p["estado"] = "borrado_por_revolico"
                        p["fecha_deteccion_borrado"] = datetime.now().isoformat()
                        break
                guardar_cuenta(email, cuenta)

            elif resultado == "vivo":
                vivos += 1
            # "error" → no contamos, por precaución

            # Pausa entre verificaciones
            if i < len(ausentes_para_verificar) - 1:
                await asyncio.sleep(random.uniform(2, 4))

    # ── Resumen ──
    stats = {
        "vivos": vivos,
        "borrados": borrados,
        "total_estado": len(publicados),
        "total_revolico": len(ids_en_revolico),
        "productos_borrados": productos_borrados,
    }

    print(f"\n  {'─'*50}")
    print(f"  📊 Resumen — {email}")
    print(f"  {'─'*50}")
    print(f"  ✅ Vivos confirmados                   : {vivos}")
    print(f"  ❌ Borrados/Despublicados por Revolico  : {borrados}")
    print(f"  📦 Total en estado 'publicado'          : {len(publicados)}")
    print(f"  🌐 Total anuncios en /account/ads       : {len(ids_en_revolico)}")

    if borrados > 0:
        pct = (borrados / len(publicados) * 100) if publicados else 0
        print(f"\n  ⚠️  Revolico borró/despublicó el {pct:.1f}% de tus anuncios")
        print(f"\n  Productos borrados/despublicados:")
        for pb in productos_borrados:
            print(f"    - {pb['producto']} (ID {pb['id']})")

    # IDs en Revolico que no están en el estado
    ids_estado = set()
    for pub in publicados:
        item_id = extraer_id_de_url(pub.get("url_revolico"))
        if item_id:
            ids_estado.add(item_id)

    ids_no_rastreados = ids_en_revolico - ids_estado
    if ids_no_rastreados:
        print(f"\n  ℹ️  {len(ids_no_rastreados)} anuncios en Revolico NO están en el sistema de estado")
        print(f"     (publicados manualmente o de otra herramienta)")

    return stats


# ══════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Verificar qué anuncios publicados siguen vivos en Revolico (v1.1.0)"
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--email", help="Email de la cuenta a verificar")
    grupo.add_argument("--todas", action="store_true", help="Verificar todas las cuentas registradas")
    parser.add_argument("--port", type=int, default=9222, help="Puerto de Chrome debug (default: 9222)")

    args = parser.parse_args()

    if args.todas:
        emails = listar_cuentas()
        if not emails:
            print("⚠️  No se encontraron cuentas en estado/cuentas/")
            sys.exit(0)
    else:
        emails = [args.email]

    print(f"\n{'='*60}")
    print(f"  🔍 VERIFICADOR DE ANUNCIOS — REVOLICO v1.1.0")
    print(f"{'='*60}")
    print(f"  Cuentas a verificar: {len(emails)}")
    for e in emails:
        print(f"    - {e}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        print(f"\n🔌 Conectando a Chrome en puerto {args.port}...")
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
        except Exception as e:
            print(f"\n❌ No se pudo conectar a Chrome en el puerto {args.port}")
            print(f"   Error: {e}")
            print(f"   google-chrome --remote-debugging-port={args.port}")
            sys.exit(1)

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        await limpiar_huellas(page)
        inicio = time.time()

        resumen_global = {}
        for email in emails:
            stats = await verificar_cuenta(page, email)
            if stats:
                resumen_global[email] = stats

        if len(emails) > 1 and resumen_global:
            total_vivos = sum(s["vivos"] for s in resumen_global.values())
            total_borrados = sum(s["borrados"] for s in resumen_global.values())
            total_estado = sum(s["total_estado"] for s in resumen_global.values())

            print(f"\n\n{'='*60}")
            print(f"  📊 RESUMEN GLOBAL — TODAS LAS CUENTAS")
            print(f"{'='*60}")
            print(f"  ✅ Vivos          : {total_vivos}")
            print(f"  ❌ Borrados       : {total_borrados}")
            print(f"  📦 Total en estado: {total_estado}")

            if total_borrados > 0:
                pct = (total_borrados / total_estado * 100) if total_estado > 0 else 0
                print(f"\n  ⚠️  Revolico está borrando el {pct:.1f}% de tus anuncios")

            print(f"\n  Detalle:")
            for email, stats in resumen_global.items():
                print(f"    {email}: {stats['vivos']} vivos, {stats['borrados']} borrados")

        duracion = time.time() - inicio
        print(f"\n  ⏱️  Duración: {duracion/60:.1f} min")
        print(f"{'='*60}")
        print(f"\n🎉 ¡Verificación terminada!")


if __name__ == "__main__":
    asyncio.run(main())
