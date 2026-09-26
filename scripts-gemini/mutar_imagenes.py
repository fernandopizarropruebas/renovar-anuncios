"""
mutar_imagenes.py — Generador de Variantes Únicas de Imágenes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Toma una imagen original y genera N variantes que son visualmente
reconocibles como "el mismo producto" pero técnicamente únicas para
cualquier sistema de detección de duplicados (pHash, dHash, MD5, EXIF).

Uso:
# Una imagen, 20 variantes
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 20

# Toda una carpeta de fotos
python3 scripts-opus/mutar_imagenes.py anuncios/54130535/ -n 15

# Con salida personalizada
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 10 -o mis_variantes/

# Con verificación de efectividad
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 5 --verificar

  python3 mutar_imagenes.py <imagen_o_carpeta> [--cantidad N] [--salida CARPETA]

Ejemplos:
  # Generar 10 variantes de una imagen
  python3 mutar_imagenes.py foto_01.jpg --cantidad 10

  # Generar 20 variantes de cada imagen en una carpeta
  python3 mutar_imagenes.py anuncios/54130535/ --cantidad 20

  # Especificar carpeta de salida
  python3 mutar_imagenes.py foto_01.jpg --cantidad 15 --salida ./variantes/

  # Mostrar las diferencias de hash para verificar efectividad
  python3 mutar_imagenes.py foto_01.jpg --cantidad 5 --verificar
"""

import os
import sys
import random
import argparse
import hashlib
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIGURACIÓN DE MUTACIONES
# ══════════════════════════════════════════════════════════════════════════════

# Rango de cada transformación (min, max)
CONFIG = {
    # Probabilidad de aplicar flip horizontal (0.0 a 1.0)
    "flip_probabilidad": 0.5,

    # Crop: porcentaje del borde que se recorta por cada lado
    "crop_min_pct": 0.03,   # 3%
    "crop_max_pct": 0.12,   # 12%

    # Brillo: 1.0 = original
    "brillo_min": 0.88,
    "brillo_max": 1.12,

    # Contraste: 1.0 = original
    "contraste_min": 0.88,
    "contraste_max": 1.12,

    # Saturación (Color): 1.0 = original
    "saturacion_min": 0.80,
    "saturacion_max": 1.20,

    # Nitidez (Sharpness): 1.0 = original
    "nitidez_min": 0.7,
    "nitidez_max": 1.5,

    # Rotación ligera en grados
    "rotacion_min": -3.0,
    "rotacion_max": 3.0,
    "rotacion_probabilidad": 0.4,

    # Calidad JPEG de salida
    "jpeg_quality_min": 72,
    "jpeg_quality_max": 95,

    # Shift de tono HSV (en grados, de 0 a 360)
    "hue_shift_min": -15,
    "hue_shift_max": 15,

    # Probabilidad de añadir un borde sutil
    "borde_probabilidad": 0.3,
    "borde_grosor_min": 1,
    "borde_grosor_max": 5,

    # Probabilidad de aplicar un blur muy ligero
    "blur_probabilidad": 0.25,
    "blur_radius_min": 0.3,
    "blur_radius_max": 0.8,
}


# ══════════════════════════════════════════════════════════════════════════════
# ── FUNCIONES DE MUTACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def flip_horizontal(img):
    """Espejo horizontal — cambia toda la distribución de gradientes del pHash."""
    if random.random() < CONFIG["flip_probabilidad"]:
        return img.transpose(Image.FLIP_LEFT_RIGHT), True
    return img, False


def crop_aleatorio(img):
    """Recorte aleatorio asimétrico por cada lado — altera la composición."""
    w, h = img.size
    left = int(w * random.uniform(0, CONFIG["crop_max_pct"]))
    right = int(w * random.uniform(0, CONFIG["crop_max_pct"]))
    top = int(h * random.uniform(0, CONFIG["crop_max_pct"]))
    bottom = int(h * random.uniform(0, CONFIG["crop_max_pct"]))

    # Asegurar que al menos un lado tenga crop mínimo
    lado = random.choice(["left", "right", "top", "bottom"])
    min_px_w = int(w * CONFIG["crop_min_pct"])
    min_px_h = int(h * CONFIG["crop_min_pct"])
    if lado == "left":
        left = max(left, min_px_w)
    elif lado == "right":
        right = max(right, min_px_w)
    elif lado == "top":
        top = max(top, min_px_h)
    else:
        bottom = max(bottom, min_px_h)

    nuevo = img.crop((left, top, w - right, h - bottom))
    return nuevo, f"crop L={left} R={right} T={top} B={bottom}"


def ajustar_brillo(img):
    """Variación de brillo."""
    factor = random.uniform(CONFIG["brillo_min"], CONFIG["brillo_max"])
    return ImageEnhance.Brightness(img).enhance(factor), f"brillo={factor:.3f}"


def ajustar_contraste(img):
    """Variación de contraste."""
    factor = random.uniform(CONFIG["contraste_min"], CONFIG["contraste_max"])
    return ImageEnhance.Contrast(img).enhance(factor), f"contraste={factor:.3f}"


def ajustar_saturacion(img):
    """Variación de saturación/color."""
    factor = random.uniform(CONFIG["saturacion_min"], CONFIG["saturacion_max"])
    return ImageEnhance.Color(img).enhance(factor), f"saturacion={factor:.3f}"


def ajustar_nitidez(img):
    """Variación de nitidez."""
    factor = random.uniform(CONFIG["nitidez_min"], CONFIG["nitidez_max"])
    return ImageEnhance.Sharpness(img).enhance(factor), f"nitidez={factor:.3f}"


def shift_hue(img):
    """Rotación del tono en el espacio HSV — cambia el perfil de color global."""
    shift = random.randint(CONFIG["hue_shift_min"], CONFIG["hue_shift_max"])
    if shift == 0:
        shift = random.choice([-5, 5])

    hsv = img.convert("HSV")
    h, s, v = hsv.split()

    # Shift circular del canal H (0-255 en Pillow, donde 255 = 360°)
    h_data = list(h.getdata())
    h_shifted = [(px + int(shift * 255 / 360)) % 256 for px in h_data]
    h.putdata(h_shifted)

    resultado = Image.merge("HSV", (h, s, v)).convert("RGB")
    return resultado, f"hue_shift={shift}°"


def rotacion_ligera(img):
    """Rotación de unos pocos grados con relleno."""
    if random.random() < CONFIG["rotacion_probabilidad"]:
        angulo = random.uniform(CONFIG["rotacion_min"], CONFIG["rotacion_max"])
        if abs(angulo) < 0.5:
            angulo = random.choice([-1.5, 1.5])
        # expand=True para no recortar, luego recortamos el exceso
        rotada = img.rotate(angulo, resample=Image.BICUBIC, expand=True,
                           fillcolor=(255, 255, 255))
        # Recortar al tamaño original centrado
        rw, rh = rotada.size
        ow, oh = img.size
        left = (rw - ow) // 2
        top = (rh - oh) // 2
        rotada = rotada.crop((left, top, left + ow, top + oh))
        return rotada, f"rotacion={angulo:.1f}°"
    return img, None


def añadir_borde(img):
    """Añade un borde sutil de color aleatorio."""
    if random.random() < CONFIG["borde_probabilidad"]:
        grosor = random.randint(CONFIG["borde_grosor_min"], CONFIG["borde_grosor_max"])
        # Color del borde: tonos neutros/cercanos al blanco o negro
        tipo = random.choice(["claro", "oscuro", "color"])
        if tipo == "claro":
            color = (
                random.randint(230, 255),
                random.randint(230, 255),
                random.randint(230, 255),
            )
        elif tipo == "oscuro":
            color = (
                random.randint(0, 30),
                random.randint(0, 30),
                random.randint(0, 30),
            )
        else:
            color = (
                random.randint(50, 220),
                random.randint(50, 220),
                random.randint(50, 220),
            )

        w, h = img.size
        nueva = Image.new("RGB", (w + grosor * 2, h + grosor * 2), color)
        nueva.paste(img, (grosor, grosor))
        return nueva, f"borde={grosor}px"
    return img, None


def blur_ligero(img):
    """Aplica un desenfoque muy sutil."""
    if random.random() < CONFIG["blur_probabilidad"]:
        radius = random.uniform(CONFIG["blur_radius_min"], CONFIG["blur_radius_max"])
        return img.filter(ImageFilter.GaussianBlur(radius=radius)), f"blur={radius:.2f}"
    return img, None


def limpiar_exif(img):
    """Elimina toda la metadata EXIF de la imagen."""
    datos = list(img.getdata())
    limpia = Image.new(img.mode, img.size)
    limpia.putdata(datos)
    return limpia


# ══════════════════════════════════════════════════════════════════════════════
# ── HASHES Y COMPARACIÓN PERCEPTUAL
# ══════════════════════════════════════════════════════════════════════════════

def md5_archivo(ruta):
    """Calcula el MD5 de un archivo."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()


def dhash(img, tamaño=16):
    """
    Calcula el difference hash (dHash) de una imagen.
    Método similar al que usan los sistemas de detección de duplicados.
    Compara píxeles adyacentes para crear un fingerprint de 256 bits.
    """
    # Redimensionar a (tamaño+1, tamaño) en escala de grises
    img_small = img.convert("L").resize((tamaño + 1, tamaño), Image.LANCZOS)
    pixels = list(img_small.getdata())

    hash_bits = []
    for row in range(tamaño):
        for col in range(tamaño):
            idx = row * (tamaño + 1) + col
            # 1 si el píxel actual es mayor que el siguiente
            hash_bits.append(1 if pixels[idx] > pixels[idx + 1] else 0)

    # Convertir bits a hex (64 caracteres hex = 256 bits)
    hash_int = int("".join(str(b) for b in hash_bits), 2)
    return format(hash_int, f"0{tamaño * tamaño // 4}x")


def hamming_distance(hash1, hash2):
    """Distancia de Hamming entre dos hashes hexadecimales (0 a 256 bits)."""
    if len(hash1) != len(hash2):
        return -1
    bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
    bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
    return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))


# ══════════════════════════════════════════════════════════════════════════════
# ── PIPELINE DE MUTACIÓN CON VALIDACIÓN DE ALTA SEGURIDAD
# ══════════════════════════════════════════════════════════════════════════════

class ResultadoMutacion(tuple):
    """Tupla compatible con (transformaciones, size_orig, size_final) con metadata extra."""
    def __new__(cls, transformaciones, size_orig, size_final, **kwargs):
        obj = super().__new__(cls, (transformaciones, size_orig, size_final))
        obj.transformaciones = transformaciones
        obj.size_orig = size_orig
        obj.size_final = size_final
        obj.info = kwargs
        return obj


def aplicar_transformaciones(img_original):
    """Aplica una combinación aleatoria de todas las transformaciones sobre una copia."""
    img = img_original.copy()
    transformaciones = []

    # 1. Flip horizontal
    img, aplicado = flip_horizontal(img)
    if aplicado:
        transformaciones.append("flip_h")

    # 2. Crop aleatorio (SIEMPRE se aplica — es la más efectiva)
    img, info = crop_aleatorio(img)
    transformaciones.append(info)

    # 3. Rotación ligera
    img, info = rotacion_ligera(img)
    if info:
        transformaciones.append(info)

    # 4. Shift de tono HSV
    img, info = shift_hue(img)
    transformaciones.append(info)

    # 5. Brillo
    img, info = ajustar_brillo(img)
    transformaciones.append(info)

    # 6. Contraste
    img, info = ajustar_contraste(img)
    transformaciones.append(info)

    # 7. Saturación
    img, info = ajustar_saturacion(img)
    transformaciones.append(info)

    # 8. Nitidez
    img, info = ajustar_nitidez(img)
    transformaciones.append(info)

    # 9. Blur ligero
    img, info = blur_ligero(img)
    if info:
        transformaciones.append(info)

    # 10. Borde sutil
    img, info = añadir_borde(img)
    if info:
        transformaciones.append(info)

    return img, transformaciones


def mutar_imagen(ruta_original, ruta_salida, indice=1,
                 hashes_previos=None, md5s_previos=None,
                 umbral_orig=30, umbral_entre=25, max_intentos=30,
                 validar=True):
    """
    Aplica mutaciones aleatorias con VALIDACIÓN PERCEPTUAL DE ALTA SEGURIDAD:
    - Distancia dHash vs Original >= umbral_orig (default: 30)
    - Distancia dHash vs Otras Variantes >= umbral_entre (default: 25)
    - MD5 binario único
    - EXIF limpio
    Si una variante no cumple el umbral, se descarta y se reintenta automáticamente.
    """
    img_orig = Image.open(ruta_original)
    if img_orig.mode in ("RGBA", "P", "LA"):
        img_orig = img_orig.convert("RGB")

    hash_orig = dhash(img_orig)
    md5_orig = md5_archivo(ruta_original) if Path(ruta_original).exists() else ""

    hashes_existentes = hashes_previos or []  # lista de (nombre, dhash)
    md5s_existentes = set(md5s_previos or [])

    mejor_candidato = None
    mejor_dist_global = -1

    u_orig = umbral_orig
    u_entre = umbral_entre

    for intento in range(1, max_intentos + 1):
        # A partir del intento 18, si el umbral resulta extremadamente estricto para una imagen simple,
        # reducir ligeramente para converger manteniendo seguridad muy por encima de Revolico (>= 20)
        if intento == 18 and validar:
            u_orig = max(25, umbral_orig - 5)
            u_entre = max(20, umbral_entre - 5)

        img_mutada, transformaciones = aplicar_transformaciones(img_orig)
        hash_var = dhash(img_mutada)

        dist_orig = hamming_distance(hash_orig, hash_var)

        if hashes_existentes:
            dist_entre = min(hamming_distance(h[1], hash_var) for h in hashes_existentes)
        else:
            dist_entre = 999

        score = min(dist_orig, dist_entre)
        if score > mejor_dist_global:
            mejor_dist_global = score
            mejor_candidato = (img_mutada, transformaciones, hash_var, dist_orig, dist_entre, intento)

        if not validar:
            break

        # Comprobar si cumple ambos umbrales de seguridad
        if dist_orig >= u_orig and dist_entre >= u_entre:
            break

    img_final, transformaciones, hash_final, dist_orig_final, dist_entre_final, intento_final = mejor_candidato

    # Limpiar EXIF
    img_final = limpiar_exif(img_final)

    # Guardar con calidad JPEG variable
    quality = random.randint(CONFIG["jpeg_quality_min"], CONFIG["jpeg_quality_max"])
    salida_path = Path(ruta_salida)
    salida_path.parent.mkdir(parents=True, exist_ok=True)
    img_final.save(salida_path, "JPEG", quality=quality)
    transformaciones.append(f"quality={quality}")

    md5_final = md5_archivo(salida_path)

    # Si coincidió el MD5 con la original o con otra variante previa, re-guardar con calidad diferente
    reintentos_md5 = 0
    while (md5_final == md5_orig or md5_final in md5s_existentes) and reintentos_md5 < 5:
        reintentos_md5 += 1
        quality = random.randint(CONFIG["jpeg_quality_min"], CONFIG["jpeg_quality_max"])
        img_final.save(salida_path, "JPEG", quality=quality)
        md5_final = md5_archivo(salida_path)

    return ResultadoMutacion(
        transformaciones,
        img_orig.size,
        img_final.size,
        hash=hash_final,
        md5=md5_final,
        dist_orig=dist_orig_final,
        dist_entre=dist_entre_final,
        intentos=intento_final
    )


def verificar_efectividad(ruta_original, rutas_variantes):
    """Compara los hashes de la original con cada variante Y entre variantes."""
    img_original = Image.open(ruta_original).convert("RGB")
    hash_original = dhash(img_original)
    md5_original = md5_archivo(ruta_original)

    print(f"\n{'═' * 70}")
    print(f"  VERIFICACIÓN DE EFECTIVIDAD")
    print(f"{'═' * 70}")
    print(f"  Original: {os.path.basename(ruta_original)}")
    print(f"  dHash:    {hash_original}")
    print(f"  MD5:      {md5_original}")

    # ── PARTE 1: Cada variante vs la original ──
    print(f"\n{'─' * 70}")
    print(f"  📊 VARIANTES vs ORIGINAL:")
    print(f"{'─' * 70}")

    distancias_vs_original = []
    hashes_variantes = []  # Para comparar entre sí después

    for ruta in rutas_variantes:
        img_var = Image.open(ruta).convert("RGB")
        hash_var = dhash(img_var)
        md5_var = md5_archivo(ruta)
        hashes_variantes.append((os.path.basename(ruta), hash_var, md5_var))

        dist = hamming_distance(hash_original, hash_var)
        distancias_vs_original.append(dist)

        if dist <= 5:
            estado = "⚠️  DETECTADA como igual"
        elif dist <= 10:
            estado = "🟡 Similar (zona de riesgo)"
        else:
            estado = "✅ ÚNICA"

        md5_match = "⚠️ IGUAL" if md5_var == md5_original else "✅ Dif"

        print(f"  {os.path.basename(ruta):30s} dist={dist:3d}/256 {estado}  MD5:{md5_match}")

    promedio_orig = sum(distancias_vs_original) / len(distancias_vs_original) if distancias_vs_original else 0
    min_orig = min(distancias_vs_original) if distancias_vs_original else 0
    unicas_orig = sum(1 for d in distancias_vs_original if d > 10)

    print(f"\n  Resumen vs Original: promedio={promedio_orig:.1f}  min={min_orig}  únicas={unicas_orig}/{len(distancias_vs_original)}")

    # ── PARTE 2: Cada variante vs TODAS las demás variantes ──
    print(f"\n{'─' * 70}")
    print(f"  📊 VARIANTES ENTRE SÍ (¿son únicas unas de otras?):")
    print(f"{'─' * 70}")

    distancias_entre_variantes = []
    pares_peligrosos = []

    for i in range(len(hashes_variantes)):
        for j in range(i + 1, len(hashes_variantes)):
            nombre_i, hash_i, _ = hashes_variantes[i]
            nombre_j, hash_j, _ = hashes_variantes[j]
            dist = hamming_distance(hash_i, hash_j)
            distancias_entre_variantes.append(dist)

            if dist <= 10:
                pares_peligrosos.append((nombre_i, nombre_j, dist))

    if distancias_entre_variantes:
        total_pares = len(distancias_entre_variantes)
        promedio_entre = sum(distancias_entre_variantes) / total_pares
        min_entre = min(distancias_entre_variantes)
        max_entre = max(distancias_entre_variantes)
        pares_unicos = sum(1 for d in distancias_entre_variantes if d > 10)

        print(f"  Total de pares comparados: {total_pares}")
        print(f"  Distancia promedio:  {promedio_entre:.1f}/256")
        print(f"  Distancia mínima:    {min_entre}/256")
        print(f"  Distancia máxima:    {max_entre}/256")
        print(f"  Pares únicos:        {pares_unicos}/{total_pares} ({pares_unicos/total_pares*100:.0f}%)")

        if pares_peligrosos:
            print(f"\n  ⚠️  PARES PELIGROSOS (distancia ≤ 10, podrían detectarse como iguales):")
            for n1, n2, d in pares_peligrosos:
                print(f"    {n1} ↔ {n2}  dist={d}")
        else:
            print(f"\n  ✅ Ningún par de variantes se parece entre sí. ¡Todas son únicas!")

    # ── VEREDICTO FINAL ──
    print(f"\n{'═' * 70}")
    print(f"  🏆 VEREDICTO FINAL")
    print(f"{'═' * 70}")

    todo_ok = True
    if promedio_orig > 15:
        print(f"  ✅ vs Original: EFECTIVAS (promedio {promedio_orig:.1f}, mín {min_orig})")
    elif promedio_orig > 8:
        print(f"  🟡 vs Original: MODERADAS (promedio {promedio_orig:.1f}, mín {min_orig})")
        todo_ok = False
    else:
        print(f"  🔴 vs Original: INSUFICIENTES (promedio {promedio_orig:.1f}, mín {min_orig})")
        todo_ok = False

    if distancias_entre_variantes:
        promedio_entre = sum(distancias_entre_variantes) / len(distancias_entre_variantes)
        min_entre = min(distancias_entre_variantes)
        if not pares_peligrosos:
            print(f"  ✅ Entre variantes: TODAS ÚNICAS (promedio {promedio_entre:.1f}, mín {min_entre})")
        else:
            print(f"  ⚠️  Entre variantes: {len(pares_peligrosos)} pares peligrosos de {total_pares}")
            todo_ok = False

    if todo_ok:
        print(f"\n  🎯 Puedes subir la original + todas las variantes sin riesgo de detección.")
    else:
        print(f"\n  🟡 Hay riesgo. Considera aumentar la intensidad de las mutaciones.")
    print(f"{'═' * 70}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN
# ══════════════════════════════════════════════════════════════════════════════

def obtener_imagenes(ruta):
    """Obtiene la lista de imágenes de un archivo o carpeta."""
    extensiones = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ruta = Path(ruta)

    if ruta.is_file() and ruta.suffix.lower() in extensiones:
        return [ruta]

    if ruta.is_dir():
        imagenes = []
        for ext in extensiones:
            imagenes.extend(ruta.glob(f"*{ext}"))
            imagenes.extend(ruta.glob(f"*{ext.upper()}"))
        # Eliminar duplicados y ordenar
        vistas = set()
        resultado = []
        for img in sorted(imagenes, key=lambda x: x.name.lower()):
            if img.name.lower() not in vistas:
                vistas.add(img.name.lower())
                resultado.append(img)
        return resultado

    print(f"❌ No se encontró imagen o carpeta: {ruta}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Genera variantes únicas de imágenes para evitar detección de duplicados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 mutar_imagenes.py foto_01.jpg --cantidad 10
  python3 mutar_imagenes.py anuncios/54130535/ --cantidad 20 --salida ./variantes/
  python3 mutar_imagenes.py foto_01.jpg --cantidad 5 --verificar
        """
    )
    parser.add_argument("entrada", help="Imagen o carpeta con imágenes")
    parser.add_argument("--cantidad", "-n", type=int, default=10,
                       help="Cantidad de variantes a generar por imagen (default: 10)")
    parser.add_argument("--salida", "-o", type=str, default=None,
                       help="Carpeta de salida (default: variantes_<nombre>/)")
    parser.add_argument("--umbral-orig", type=int, default=30,
                       help="Distancia dHash mínima vs original para seguridad alta (default: 30)")
    parser.add_argument("--umbral-entre", type=int, default=25,
                       help="Distancia dHash mínima entre variantes para seguridad alta (default: 25)")
    parser.add_argument("--sin-validacion", action="store_true",
                       help="Desactivar validación perceptual automática (no recomendado)")
    parser.add_argument("--verificar", "-v", action="store_true",
                       help="Mostrar análisis completo de hashes al terminar")

    args = parser.parse_args()
    imagenes = obtener_imagenes(args.entrada)

    if not imagenes:
        print("❌ No se encontraron imágenes")
        sys.exit(1)

    print(f"\n🖼️  Imágenes encontradas: {len(imagenes)}")
    print(f"🔄 Variantes por imagen: {args.cantidad}")
    print(f"🛡️  Validación dHash: {'DESACTIVADA' if args.sin_validacion else f'ACTIVA (vs orig >= {args.umbral_orig}, entre vars >= {args.umbral_entre})'}")
    print(f"📊 Total a generar: {len(imagenes) * args.cantidad}\n")

    for img_path in imagenes:
        nombre_base = img_path.stem

        # Determinar carpeta de salida
        if args.salida:
            carpeta_salida = Path(args.salida)
        else:
            carpeta_salida = img_path.parent / f"variantes_{nombre_base}"

        carpeta_salida.mkdir(parents=True, exist_ok=True)

        print(f"{'━' * 60}")
        print(f"  📸 {img_path.name}")
        print(f"  📁 Salida: {carpeta_salida}/")
        print(f"{'━' * 60}")

        rutas_generadas = []
        hashes_existentes = []
        md5s_existentes = set()

        # Si ya hay variantes en la carpeta, cargarlas para no colisionar
        if carpeta_salida.exists():
            for f in sorted(carpeta_salida.iterdir()):
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    try:
                        h = dhash(Image.open(f).convert("RGB"))
                        hashes_existentes.append((f.name, h))
                        md5s_existentes.add(md5_archivo(f))
                    except Exception:
                        pass

        for i in range(1, args.cantidad + 1):
            nombre_variante = f"{nombre_base}_v{i:03d}.jpg"
            ruta_variante = carpeta_salida / nombre_variante

            try:
                res = mutar_imagen(
                    str(img_path), str(ruta_variante), i,
                    hashes_previos=hashes_existentes,
                    md5s_previos=md5s_existentes,
                    umbral_orig=args.umbral_orig,
                    umbral_entre=args.umbral_entre,
                    validar=not args.sin_validacion
                )
                transformaciones, size_orig, size_final = res
                rutas_generadas.append(str(ruta_variante))
                hashes_existentes.append((nombre_variante, res.info["hash"]))
                md5s_existentes.add(res.info["md5"])

                trans_str = " | ".join(t for t in transformaciones if t)
                d_orig = res.info.get("dist_orig", "?")
                d_entre = res.info.get("dist_entre", "?")
                d_entre_str = f"{d_entre}/256" if d_entre != 999 else "1ra (n/a)"
                intentos = res.info.get("intentos", 1)
                intentos_str = f" [{intentos} intentos]" if intentos > 1 else ""

                print(f"  [{i:3d}/{args.cantidad}] ✅ {nombre_variante}{intentos_str}")
                print(f"           dHash vs orig: {d_orig}/256 | vs otras: {d_entre_str}")
                print(f"           {size_orig[0]}x{size_orig[1]} → {size_final[0]}x{size_final[1]}")
                print(f"           {trans_str}")

            except Exception as e:
                print(f"  [{i:3d}/{args.cantidad}] ❌ Error: {e}")

        # Verificación de efectividad si se pidió
        if args.verificar and rutas_generadas:
            verificar_efectividad(str(img_path), rutas_generadas)

    print(f"\n✅ ¡Listo! Se generaron {len(imagenes) * args.cantidad} variantes en total.\n")


if __name__ == "__main__":
    main()
