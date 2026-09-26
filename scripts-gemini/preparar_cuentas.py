"""
preparar_cuentas.py — Organizador de Productos por Cuenta
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Este script es el PASO 2 del flujo. Toma la carpeta de productos
con sus imágenes y descripciones, y prepara todo lo necesario para
que el publicador sepa qué publicar en cada cuenta.

Estructura esperada de entrada (productos/):
  productos/
  ├── buros/
  │   ├── producto.json        ← {nombre, precio, moneda, categoria}
  │   ├── descripcion_base.txt ← Descripción base del producto
  │   └── imagenes/
  │       ├── img_01.jpg
  │       ├── img_02.jpg
  │       └── ...
  ├── colchonetas/
  │   ├── producto.json
  │   ├── descripcion_base.txt
  │   └── imagenes/
  └── ...

Lo que genera (estado/):
  estado/
  ├── registro_global.json     ← Mapeo maestro de todo
  └── cuentas/
      ├── cuenta1@gmail.com.json
      └── ...

Uso:
  # Preparar asignación para una nueva cuenta
  python3 preparar_cuentas.py asignar --email cuenta1@gmail.com

  # Ver estado actual de todas las cuentas
  python3 preparar_cuentas.py estado

  # Ver qué falta por publicar en una cuenta
  python3 preparar_cuentas.py pendientes --email cuenta1@gmail.com

  # Generar variantes de imágenes para todos los productos
  python3 preparar_cuentas.py generar-imagenes --cantidad 20

  # Generar variantes de descripción para todos los productos
  python3 preparar_cuentas.py generar-descripciones --cantidad 20

  # Inicializar la estructura de productos desde la carpeta anuncios/ existente
  python3 preparar_cuentas.py importar-anuncios
"""

import os
import sys
import json
import shutil
import random
import re
import argparse
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent  # raíz del proyecto
PRODUCTOS_DIR = BASE_DIR / "productos"
ESTADO_DIR = BASE_DIR / "estado"
CUENTAS_DIR = ESTADO_DIR / "cuentas"
ANUNCIOS_DIR = BASE_DIR / "anuncios"  # carpeta vieja para importar
DESCRIPCIONES_DIR = Path(__file__).parent / "descripciones"  # banco editable


# ══════════════════════════════════════════════════════════════════════════════
# ── UTILIDADES
# ══════════════════════════════════════════════════════════════════════════════

def asegurar_carpetas():
    """Crea las carpetas base si no existen."""
    PRODUCTOS_DIR.mkdir(parents=True, exist_ok=True)
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    CUENTAS_DIR.mkdir(parents=True, exist_ok=True)


def cargar_json(ruta, default=None):
    """Carga un archivo JSON o devuelve el default."""
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def guardar_json(ruta, datos):
    """Guarda un diccionario como JSON."""
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def listar_productos():
    """Lista todos los productos disponibles."""
    if not PRODUCTOS_DIR.exists():
        return []
    productos = []
    for d in sorted(PRODUCTOS_DIR.iterdir()):
        if d.is_dir() and (d / "producto.json").exists():
            productos.append(d.name)
    return productos


def cargar_producto(nombre):
    """Carga los datos de un producto."""
    ruta = PRODUCTOS_DIR / nombre / "producto.json"
    return cargar_json(str(ruta))


def listar_imagenes_originales_producto(nombre):
    """Lista SOLO las imágenes originales de un producto (no variantes)."""
    carpeta = PRODUCTOS_DIR / nombre / "imagenes"
    if not carpeta.exists():
        return []
    extensiones = {".jpg", ".jpeg", ".png", ".webp"}
    imagenes = []
    for f in sorted(carpeta.iterdir()):
        if f.is_file() and f.suffix.lower() in extensiones:
            # Solo excluir si es explícitamente una variante con formato _vXXX
            if not re.search(r"_v\d{3}$", f.stem):
                imagenes.append(f.name)
    return imagenes


def listar_variantes_de_imagen(nombre, imagen_original):
    """Lista las variantes generadas de una imagen original específica."""
    stem = Path(imagen_original).stem  # ej: "foto_01"
    carpeta_variantes = PRODUCTOS_DIR / nombre / "imagenes" / f"variantes_{stem}"
    if not carpeta_variantes.exists():
        return []
    extensiones = {".jpg", ".jpeg", ".png", ".webp"}
    variantes = []
    for f in sorted(carpeta_variantes.iterdir()):
        if f.is_file() and f.suffix.lower() in extensiones:
            variantes.append(f"variantes_{stem}/{f.name}")
    return variantes


def listar_sets_imagenes_producto(nombre):
    """
    Para un producto con N fotos originales, lista los 'sets' disponibles.
    Cada set es un grupo de variantes (una por cada foto original) que se
    publican juntas en un solo anuncio.
    
    Retorna lista de listas: [[variante_foto1, variante_foto2], ...]
    """
    originales = listar_imagenes_originales_producto(nombre)
    if not originales:
        return []
    
    # Obtener variantes de cada original
    variantes_por_original = {}
    for orig in originales:
        variantes = listar_variantes_de_imagen(nombre, orig)
        if not variantes:
            # Si no hay variantes generadas para alguna de las imágenes originales,
            # NO usamos la original cruda para evitar que Revolico detecte duplicados.
            # Se requiere que todas las imágenes originales tengan variantes.
            return []
        variantes_por_original[orig] = variantes
    
    # Construir sets: cada set tiene 1 variante de cada original
    # La cantidad de sets posibles = mínimo de variantes entre todas las originales
    min_variantes = min(len(v) for v in variantes_por_original.values())
    
    sets = []
    for i in range(min_variantes):
        un_set = []
        for orig in originales:
            un_set.append(variantes_por_original[orig][i])
        sets.append(un_set)
    
    return sets


def listar_descripciones_producto(nombre):
    """Lista las variantes de descripción de un producto."""
    carpeta = PRODUCTOS_DIR / nombre / "descripciones"
    if not carpeta.exists():
        # Si no hay carpeta de variantes, verificar si hay descripcion_base
        base = PRODUCTOS_DIR / nombre / "descripcion_base.txt"
        if base.exists():
            return ["descripcion_base.txt"]
        return []
    descs = []
    for f in sorted(carpeta.iterdir()):
        if f.suffix == ".txt":
            descs.append(f.name)
    return descs


def cargar_cuenta(email):
    """Carga el JSON de estado de una cuenta."""
    ruta = CUENTAS_DIR / f"{email}.json"
    return cargar_json(str(ruta), {
        "email": email,
        "alias": None,
        "fecha_creacion": datetime.now().isoformat(),
        "publicaciones": []
    })


def guardar_cuenta(email, datos):
    """Guarda el JSON de estado de una cuenta."""
    ruta = CUENTAS_DIR / f"{email}.json"
    guardar_json(str(ruta), datos)


def obtener_registro_global():
    """Carga el registro global."""
    ruta = ESTADO_DIR / "registro_global.json"
    return cargar_json(str(ruta), {
        "cuentas_registradas": [],
        "ultima_actualizacion": None,
        "estadisticas": {}
    })


def guardar_registro_global(registro):
    """Guarda el registro global."""
    registro["ultima_actualizacion"] = datetime.now().isoformat()
    ruta = ESTADO_DIR / "registro_global.json"
    guardar_json(str(ruta), registro)


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: importar-anuncios
# ══════════════════════════════════════════════════════════════════════════════

def parsear_datos_md(ruta_md):
    """Parsea un datos.md existente al formato producto.json."""
    with open(ruta_md, "r", encoding="utf-8") as f:
        contenido = f.read()

    datos = {"nombre": "", "precio": "", "moneda": "USD", "categoria": []}

    m = re.search(r'^#\s+(.+)$', contenido, re.MULTILINE)
    if m:
        datos["nombre"] = m.group(1).strip()

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

    descripcion = ""
    m = re.search(r'##\s+Descripci[oó]n(.*?)(?=\n#|\Z)', contenido, re.DOTALL)
    if m:
        raw_desc = m.group(1).strip()
        if "## Fotos" in raw_desc:
            raw_desc = raw_desc.split("## Fotos")[0].strip()
        lineas = raw_desc.split("\n")
        lineas_reales = [l for l in lineas if not re.match(r'\s*-\s*`foto_\d+\.\w+`', l)
                        and l.strip() not in ("_Sin descripción_", "")]
        descripcion = "\n".join(lineas_reales).strip()

    return datos, descripcion


def cmd_importar_anuncios(args):
    """Importa los anuncios existentes a la nueva estructura productos/."""
    asegurar_carpetas()

    if not ANUNCIOS_DIR.exists():
        print(f"❌ No existe la carpeta {ANUNCIOS_DIR}")
        return

    # Cargar index.json si existe para obtener nombres legibles
    index_path = ANUNCIOS_DIR / "index.json"
    index = cargar_json(str(index_path), [])

    # Crear mapa de ID → título del index
    titulo_por_id = {}
    if isinstance(index, list):
        for item in index:
            if isinstance(item, dict):
                titulo_por_id[str(item.get("id", ""))] = item.get("titulo", "")

    importados = 0
    errores = 0

    for carpeta in sorted(ANUNCIOS_DIR.iterdir()):
        if not carpeta.is_dir() or not carpeta.name.isdigit():
            continue

        datos_md = carpeta / "datos.md"
        if not datos_md.exists():
            continue

        # Parsear datos
        datos, descripcion = parsear_datos_md(str(datos_md))
        nombre_producto = datos["nombre"] or titulo_por_id.get(carpeta.name, carpeta.name)

        # Crear nombre de carpeta limpio
        nombre_carpeta = re.sub(r'[^\w\s-]', '', nombre_producto.lower())
        nombre_carpeta = re.sub(r'\s+', '-', nombre_carpeta.strip())
        if not nombre_carpeta:
            nombre_carpeta = f"producto-{carpeta.name}"

        # Si ya existe, añadir ID para distinguir
        destino = PRODUCTOS_DIR / nombre_carpeta
        if destino.exists():
            nombre_carpeta = f"{nombre_carpeta}-{carpeta.name}"
            destino = PRODUCTOS_DIR / nombre_carpeta

        try:
            destino.mkdir(parents=True, exist_ok=True)
            (destino / "imagenes").mkdir(exist_ok=True)

            # Guardar producto.json
            guardar_json(str(destino / "producto.json"), {
                "nombre": nombre_producto,
                "precio": datos["precio"],
                "moneda": datos["moneda"],
                "categoria": datos["categoria"],
                "id_original": carpeta.name
            })

            # Guardar descripción base
            if descripcion:
                with open(destino / "descripcion_base.txt", "w", encoding="utf-8") as f:
                    f.write(descripcion)

            # Copiar fotos
            extensiones = {".jpg", ".jpeg", ".png", ".webp"}
            fotos_copiadas = 0
            for foto in sorted(carpeta.iterdir()):
                if foto.suffix.lower() in extensiones:
                    shutil.copy2(str(foto), str(destino / "imagenes" / foto.name))
                    fotos_copiadas += 1

            print(f"  ✅ {nombre_producto:40s} → {nombre_carpeta}/ ({fotos_copiadas} fotos)")
            importados += 1

        except Exception as e:
            print(f"  ❌ {carpeta.name}: {e}")
            errores += 1

    print(f"\n{'═' * 60}")
    print(f"  Importados: {importados}  |  Errores: {errores}")
    print(f"  Carpeta: {PRODUCTOS_DIR}/")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: generar-imagenes
# ══════════════════════════════════════════════════════════════════════════════

def cmd_generar_imagenes(args):
    """Genera variantes de imágenes para todos los productos usando mutar_imagenes.py."""
    import subprocess

    productos = listar_productos()
    if not productos:
        print("❌ No hay productos en productos/. Usa 'importar-anuncios' primero.")
        return

    script_mutar = Path(__file__).parent / "mutar_imagenes.py"
    if not script_mutar.exists():
        print(f"❌ No se encuentra {script_mutar}")
        return

    print(f"\n🖼️  Generando {args.cantidad} variantes por imagen para {len(productos)} productos\n")

    for producto in productos:
        carpeta_imgs = PRODUCTOS_DIR / producto / "imagenes"
        if not carpeta_imgs.exists():
            print(f"  ⚠️  {producto}: sin carpeta de imágenes")
            continue

        # Contar imágenes originales (no carpetas de variantes)
        originales = [f for f in sorted(carpeta_imgs.iterdir())
                     if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                     and not re.search(r"_v\d{3}$", f.stem)]

        if not originales:
            print(f"  ⚠️  {producto}: sin imágenes originales")
            continue

        print(f"  📦 {producto} ({len(originales)} originales)")

        for img in originales:
            salida = carpeta_imgs / f"variantes_{img.stem}"

            # Saltar si ya están generadas
            if salida.exists() and len(list(salida.iterdir())) >= args.cantidad:
                print(f"    ⏭️  {img.name}: ya tiene {len(list(salida.iterdir()))} variantes")
                continue

            cmd = [
                sys.executable, str(script_mutar),
                str(img),
                "--cantidad", str(args.cantidad),
                "--salida", str(salida)
            ]
            resultado = subprocess.run(cmd, capture_output=True, text=True)
            if resultado.returncode == 0:
                generadas = len(list(salida.iterdir())) if salida.exists() else 0
                print(f"    ✅ {img.name}: {generadas} variantes generadas")
            else:
                print(f"    ❌ {img.name}: {resultado.stderr[:200]}")

    print(f"\n✅ Generación de imágenes completada.")


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: generar-descripciones
# ══════════════════════════════════════════════════════════════════════════════

def cargar_sinonimos():
    """Carga sinónimos desde el archivo editable scripts-opus/descripciones/sinonimos.txt"""
    ruta = DESCRIPCIONES_DIR / "sinonimos.txt"
    sinonimos = {}
    if not ruta.exists():
        return sinonimos
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "=" in linea:
                palabra, alternativas = linea.split("=", 1)
                alts = [a.strip() for a in alternativas.split(",") if a.strip()]
                if alts:
                    sinonimos[palabra.strip().lower()] = alts
    return sinonimos


def cargar_frases_cierre():
    """Carga frases de cierre desde scripts-opus/descripciones/frases_cierre.txt"""
    ruta = DESCRIPCIONES_DIR / "frases_cierre.txt"
    frases = []
    if not ruta.exists():
        return ["Escríbame para más información."]
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                frases.append(linea)
    return frases if frases else ["Escríbame para más información."]


def variar_descripcion(descripcion_base, indice):
    """Genera una variante de la descripción base usando archivos editables."""
    sinonimos = cargar_sinonimos()
    frases_cierre = cargar_frases_cierre()

    if not descripcion_base.strip():
        return random.choice(frases_cierre)

    desc = descripcion_base

    # 1. Reemplazar sinónimos aleatoriamente
    for palabra, alternativas in sinonimos.items():
        if palabra.lower() in desc.lower():
            if random.random() < 0.5:
                patron = re.compile(re.escape(palabra), re.IGNORECASE)
                desc = patron.sub(random.choice(alternativas), desc, count=1)

    # 2. Reordenar oraciones si hay varias
    oraciones = [s.strip() for s in desc.split(".") if s.strip()]
    if len(oraciones) > 2 and random.random() < 0.4:
        primera = oraciones[0]
        medio = oraciones[1:-1]
        ultima = oraciones[-1]
        random.shuffle(medio)
        oraciones = [primera] + medio + [ultima]
        desc = ". ".join(oraciones) + "."

    # 3. Añadir frase de cierre aleatoria
    frases = random.sample(frases_cierre, k=min(random.randint(1, 2), len(frases_cierre)))
    desc = desc.rstrip() + "\n" + " ".join(frases)

    # 4. Variación de espaciado/saltos de línea
    if random.random() < 0.3:
        desc = desc.replace("\n\n", "\n")
    if random.random() < 0.3:
        desc = desc.replace("\n", "\n\n", 1)

    return desc.strip()


def cmd_generar_descripciones(args):
    """Genera variantes de descripción para todos los productos."""
    productos = listar_productos()
    if not productos:
        print("❌ No hay productos en productos/. Usa 'importar-anuncios' primero.")
        return

    print(f"\n📝 Generando {args.cantidad} descripciones por producto para {len(productos)} productos\n")

    for producto in productos:
        base_path = PRODUCTOS_DIR / producto / "descripcion_base.txt"
        desc_dir = PRODUCTOS_DIR / producto / "descripciones"

        descripcion_base = ""
        if base_path.exists():
            with open(base_path, "r", encoding="utf-8") as f:
                descripcion_base = f.read().strip()

        # Saltar si ya están generadas
        if desc_dir.exists() and len(list(desc_dir.glob("*.txt"))) >= args.cantidad:
            existentes = len(list(desc_dir.glob("*.txt")))
            print(f"  ⏭️  {producto}: ya tiene {existentes} descripciones")
            continue

        desc_dir.mkdir(parents=True, exist_ok=True)

        for i in range(1, args.cantidad + 1):
            variante = variar_descripcion(descripcion_base, i)
            ruta = desc_dir / f"variante_{i:03d}.txt"
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(variante)

        print(f"  ✅ {producto}: {args.cantidad} descripciones generadas")

    print(f"\n✅ Generación de descripciones completada.")


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: asignar
# ══════════════════════════════════════════════════════════════════════════════

def cmd_asignar(args):
    """
    Asigna productos a una cuenta, eligiendo un SET de imágenes (una variante
    por cada foto original) y una descripción no usada EN NINGUNA cuenta.
    """
    asegurar_carpetas()

    email = args.email
    productos = listar_productos()

    if not productos:
        print("❌ No hay productos. Usa 'importar-anuncios' y 'generar-imagenes' primero.")
        return

    # Cargar cuenta (existente o nueva)
    cuenta = cargar_cuenta(email)

    # Determinar alias
    registro = obtener_registro_global()
    if email not in registro["cuentas_registradas"]:
        num = len(registro["cuentas_registradas"]) + 1
        cuenta["alias"] = f"cuenta-{num}"
        registro["cuentas_registradas"].append(email)
        guardar_registro_global(registro)

    # Obtener lo que ya tiene asignado/publicado esta cuenta
    productos_en_cuenta = set()
    for pub in cuenta.get("publicaciones", []):
        productos_en_cuenta.add(pub["producto"])

    # Recopilar GLOBALMENTE: qué sets de imágenes y descripciones ya se usaron
    # Una imagen quemada en CUALQUIER cuenta no se puede reusar en NINGUNA
    sets_globales_usados = {}   # producto → set de tuplas de imágenes usadas
    imgs_globales_usadas = {}   # producto → set de imágenes individuales usadas
    descs_globales_usadas = {}  # producto → set de descripciones usadas

    if CUENTAS_DIR.exists():
        for archivo_cuenta in CUENTAS_DIR.iterdir():
            if archivo_cuenta.suffix == ".json":
                otra_cuenta = cargar_json(str(archivo_cuenta))
                for pub in otra_cuenta.get("publicaciones", []):
                    prod = pub["producto"]
                    if prod not in sets_globales_usados:
                        sets_globales_usados[prod] = set()
                        imgs_globales_usadas[prod] = set()
                    # Imágenes: guardar tanto el set completo como cada foto individual
                    imgs = pub.get("imagenes_usadas", [])
                    if imgs:
                        sets_globales_usados[prod].add(tuple(imgs))
                        for img in imgs:
                            imgs_globales_usadas[prod].add(img)
                    # Compatibilidad con formato viejo (imagen_usada singular)
                    elif pub.get("imagen_usada"):
                        sets_globales_usados[prod].add((pub["imagen_usada"],))
                        imgs_globales_usadas[prod].add(pub["imagen_usada"])
                    # Descripciones
                    if prod not in descs_globales_usadas:
                        descs_globales_usadas[prod] = set()
                    descs_globales_usadas[prod].add(pub.get("descripcion_usada", ""))

    # Asignar un producto por cada producto disponible
    asignaciones_nuevas = []
    ya_tenia = 0
    sin_recursos = 0

    for producto in productos:
        if producto in productos_en_cuenta:
            ya_tenia += 1
            continue

        # Obtener sets de imágenes disponibles (un set = una variante de cada foto original)
        todos_sets = listar_sets_imagenes_producto(producto)
        usados_sets = sets_globales_usados.get(producto, set())
        usadas_imgs = imgs_globales_usadas.get(producto, set())

        # Filtrar sets que no hayan sido usados como set ni contengan fotos ya usadas globalmente
        disponibles = [
            s for s in todos_sets
            if tuple(s) not in usados_sets and not any(img in usadas_imgs for img in s)
        ]

        if not disponibles:
            if todos_sets:
                print(f"  ⚠️  {producto}: sin sets de imágenes disponibles ({len(todos_sets)} generados, todos quemados)")
            else:
                print(f"  ⚠️  {producto}: sin sets generados (falta generar variantes con 'generar-imagenes')")
            sin_recursos += 1
            continue

        set_elegido = disponibles[0]  # Primer set disponible
        sets_globales_usados.setdefault(producto, set()).add(tuple(set_elegido))
        for img in set_elegido:
            imgs_globales_usadas.setdefault(producto, set()).add(img)

        # Buscar descripción no usada GLOBALMENTE
        todas_descs = listar_descripciones_producto(producto)
        usadas_d = descs_globales_usadas.get(producto, set())
        disponibles_d = [d for d in todas_descs if d not in usadas_d]

        if disponibles_d:
            desc_elegida = disponibles_d[0]
            descs_globales_usadas.setdefault(producto, set()).add(desc_elegida)
        elif todas_descs:
            # Si no hay más descripciones únicas, advertir
            print(f"  🟡 {producto}: descripciones agotadas, reutilizando una")
            desc_elegida = random.choice(todas_descs)
        else:
            desc_elegida = "descripcion_base.txt"

        asignaciones_nuevas.append({
            "producto": producto,
            "imagenes_usadas": set_elegido,  # LISTA de imágenes (una por cada foto original)
            "descripcion_usada": desc_elegida,
            "fecha_asignacion": datetime.now().isoformat(),
            "estado": "pendiente",
            "url_revolico": None
        })

    # Guardar
    cuenta["publicaciones"].extend(asignaciones_nuevas)
    guardar_cuenta(email, cuenta)

    print(f"\n{'═' * 60}")
    print(f"  📧 Cuenta: {email} ({cuenta['alias']})")
    print(f"{'═' * 60}")
    print(f"  Ya tenía asignados: {ya_tenia} productos")
    print(f"  Nuevos asignados:   {len(asignaciones_nuevas)} productos")
    if sin_recursos:
        print(f"  Sin recursos:       {sin_recursos} productos (imágenes agotadas)")
    print(f"  Total pendientes:   {sum(1 for p in cuenta['publicaciones'] if p['estado'] == 'pendiente')}")
    print(f"{'─' * 60}")

    for a in asignaciones_nuevas[:10]:
        n_fotos = len(a['imagenes_usadas'])
        print(f"  📦 {a['producto']:30s} 🖼️ {n_fotos} foto(s)  📝 {a['descripcion_usada']}")

    if len(asignaciones_nuevas) > 10:
        print(f"  ... y {len(asignaciones_nuevas) - 10} más")

    print(f"{'═' * 60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: estado
# ══════════════════════════════════════════════════════════════════════════════

def cmd_estado(args):
    """Muestra el estado actual de todas las cuentas."""
    asegurar_carpetas()

    productos = listar_productos()
    print(f"\n{'═' * 60}")
    print(f"  📊 ESTADO DEL SISTEMA")
    print(f"{'═' * 60}")
    print(f"  Productos disponibles: {len(productos)}")

    # Contar imágenes totales
    total_imgs = 0
    for p in productos:
        total_imgs += len(listar_imagenes_originales_producto(p))
    print(f"  Imágenes originales:   {total_imgs}")

    # Listar cuentas
    print(f"\n{'─' * 60}")
    print(f"  📧 CUENTAS REGISTRADAS:")
    print(f"{'─' * 60}")

    if not CUENTAS_DIR.exists() or not list(CUENTAS_DIR.glob("*.json")):
        print("  (ninguna cuenta registrada)")
    else:
        for archivo in sorted(CUENTAS_DIR.glob("*.json")):
            cuenta = cargar_json(str(archivo))
            email = cuenta.get("email", archivo.stem)
            alias = cuenta.get("alias", "?")
            pubs = cuenta.get("publicaciones", [])
            pendientes = sum(1 for p in pubs if p.get("estado") == "pendiente")
            publicados = sum(1 for p in pubs if p.get("estado") == "publicado")
            fallidos = sum(1 for p in pubs if p.get("estado") == "fallido")

            print(f"  {alias:12s} {email}")
            print(f"               pendientes={pendientes}  publicados={publicados}  fallidos={fallidos}")

    print(f"{'═' * 60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ── COMANDO: pendientes
# ══════════════════════════════════════════════════════════════════════════════

def cmd_pendientes(args):
    """Muestra los productos pendientes de publicar para una cuenta."""
    email = args.email
    ruta = CUENTAS_DIR / f"{email}.json"

    if not ruta.exists():
        print(f"❌ No existe la cuenta {email}. Usa 'asignar --email {email}' primero.")
        return

    cuenta = cargar_json(str(ruta))
    pubs = cuenta.get("publicaciones", [])
    pendientes = [p for p in pubs if p.get("estado") == "pendiente"]

    print(f"\n{'═' * 60}")
    print(f"  📧 {email} ({cuenta.get('alias', '?')})")
    print(f"  Pendientes: {len(pendientes)}/{len(pubs)}")
    print(f"{'─' * 60}")

    for i, p in enumerate(pendientes, 1):
        datos = cargar_producto(p["producto"])
        nombre = datos.get("nombre", p["producto"]) if datos else p["producto"]
        precio = datos.get("precio", "?") if datos else "?"
        moneda = datos.get("moneda", "") if datos else ""
        print(f"  {i:3d}. {nombre:35s} {precio} {moneda}")
        imgs = p.get('imagenes_usadas', [p.get('imagen_usada', '?')])
        print(f"       🖼️ {len(imgs)} foto(s)  📝 {p['descripcion_usada']}")

    print(f"{'═' * 60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Sistema de organización de productos por cuenta para Revolico",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="comando", help="Comando a ejecutar")

    # importar-anuncios
    sp = subparsers.add_parser("importar-anuncios",
                               help="Importar anuncios existentes a la estructura productos/")
    sp.set_defaults(func=cmd_importar_anuncios)

    # generar-imagenes
    sp = subparsers.add_parser("generar-imagenes",
                               help="Generar variantes de imágenes para todos los productos")
    sp.add_argument("--cantidad", "-n", type=int, default=20)
    sp.set_defaults(func=cmd_generar_imagenes)

    # generar-descripciones
    sp = subparsers.add_parser("generar-descripciones",
                               help="Generar variantes de descripción para todos los productos")
    sp.add_argument("--cantidad", "-n", type=int, default=20)
    sp.set_defaults(func=cmd_generar_descripciones)

    # asignar
    sp = subparsers.add_parser("asignar",
                               help="Asignar productos a una cuenta")
    sp.add_argument("--email", "-e", required=True, help="Email de la cuenta")
    sp.set_defaults(func=cmd_asignar)

    # estado
    sp = subparsers.add_parser("estado",
                               help="Ver estado actual de todas las cuentas")
    sp.set_defaults(func=cmd_estado)

    # pendientes
    sp = subparsers.add_parser("pendientes",
                               help="Ver productos pendientes de una cuenta")
    sp.add_argument("--email", "-e", required=True, help="Email de la cuenta")
    sp.set_defaults(func=cmd_pendientes)

    args = parser.parse_args()

    if not args.comando:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
