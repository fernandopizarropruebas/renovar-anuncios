# -*- coding: utf-8 -*-
"""
descargar_anuncios.py -- Descarga info y fotos de todos tus anuncios de Revolico
=================================================================================

Requisitos:
    pip3 install playwright httpx
    playwright install chromium

Antes de correr:
    Abre Chrome con debugging activo:
    google-chrome --remote-debugging-port=9222 --user-data-dir=/home/TU_USUARIO/.config/google-chrome-debug
    
    En windows:
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\Users\\TU_USUARIO\\chrome-debug"


Estructura de salida:
    anuncios/
    ├── index.json          ← resumen de todos los anuncios (para verificar_anuncios.py)
    ├── 54272270/
    │   ├── datos.md        ← título, precio, descripción, categoría, fecha
    │   ├── foto_01.jpg
    │   └── foto_02.jpg
    └── 54356411/
        ├── datos.md
        └── foto_01.jpg

Uso:
    python3 descargar_anuncios.py              # descarga solo los nuevos
    python3 descargar_anuncios.py --force      # re-descarga todos aunque ya existan
"""

import asyncio
import re
import json
import os
import sys
from datetime import datetime

import httpx
from playwright.async_api import async_playwright

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR = "anuncios"
FORZAR_ACTUALIZAR = "--force" in sys.argv  # re-descarga aunque ya exista
# ──────────────────────────────────────────────────────────────────────────────


async def cerrar_popup(page):
    """Cierra el popup de 'Destacados' que aparece en las páginas de gestión."""
    for sel in [
        'button[aria-label="Close"]',
        'button[aria-label="Cerrar"]',
        '[data-slot="dialog-close"]',
        '[data-slot="dialog-portal"] button',
    ]:
        btn = await page.query_selector(sel)
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            return True
    return False


async def cargar_todos_los_anuncios(page):
    """
    Scrollea /account hasta el fondo y recoge {ID: url_publica} de cada anuncio.
    Usa lazy loading como la guía indica: 3 scrolls sin cambio = fin de lista.
    """
    print("⬇️  Cargando todos los anuncios (scrolleando)...")
    anuncios = {}    # id -> public_url
    sin_cambios = 0

    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        anuncios_actuales = {}
        for el in links:
            href = await el.get_attribute("href")
            if not href:
                continue
            # href tiene forma: /item/slug-titulo-54272270?token=_
            slug_match = re.search(r'/item/([^?#]+)', href)
            if not slug_match:
                continue
            slug = slug_match.group(1)  # ej: "bucaro-blanco-54272270"
            # El ID son los dígitos al final del slug
            id_match = re.search(r'-(\d{7,9})$', slug)
            if id_match:
                item_id = id_match.group(1)
                public_url = f"https://www.revolico.com/item/{slug}"
                anuncios_actuales[item_id] = public_url
            else:
                # Fallback: /item/54272270 (sin slug de texto)
                id_match2 = re.search(r'^(\d{7,9})$', slug)
                if id_match2:
                    item_id = id_match2.group(1)
                    anuncios_actuales[item_id] = f"https://www.revolico.com/item/{slug}"

        if anuncios_actuales == anuncios:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            anuncios = anuncios_actuales
            print(f"  📦 {len(anuncios)} anuncios cargados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return anuncios


async def extraer_datos_anuncio(page, item_id, public_url):
    """
    Navega a la página pública del anuncio y extrae todos los datos visibles.
    Usa múltiples selectores con fallbacks para cada campo.
    """
    await page.goto(public_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    datos = {
        "id": item_id,
        "url": public_url,
        "descargado": datetime.now().isoformat(),
        "titulo": "",
        "precio": "",
        "categoria": "",
        "descripcion": "",
        "fecha": "",
        "fotos_urls": [],
    }

    # ── Título ────────────────────────────────────────────────────────────────
    for sel in ["h1", "[class*='title'] h1", "[data-testid*='title']"]:
        try:
            el = await page.query_selector(sel)
            if el:
                texto = (await el.inner_text()).strip()
                if texto:
                    datos["titulo"] = texto
                    break
        except Exception:
            pass

    # ── Precio ────────────────────────────────────────────────────────────────
    # Revolico muestra precios como "150 USD" o "5000 CUP"
    for sel in [
        "[class*='price']",
        "[data-testid*='price']",
        "span:has-text('USD')",
        "span:has-text('CUP')",
        "p:has-text('USD')",
        "p:has-text('CUP')",
        "div:has-text('USD')",
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                texto = (await el.inner_text()).strip()
                # Quedarse solo con la parte del precio (evitar textos largos)
                if texto and len(texto) < 60:
                    datos["precio"] = texto
                    break
        except Exception:
            pass

    # ── Descripción ───────────────────────────────────────────────────────────
    for sel in [
        "[class*='description']",
        "[data-testid*='description']",
        "article p",
        "main p",
        "[class*='body']",
        "[class*='content'] p",
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                texto = (await el.inner_text()).strip()
                if texto and len(texto) > 10:
                    datos["descripcion"] = texto
                    break
        except Exception:
            pass

    # ── Categoría (breadcrumbs) ───────────────────────────────────────────────
    try:
        for sel in [
            'nav[aria-label*="bread"] a',
            'nav[aria-label*="Bread"] a',
            '[class*="breadcrumb"] a',
            '[class*="Breadcrumb"] a',
            'nav ol a',
            'nav ul a',
        ]:
            breadcrumbs = await page.query_selector_all(sel)
            if breadcrumbs:
                cats = []
                for b in breadcrumbs:
                    t = (await b.inner_text()).strip()
                    if t and t.lower() not in ["inicio", "home", "revolico", ""]:
                        cats.append(t)
                if cats:
                    datos["categoria"] = " > ".join(cats)
                    break
    except Exception:
        pass

    # ── Fecha de publicación / renovación ─────────────────────────────────────
    try:
        time_el = await page.query_selector("time")
        if time_el:
            dt_attr = await time_el.get_attribute("datetime")
            datos["fecha"] = dt_attr if dt_attr else (await time_el.inner_text()).strip()
    except Exception:
        pass

    # ── Fotos ─────────────────────────────────────────────────────────────────
    # Buscar imágenes del anuncio (evitar logos y íconos pequeños)
    try:
        fotos_encontradas = []
        vistas = set()

        # Intentar primero en galerías/sliders de imágenes
        for sel in [
            "img[src*='revolico']",
            "img[src*='imgix']",
            "img[src*='cloudinary']",
            "img[src*='.jpg']",
            "img[src*='.jpeg']",
            "img[src*='.png']",
            "img[src*='.webp']",
        ]:
            imgs = await page.query_selector_all(sel)
            for img in imgs:
                src = await img.get_attribute("src")
                if not src or src in vistas:
                    continue
                # Filtrar: ignorar imágenes muy pequeñas (logos, íconos)
                try:
                    w = await img.evaluate("el => el.naturalWidth || el.offsetWidth || 0")
                    h = await img.evaluate("el => el.naturalHeight || el.offsetHeight || 0")
                    if w < 80 or h < 80:
                        continue
                except Exception:
                    pass
                # Ignorar imágenes del header/nav (logotipos del sitio)
                try:
                    in_nav = await img.evaluate(
                        "el => !!el.closest('nav, header, footer, [class*=navbar], [class*=Navbar]')"
                    )
                    if in_nav:
                        continue
                except Exception:
                    pass

                vistas.add(src)
                fotos_encontradas.append(src)

            if fotos_encontradas:
                break  # Con el primer selector que da resultados es suficiente

        datos["fotos_urls"] = fotos_encontradas[:20]  # máximo 20 fotos
    except Exception:
        pass

    return datos


def guardar_datos_md(datos, carpeta):
    """Guarda el archivo datos.md con toda la información del anuncio."""
    os.makedirs(carpeta, exist_ok=True)

    n_fotos = len(datos.get("fotos_urls", []))
    lista_fotos = "\n".join(
        [f"- `foto_{i+1:02d}.jpg`" for i in range(n_fotos)]
    ) if n_fotos > 0 else "_Sin fotos_"

    fecha_desc = datos.get("descargado", "")[:19].replace("T", " ")
    fecha_anuncio = datos.get("fecha", "N/A")

    contenido = f"""# {datos.get('titulo', 'Sin título')}

| Campo | Valor |
|---|---|
| **ID** | {datos['id']} |
| **Precio** | {datos.get('precio', 'N/A')} |
| **Categoría** | {datos.get('categoria', 'N/A')} |
| **Fecha anuncio** | {fecha_anuncio} |
| **Descargado** | {fecha_desc} |
| **URL** | [{datos['url']}]({datos['url']}) |

## Descripción

{datos.get('descripcion', '_Sin descripción_')}

## Fotos ({n_fotos})

{lista_fotos}
"""

    with open(os.path.join(carpeta, "datos.md"), "w", encoding="utf-8") as f:
        f.write(contenido)


async def descargar_fotos(fotos_urls, carpeta):
    """Descarga todas las fotos del anuncio a la carpeta dada."""
    descargadas = 0
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
    ) as client:
        for i, url in enumerate(fotos_urls):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    # Detectar extensión por Content-Type
                    ct = resp.headers.get("content-type", "")
                    if "png" in ct:
                        ext = "png"
                    elif "webp" in ct:
                        ext = "webp"
                    elif "jpeg" in ct or "jpg" in ct:
                        ext = "jpg"
                    else:
                        ext = "jpg"  # default

                    ruta = os.path.join(carpeta, f"foto_{i+1:02d}.{ext}")
                    with open(ruta, "wb") as f:
                        f.write(resp.content)
                    descargadas += 1
                else:
                    print(f"      ⚠️  Foto {i+1}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"      ⚠️  Foto {i+1} error: {e}")
    return descargadas


async def main():
    os.makedirs(BASE_DIR, exist_ok=True)

    # Cargar index existente (para no perder datos de anuncios ya guardados)
    index_path = os.path.join(BASE_DIR, "index.json")
    index = {}
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        print(f"📂 Index cargado: {len(index)} anuncios previamente guardados")

    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        print("📄 Navegando a tu cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando que cargue la página (10 segundos)...")
        await asyncio.sleep(10)

        anuncios = await cargar_todos_los_anuncios(page)
        total = len(anuncios)
        print(f"\n📦 Total de anuncios encontrados en Revolico: {total}")

        if total == 0:
            print("⚠️  No se encontraron anuncios. ¿Estás logueado en Revolico?")
            return

        print(f"{'='*55}")
        if FORZAR_ACTUALIZAR:
            print("  Modo: --force (re-descargando todos)")
        else:
            print("  Modo: solo nuevos (usa --force para actualizar todos)")
        print(f"{'='*55}\n")

        nuevos = 0
        saltados = 0
        fallidos = 0

        for i, (item_id, public_url) in enumerate(anuncios.items()):
            carpeta = os.path.join(BASE_DIR, item_id)
            datos_path = os.path.join(carpeta, "datos.md")

            print(f"[{i+1}/{total}] ID {item_id}")

            # Saltar si ya existe y no se fuerza actualización
            if os.path.exists(datos_path) and not FORZAR_ACTUALIZAR:
                print(f"  ⏭️  Ya descargado — saltando (usa --force para actualizar)")
                saltados += 1
                continue

            try:
                datos = await extraer_datos_anuncio(page, item_id, public_url)

                titulo = datos.get("titulo") or "Sin título"
                precio = datos.get("precio") or "Sin precio"
                categoria = datos.get("categoria") or "Sin categoría"
                n_fotos = len(datos.get("fotos_urls", []))

                print(f"  📝 {titulo[:55]}")
                print(f"  💰 {precio}  |  📁 {categoria[:40]}")

                # Guardar datos.md
                guardar_datos_md(datos, carpeta)

                # Descargar fotos
                if n_fotos > 0:
                    desc = await descargar_fotos(datos["fotos_urls"], carpeta)
                    print(f"  🖼️  {desc}/{n_fotos} fotos")
                else:
                    print(f"  🖼️  Sin fotos detectadas")

                # Actualizar index.json
                index[item_id] = {
                    "titulo": titulo,
                    "precio": precio,
                    "categoria": categoria,
                    "url": public_url,
                    "fecha": datos.get("fecha", ""),
                    "descargado": datos["descargado"],
                    "n_fotos": n_fotos,
                }
                # Guardar index tras cada anuncio (por si el script se interrumpe)
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index, f, ensure_ascii=False, indent=2)

                nuevos += 1
                await asyncio.sleep(2)  # Pausa para no disparar Cloudflare

            except Exception as e:
                print(f"  ❌ Error: {e}")
                fallidos += 1
                await asyncio.sleep(2)
                continue

    # ── Resumen final ─────────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*55}")
    print(f"  📥 Descargados este run : {nuevos}")
    print(f"  ⏭️  Saltados (ya tenías) : {saltados}")
    print(f"  ❌ Fallidos             : {fallidos}")
    print(f"  📦 Total en Revolico    : {total}")
    print(f"  📂 Carpeta de datos     : ./{BASE_DIR}/")
    print(f"  📋 Index actualizado    : ./{BASE_DIR}/index.json")
    print(f"{'='*55}")
    print("\n✅ ¡Listo!")


asyncio.run(main())
