"""
verificar_anuncios.py — Compara tus anuncios guardados vs los activos en Revolico
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Qué hace:
  1. Lee los anuncios guardados en la carpeta anuncios/ (index.json)
  2. Entra a Revolico y carga todos los anuncios activos
  3. Compara y muestra:
     ✅ Anuncios que siguen activos y los tienes guardados
     🗑️  Anuncios que Revolico BORRÓ (están en local pero no en web)
     🆕  Anuncios nuevos en web que aún no descargaste

Requisitos:
    pip3 install playwright
    playwright install chromium

Antes de correr:
    Abre Chrome con debugging activo:
    google-chrome --remote-debugging-port=9222 \
      --user-data-dir=/home/TU_USUARIO/.config/google-chrome-debug

Uso:
    python3 verificar_anuncios.py
"""

import asyncio
import re
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR = "anuncios"
# ──────────────────────────────────────────────────────────────────────────────


async def cargar_ids_desde_web(page):
    """
    Scrollea /account y recoge todos los IDs de anuncios activos en Revolico.
    Idéntica lógica al script de renovar_anuncios.py (ya probada y funcional).
    """
    print("⬇️  Cargando anuncios activos en Revolico (scrolleando)...")
    ids_vistos = set()
    sin_cambios = 0

    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()
        for el in links:
            href = await el.get_attribute("href")
            if not href:
                continue
            # Extraer ID del slug: /item/titulo-del-anuncio-54272270?token=_
            match = re.search(r'-(\d{7,9})\?', href)
            if match:
                ids_actuales.add(match.group(1))
            else:
                # Fallback: /item/54272270
                match2 = re.search(r'/item/(\d{7,9})', href)
                if match2:
                    ids_actuales.add(match2.group(1))

        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
            print(f"  📦 {len(ids_vistos)} anuncios encontrados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return ids_vistos


def cargar_ids_locales():
    """
    Lee los IDs guardados localmente desde index.json o carpetas.
    Devuelve (set_de_ids, dict_index).
    """
    index_path = os.path.join(BASE_DIR, "index.json")

    # Preferir index.json si existe (tiene más info)
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        return set(index.keys()), index

    # Fallback: leer carpetas de la estructura anuncios/{ID}/
    if os.path.isdir(BASE_DIR):
        ids = set(
            d for d in os.listdir(BASE_DIR)
            if os.path.isdir(os.path.join(BASE_DIR, d)) and d.isdigit()
        )
        return ids, {}

    return set(), {}


def formatear_info_anuncio(item_id, index):
    """Devuelve una línea de texto con info del anuncio para mostrar en el reporte."""
    info = index.get(item_id, {})
    titulo = info.get("titulo", "Sin título")[:50]
    precio = info.get("precio", "")
    fecha_desc = info.get("descargado", "")[:10]
    partes = [f"[{item_id}]", titulo]
    if precio:
        partes.append(f"— {precio}")
    if fecha_desc:
        partes.append(f"(guardado: {fecha_desc})")
    return " ".join(partes)


async def main():
    # ── 1. Cargar datos locales ────────────────────────────────────────────────
    if not os.path.isdir(BASE_DIR):
        print(f"❌ No existe la carpeta '{BASE_DIR}/'")
        print(f"   Ejecuta primero: python3 descargar_anuncios.py")
        return

    ids_locales, index = cargar_ids_locales()

    if not ids_locales:
        print(f"⚠️  No se encontraron anuncios guardados en '{BASE_DIR}/'")
        print(f"   Ejecuta primero: python3 descargar_anuncios.py")
        return

    print(f"📂 Anuncios guardados localmente: {len(ids_locales)}")

    # ── 2. Cargar IDs activos en Revolico ─────────────────────────────────────
    async with async_playwright() as p:
        print("\n🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        print("📄 Navegando a tu cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando que cargue la página (10 segundos)...")
        await asyncio.sleep(10)

        ids_web = await cargar_ids_desde_web(page)

    print(f"\n🌐 Anuncios activos en Revolico: {len(ids_web)}")

    # ── 3. Comparar ────────────────────────────────────────────────────────────
    borrados       = ids_locales - ids_web    # estaban en local, desaparecieron de web
    nuevos_en_web  = ids_web - ids_locales    # en web pero no descargados aún
    ok             = ids_locales & ids_web    # en ambos lados

    hora = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{'━'*60}")
    print(f"  📊  RESULTADO DE VERIFICACIÓN  —  {hora}")
    print(f"{'━'*60}")
    print(f"  ✅  Activos y guardados         : {len(ok)}")
    print(f"  🗑️   BORRADOS de Revolico        : {len(borrados)}")
    print(f"  🆕  En web, sin descargar aún   : {len(nuevos_en_web)}")
    print(f"{'━'*60}")

    # ── Detalle de borrados ────────────────────────────────────────────────────
    if borrados:
        print(f"\n🗑️  ANUNCIOS QUE REVOLICO TE BORRÓ ({len(borrados)}):")
        print(f"{'─'*60}")
        for item_id in sorted(borrados):
            print(f"  • {formatear_info_anuncio(item_id, index)}")
            carpeta = os.path.join(BASE_DIR, item_id)
            if os.path.exists(carpeta):
                print(f"    → Copia guardada en: {carpeta}/")
        print()
        print("  💡 Tienes los datos guardados localmente.")
        print("     Si quieres volver a publicar, están en la carpeta de cada ID.")

    # ── Detalle de nuevos sin descargar ───────────────────────────────────────
    if nuevos_en_web:
        print(f"\n🆕  ANUNCIOS EN WEB QUE AÚN NO DESCARGASTE ({len(nuevos_en_web)}):")
        print(f"{'─'*60}")
        for item_id in sorted(nuevos_en_web):
            print(f"  • ID {item_id}")
        print()
        print("  💡 Ejecuta descargar_anuncios.py para descargarlos.")

    # ── Todo bien ─────────────────────────────────────────────────────────────
    if not borrados and not nuevos_en_web:
        print("\n  🎉 ¡Todo en orden! Ningún anuncio fue borrado.")

    # ── Guardar reporte en archivo ─────────────────────────────────────────────
    reporte_path = os.path.join(BASE_DIR, "ultimo_reporte.txt")
    with open(reporte_path, "w", encoding="utf-8") as f:
        f.write(f"Verificación: {hora}\n")
        f.write(f"Guardados localmente : {len(ids_locales)}\n")
        f.write(f"Activos en Revolico  : {len(ids_web)}\n")
        f.write(f"OK                   : {len(ok)}\n")
        f.write(f"BORRADOS             : {len(borrados)}\n")
        f.write(f"Sin descargar        : {len(nuevos_en_web)}\n\n")

        if borrados:
            f.write("BORRADOS:\n")
            for item_id in sorted(borrados):
                f.write(f"  {formatear_info_anuncio(item_id, index)}\n")
            f.write("\n")

        if nuevos_en_web:
            f.write("SIN DESCARGAR:\n")
            for item_id in sorted(nuevos_en_web):
                f.write(f"  ID {item_id}\n")

    print(f"\n{'━'*60}")
    print(f"  📄 Reporte guardado en: {reporte_path}")
    print(f"{'━'*60}")


asyncio.run(main())
