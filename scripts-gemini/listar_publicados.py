#!/usr/bin/env python3
"""
listar_publicados.py — Lista todos los productos actualmente publicados en la cuenta de Revolico.

Conecta a Chrome via CDP, navega a /account/ads, hace scroll para cargar
todos los anuncios por lazy loading, y muestra la lista completa de productos
con su nombre, precio e ID, junto con el total final.

Uso:
    python3 scripts-gemini/listar_publicados.py --port=9223
    python3 scripts-gemini/listar_publicados.py --email catalogo.ventas.cuba@gmail.com --port=9223
    python3 scripts-gemini/listar_publicados.py --port=9223 --guardar
"""

import asyncio
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

URL_CUENTA = "https://www.revolico.com/account/ads"
BASE_DIR = Path(__file__).parent.parent
ESTADO_DIR = BASE_DIR / "estado"


async def limpiar_huellas(page):
    """Elimina rastros de automatización del navegador."""
    try:
        await page.evaluate("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            if (window.__playwright) delete window.__playwright;
            if (window.__pw_manual) delete window.__pw_manual;
        """)
    except Exception:
        pass


async def detectar_cloudflare(page):
    """Detecta si la página actual tiene challenge de Cloudflare."""
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


async def obtener_email_sesion(context):
    """Intenta obtener el email logueado en Revolico."""
    for page in context.pages:
        try:
            user_el = await page.query_selector('.user-email, [class*="user-email"], [class*="profile"] span')
            if user_el:
                txt = (await user_el.text_content()).strip()
                if "@" in txt:
                    return txt
        except Exception:
            pass
    return None


async def hacer_scroll_completo(page):
    """Hace scroll continuo hasta el fondo de la página hasta cargar todos los anuncios."""
    print("  ⬇️  Cargando anuncios con scroll...")
    ids_vistos = set()
    sin_cambios = 0
    max_sin_cambio = 3

    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()

        for link in links:
            href = await link.get_attribute("href") or ""
            m = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
            if m:
                ids_actuales.add(m.group(1))

        if len(ids_actuales) > len(ids_vistos):
            ids_vistos = ids_actuales
            sin_cambios = 0
            print(f"     📦 {len(ids_vistos)} anuncios detectados...")
        else:
            sin_cambios += 1
            if sin_cambios >= max_sin_cambio:
                break

        # Scroll al fondo
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.8)

    print(f"  ✅ Scroll completado: {len(ids_vistos)} anuncios cargados.")
    return ids_vistos


async def extraer_productos(page):
    """Extrae los detalles (nombre, precio, id, enlace) de cada anuncio cargado."""
    links = await page.query_selector_all('a:has-text("Gestionar")')
    productos = []
    ids_registrados = set()

    for link in links:
        href = await link.get_attribute("href") or ""
        m = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
        item_id = m.group(1) if m else ""

        if not item_id or item_id in ids_registrados:
            continue
        ids_registrados.add(item_id)

        try:
            raw_text = await link.inner_text()
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            header_line = lines[0] if lines else "Sin título"

            if "·" in header_line:
                partes = header_line.split("·", 1)
                precio = partes[0].strip()
                nombre = partes[1].strip()
            else:
                precio = ""
                nombre = header_line.replace("Gestionar", "").strip()

            url_completa = f"https://www.revolico.com/item/{item_id}/_/manage"

            productos.append({
                "numero": len(productos) + 1,
                "nombre": nombre,
                "precio": precio,
                "id": item_id,
                "url": url_completa,
                "href_original": href
            })
        except Exception:
            continue

    return productos


async def main():
    parser = argparse.ArgumentParser(
        description="Listar todos los productos actualmente publicados en la cuenta de Revolico",
    )
    parser.add_argument("--port", "-p", type=int, default=9222, help="Puerto de Chrome debug (default: 9222)")
    parser.add_argument("--email", "-e", type=str, default="", help="Email de referencia para la cuenta")
    parser.add_argument("--guardar", "-g", action="store_true", help="Guardar la lista en un archivo de texto/JSON")
    parser.add_argument("--salida", "-s", type=str, default="", help="Ruta personalizada del archivo de salida")

    args = parser.parse_args()

    print(f"\n{'═' * 70}")
    print(f"  📋 LISTADOR DE PRODUCTOS PUBLICADOS — REVOLICO")
    print(f"{'═' * 70}")
    print(f"  Puerto Chrome: {args.port}")
    if args.email:
        print(f"  Cuenta:        {args.email}")
    print(f"{'═' * 70}\n")

    async with async_playwright() as p:
        print(f"🔌 Conectando a Chrome en puerto {args.port}...")
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
        except Exception as e:
            print(f"❌ No se pudo conectar a Chrome: {e}")
            print(f"   Asegúrate de que Chrome esté abierto con: google-chrome --remote-debugging-port={args.port}")
            return

        context = browser.contexts[0]

        # Buscar página existente o crear una
        page = None
        for p_curr in context.pages:
            if "revolico.com" in p_curr.url:
                page = p_curr
                break
        if not page:
            page = context.pages[0] if context.pages else await context.new_page()

        # Limpiar huellas
        await limpiar_huellas(page)

        # Detectar cuenta si no se pasó
        email_detectado = await obtener_email_sesion(context) or args.email or "cuenta_desconocida"

        # Navegar a /account/ads si no estamos ahí
        if "revolico.com/account/ads" not in page.url:
            print(f"🌐 Navegando a {URL_CUENTA}...")
            await page.goto(URL_CUENTA, wait_until="domcontentloaded")
            await asyncio.sleep(3)

        # Verificar Cloudflare
        if await detectar_cloudflare(page):
            print("🚨 Cloudflare detectado. Por favor resuélvelo en el navegador...")
            for _ in range(30):
                await asyncio.sleep(2)
                if not await detectar_cloudflare(page):
                    print("✅ Cloudflare resuelto.")
                    break
            else:
                print("❌ Cloudflare no se resolvió a tiempo.")
                return

        # Hacer scroll para cargar todo
        await hacer_scroll_completo(page)

        # Extraer productos
        productos = await extraer_productos(page)

        # Mostrar resultados
        print(f"\n{'─' * 70}")
        print(f"  {'#':<4} {'PRODUCTO':<42} {'PRECIO':<12} {'ID REVOLICO'}")
        print(f"{'─' * 70}")

        for prod in productos:
            num = f"[{prod['numero']}]"
            nom = prod["nombre"][:40]
            prec = prod["precio"] if prod["precio"] else "-"
            pid = prod["id"]
            print(f"  {num:<4} {nom:<42} {prec:<12} {pid}")

        print(f"{'═' * 70}")
        print(f"  📊 TOTAL DE PRODUCTOS PUBLICADOS: {len(productos)}")
        print(f"{'═' * 70}\n")

        # Guardar si se solicitó
        if args.guardar or args.salida:
            fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            email_limpio = email_detectado.replace("@", "_at_").replace(".", "_")

            if args.salida:
                ruta_salida = Path(args.salida)
            else:
                carpeta_salida = ESTADO_DIR / "listados"
                carpeta_salida.mkdir(parents=True, exist_ok=True)
                ruta_salida = carpeta_salida / f"publicados_{email_limpio}_{fecha_str}.txt"

            with open(ruta_salida, "w", encoding="utf-8") as f:
                f.write(f"PRODUCTOS PUBLICADOS EN REVOLICO\n")
                f.write(f"Cuenta: {email_detectado}\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total: {len(productos)}\n\n")
                f.write(f"{'-' * 70}\n")
                for prod in productos:
                    f.write(f"[{prod['numero']:3d}] {prod['nombre']:40s} | {prod['precio']:12s} | ID: {prod['id']} | {prod['url']}\n")

            print(f"💾 Lista guardada exitosamente en: {ruta_salida}\n")


if __name__ == "__main__":
    asyncio.run(main())
