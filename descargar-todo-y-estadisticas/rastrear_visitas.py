"""
rastrear_visitas.py — Registra y compara las visitas diarias de tus anuncios
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Las visitas están en la PÁGINA PÚBLICA del anuncio, debajo del precio:
  "Hace 5 horas · 2 visitas"

Estructura de salida:
  visitas/historial.json      ← todos los registros históricos
  visitas/ultimo_reporte.txt  ← reporte del último run

Uso:
    python3 rastrear_visitas.py
"""

import asyncio
import re
import json
import os
from datetime import date
from playwright.async_api import async_playwright

BASE_DIR       = "visitas"
HISTORIAL_FILE = os.path.join(BASE_DIR, "historial.json")
REPORTE_FILE   = os.path.join(BASE_DIR, "ultimo_reporte.txt")
HOY            = date.today().isoformat()


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORIAL
# ══════════════════════════════════════════════════════════════════════════════

def cargar_historial():
    os.makedirs(BASE_DIR, exist_ok=True)
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_historial(h):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, ensure_ascii=False, indent=2)

def registro_de_hoy(registros):
    for r in registros:
        if r["fecha"] == HOY:
            return r
    return None

def registro_anterior(registros):
    anteriores = [r for r in registros if r["fecha"] < HOY and r["visitas"] is not None]
    return max(anteriores, key=lambda r: r["fecha"]) if anteriores else None


# ══════════════════════════════════════════════════════════════════════════════
#  NAVEGACIÓN
# ══════════════════════════════════════════════════════════════════════════════

async def cargar_anuncios_desde_account(page):
    """
    Scrollea /account y devuelve {item_id: {titulo, public_url}}.
    El href tiene el slug completo: /item/juegos-de-muebles-54938179?token=_
    """
    print("⬇️  Cargando lista de anuncios...")
    anuncios = {}
    sin_cambios = 0

    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        actuales = {}
        for el in links:
            href = await el.get_attribute("href")
            if not href:
                continue
            # Extraer slug completo: juegos-de-muebles-54938179
            slug_match = re.search(r'/item/([^?#]+)', href)
            if not slug_match:
                continue
            slug = slug_match.group(1)
            # ID = últimos 7-9 dígitos al final del slug
            id_match = re.search(r'-(\d{7,9})$', slug)
            if not id_match:
                continue
            item_id = id_match.group(1)
            public_url = f"https://www.revolico.com/item/{slug}"

            # Título: texto del card menos el botón "Gestionar"
            try:
                card_text = await el.evaluate(
                    "el => el.closest('article, li, [class*=card], [class*=item]')?.innerText || ''"
                )
                titulo = card_text.replace("Gestionar", "").strip().split("\n")[0][:60] or item_id
            except Exception:
                titulo = item_id

            actuales[item_id] = {"titulo": titulo, "public_url": public_url}

        if actuales == anuncios:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            anuncios = actuales
            print(f"  📦 {len(anuncios)} anuncios cargados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return anuncios


async def extraer_visitas_pagina_publica(page, public_url):
    """
    Va a la URL pública del anuncio y extrae el número de visitas.
    El texto en la página tiene el formato: "Hace 5 horas · 2 visitas"
    Patrón confirmado por diagnóstico: r'(\\d+)\\s*visitas?'
    """
    await page.goto(public_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    try:
        texto = await page.evaluate("() => document.body.innerText")
        match = re.search(r'(\d+)\s*visitas?', texto, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTE
# ══════════════════════════════════════════════════════════════════════════════

def imprimir_reporte(historial):
    # Ordenar por visitas de hoy, de mayor a menor
    def visitas_hoy_de(datos):
        reg = registro_de_hoy(datos.get("registros", []))
        return reg["visitas"] if reg and reg["visitas"] else -1

    items = sorted(historial.items(), key=lambda x: visitas_hoy_de(x[1]), reverse=True)

    col_titulo  = 44
    col_visitas =  8
    col_ganadas =  8

    sep = "━" * (col_titulo + col_visitas + col_ganadas + 6)
    print(f"\n{sep}")
    print(f"  📊  VISITAS DEL DÍA — {HOY}")
    print(sep)
    print(f"  {'ANUNCIO':<{col_titulo}} {'VISITAS':>{col_visitas}}  {'GANADAS':>{col_ganadas}}")
    print(f"  {'─' * (col_titulo + col_visitas + col_ganadas + 4)}")

    lineas_txt = []

    for item_id, datos in items:
        titulo    = datos.get("titulo", item_id)[:col_titulo]
        registros = datos.get("registros", [])
        reg_hoy   = registro_de_hoy(registros)
        reg_ant   = registro_anterior(registros)

        v_hoy = reg_hoy["visitas"] if reg_hoy else None
        v_ant = reg_ant["visitas"] if reg_ant else None

        if v_hoy is None:
            vis_str  = f"{'N/A':>{col_visitas}}"
            gan_str  = f"{'':>{col_ganadas}}"
            gan_txt  = "N/A"
        else:
            vis_str = f"{v_hoy:>{col_visitas}}"
            if v_ant is not None:
                diff = v_hoy - v_ant
                if diff > 0:
                    gan_color = f"\033[92m▲ +{diff}\033[0m"
                    gan_txt   = f"+{diff}"
                elif diff < 0:
                    gan_color = f"\033[91m▼ {diff}\033[0m"
                    gan_txt   = str(diff)
                else:
                    gan_color = "→  0"
                    gan_txt   = "0"
                gan_str = f"  {gan_color}"
            else:
                gan_str = "  (nuevo)"
                gan_txt = "nuevo"

        print(f"  {titulo:<{col_titulo}}{vis_str}{gan_str}")
        lineas_txt.append(f"{titulo:<{col_titulo}}{v_hoy if v_hoy is not None else 'N/A':>{col_visitas}}  {gan_txt:>{col_ganadas}}")

    print(sep)

    # Guardar reporte plano
    with open(REPORTE_FILE, "w", encoding="utf-8") as f:
        f.write(f"VISITAS — {HOY}\n")
        f.write("=" * (col_titulo + col_visitas + col_ganadas + 6) + "\n")
        f.write(f"{'ANUNCIO':<{col_titulo}} {'VISITAS':>{col_visitas}}  {'GANADAS':>{col_ganadas}}\n")
        f.write("-" * (col_titulo + col_visitas + col_ganadas + 6) + "\n")
        for l in lineas_txt:
            f.write(l + "\n")
        f.write("=" * (col_titulo + col_visitas + col_ganadas + 6) + "\n")

    print(f"  📄  Reporte guardado: {REPORTE_FILE}")
    print(f"  💾  Historial:        {HISTORIAL_FILE}")


def imprimir_historial_top(historial, n=5):
    """Muestra la evolución día a día de los N anuncios con más visitas."""
    top = sorted(
        historial.items(),
        key=lambda x: max((r["visitas"] or 0 for r in x[1].get("registros", [])), default=0),
        reverse=True
    )[:n]

    if not top:
        return

    print(f"\n{'━'*65}")
    print(f"  📈  HISTORIAL — top {n} anuncios")
    print(f"{'━'*65}")

    for item_id, datos in top:
        titulo    = datos.get("titulo", item_id)[:55]
        registros = sorted(datos.get("registros", []), key=lambda r: r["fecha"])
        if not registros:
            continue
        print(f"\n  {titulo}")
        print(f"  {'─'*50}")
        ant = None
        for r in registros:
            v = r["visitas"]
            fecha = r["fecha"]
            if v is None:
                print(f"    {fecha}  →   N/A")
                continue
            if ant is not None:
                diff = v - ant
                if diff > 0:
                    flecha = f"\033[92m▲ +{diff}\033[0m"
                elif diff < 0:
                    flecha = f"\033[91m▼ {diff}\033[0m"
                else:
                    flecha = "→ sin cambio"
                print(f"    {fecha}  →  {v:>6} visitas   {flecha}")
            else:
                print(f"    {fecha}  →  {v:>6} visitas   (primer registro)")
            ant = v


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    historial = cargar_historial()

    async with async_playwright() as p:
        print("🔌 Conectando a Chrome...")
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        print("✅ Conectado\n")

        print("📄 Navegando a tu cuenta de Revolico...")
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        print("⏳ Esperando carga (10 segundos)...")
        await asyncio.sleep(10)

        anuncios = await cargar_anuncios_desde_account(page)
        total = len(anuncios)

        if total == 0:
            print("⚠️  No se encontraron anuncios. ¿Estás logueado?")
            return

        print(f"\n📦 {total} anuncios. Leyendo visitas desde páginas públicas...\n")
        print(f"{'─'*65}")

        sin_datos = []

        for i, (item_id, info) in enumerate(anuncios.items()):
            titulo     = info["titulo"]
            public_url = info["public_url"]

            # Inicializar en historial si es nuevo
            if item_id not in historial:
                historial[item_id] = {"titulo": titulo, "registros": []}
            # Actualizar título si lo tenemos mejor ahora
            if titulo and titulo != item_id:
                historial[item_id]["titulo"] = titulo

            registros = historial[item_id].setdefault("registros", [])

            # No repetir si ya corrió hoy
            if registro_de_hoy(registros):
                v = registro_de_hoy(registros)["visitas"]
                print(f"[{i+1}/{total}] {titulo[:48]:<50}  ⏭  ya registrado ({v} vis.)")
                continue

            print(f"[{i+1}/{total}] {titulo[:50]}", end="", flush=True)

            visitas = await extraer_visitas_pagina_publica(page, public_url)

            if visitas is not None:
                reg_ant = registro_anterior(registros)
                if reg_ant:
                    diff = visitas - reg_ant["visitas"]
                    diff_str = f"   \033[92m▲ +{diff}\033[0m" if diff > 0 else (f"   \033[91m▼ {diff}\033[0m" if diff < 0 else "   → sin cambio")
                else:
                    diff_str = "   (primer registro)"
                print(f"  →  {visitas} visitas{diff_str}")
            else:
                print(f"  →  ⚠️  no encontrado")
                sin_datos.append(item_id)

            registros.append({"fecha": HOY, "visitas": visitas})
            guardar_historial(historial)   # guardar tras cada anuncio
            await asyncio.sleep(2)

    # ── Reporte final ─────────────────────────────────────────────────────────
    imprimir_reporte(historial)
    imprimir_historial_top(historial, n=5)

    if sin_datos:
        print(f"\n  ⚠️  {len(sin_datos)} anuncio(s) sin visitas detectadas: {', '.join(sin_datos)}")

    print("\n✅ ¡Listo!")


asyncio.run(main())
