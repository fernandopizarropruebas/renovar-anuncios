# Plan 6 — Bug y Mejoras en Publicación de Anuncios

**Fuente:** [publicar.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/bugs/publicar/publicar.md)  
**Documentación base:** [documentacion_v1.0.0](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.0.0/documentacion_v1.0.0/README.md)  
**Scripts a modificar:** EXCLUSIVAMENTE en `scripts-gemini/` (NO tocar `scripts-opus/`)  
**Estado:** Planificado  

---

## 1. Diagnóstico y Causa Raíz

### 1.1. ¿Por qué ocurrió el error `⚠️ Espejo: sin sets de imágenes disponibles (todos quemados)`?

Al ejecutar `python3 scripts-gemini/preparar_cuentas.py asignar --email alejandroantigravity1@gmail.com`, aparecieron los siguientes avisos:
- `⚠️ Espejo: sin sets de imágenes disponibles (todos quemados)`
- `⚠️ Espejos: sin sets de imágenes disponibles (todos quemados)`
- `⚠️ Lampara: sin sets de imágenes disponibles (todos quemados)`

A pesar de haber solicitado generar 10 variantes por imagen con `generar-imagenes -n 10`.

#### Causa Raíz Técnica Identificada:
1. **Filtro erróneo de imágenes originales en `preparar_cuentas.py`**:
   ```python
   originales = [f for f in carpeta_imgs.iterdir()
                if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                and "_v" not in f.stem]
   ```
   El script intentaba filtrar posibles variantes buscando la subcadena `"_v"` en el nombre del archivo.
   
2. **Nombres de imágenes generadas por Gemini con `_v`**:
   Las imágenes originales de esos 3 productos contenían `_v`:
   - `productos/Espejo/imagenes/Gemini_Generated_Image_vtq153vtq153vtq1.jpg` (`_vtq` contiene `_v`)
   - `productos/Espejos/imagenes/Gemini_Generated_Image_vl81hhvl81hhvl81.jpg` (`_vl81` contiene `_v`)
   - `productos/Lampara/imagenes/Gemini_Generated_Image_vddqrvvddqrvvddq.jpg` (`_vddq` contiene `_v`)

3. **Efecto dominó en la creación de sets**:
   - `generar-imagenes` ignoró estas 3 fotos originales y **nunca generó su carpeta de variantes**.
   - En `listar_sets_imagenes_producto`:
     ```python
     if not variantes:
         variantes = [orig]  # Fallback a la foto original cruda (longitud 1)
     ```
     La longitud de variantes para esa foto fue `1`, mientras que para las demás fotos fue `10`.
   - La cantidad de sets posibles es el mínimo de variantes entre todas las fotos:
     `min_variantes = min(10, 10, 1) = 1`
   - Por tanto, se creó **un solo set** en vez de 10, y ese set contenía la **imagen original sin mutar**.
   - La primera cuenta (`alejandroantigravity2` para Espejo/Espejos o `catalogo2` para Lámpara) tomó ese producto y consumió ese único set disponible.
   - Al llegar la segunda cuenta (`alejandroantigravity1`), ya no quedaban sets disponibles y se reportó como quemado.

---

## 2. Dudas y Aclaraciones Técnicas

### 2.1. ¿Cómo se extraen las imágenes para publicar?
- Funciona mediante **Sets**: si un producto tiene 3 fotos originales, al generar 10 variantes se crean 3 carpetas de variantes.
- Una publicación toma **1 foto de cada carpeta**, formando un set completo: `[foto1_v00k, foto2_v00k, foto3_v00k]`.
- Cada cuenta recibe un set completo diferente.

### 2.2. Duda sobre la validación dHash y distancia de Hamming
- **¿Qué es dHash?**: Reduce la imagen a una matriz de gradientes de 16x16 bits (256 bits en total).
- **Escala de distancia de Hamming (0 a 256 bits)**:
  - **0 a 5**: Imágenes virtualmente idénticas (detectadas por Revolico).
  - **6 a 10**: Zona de alto riesgo de duplicados (algoritmos anti-spam de Revolico).
  - **11 a 20**: Diferencia leve/moderada.
  - **25 a 35+**: **Diferencia perceptual ALTA y SEGURA** (totalmente indetectables como duplicadas por Revolico, pero manteniendo el producto reconocible para un comprador humano).
  - **50 a 100+**: Transformaciones radicales (como flip horizontal + crop + shift de color).
- **Umbral de Alta Seguridad que implementaremos**:
  - Distancia mínima vs Original: **$\ge 25$ o $\ge 30$** (más de 3x el umbral de Revolico).
  - Distancia mínima entre variantes de la misma foto: **$\ge 25$**.
  - Si una variante generada aleatoriamente tiene una distancia menor a 25-30, **el script la rechaza en el acto y reintenta automáticamente** con mutaciones más intensas hasta superarlo holgadamente.
  - Además se valida **MD5 byte a byte** (nunca idéntico) y **limpieza total de metadatos EXIF**.

---

## 3. Plan de Trabajo Paso a Paso

> [!IMPORTANT]
> **Regla estricta:** Todos los cambios se realizan en `scripts-gemini/`. Los archivos en `scripts-opus/` NO se tocan.

### Paso 1: Corregir detección de imágenes y formación de sets en `scripts-gemini/preparar_cuentas.py`
- **Archivo**: [scripts-gemini/preparar_cuentas.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-gemini/preparar_cuentas.py)
- **Acciones**:
  1. En `cmd_generar_imagenes`: Reemplazar `"_v" not in f.stem` por:
     ```python
     originales = [f for f in sorted(carpeta_imgs.iterdir())
                  if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                  and not re.search(r"_v\d{3}$", f.stem)]
     ```
  2. En `listar_sets_imagenes_producto`:
     - Eliminar el fallback que metía `[orig]` crudo si no había variantes.
     - Si alguna imagen no tiene variantes, emitir un aviso `⚠️ Falta generar variantes para X` y NO incluir fotos originales sin mutar en las publicaciones.
  3. En `cmd_asignar`:
     - Reforzar el quemado global a nivel de cada imagen individual.

### Paso 2: Implementar Validación Perceptual de Alta Seguridad en `scripts-gemini/mutar_imagenes.py`
- **Archivo**: [scripts-gemini/mutar_imagenes.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-gemini/mutar_imagenes.py)
- **Acciones**:
  1. Definir umbrales de alta seguridad:
     ```python
     UMBRAL_MIN_ORIGINAL = 30       # Distancia dHash mínima vs original (seguridad alta)
     UMBRAL_MIN_ENTRE_VAR = 25      # Distancia dHash mínima entre variantes de la misma foto
     MAX_INTENTOS_MUTACION = 30     # Reintentos automáticos si una mutación queda muy parecida
     ```
  2. Implementar función de mutación con validación y reintento en bucle:
     - Genera la variante.
     - Calcula MD5 y dHash (256 bits).
     - Comprueba:
       - `md5 != md5_original` y `md5` no repetido.
       - `hamming_distance(hash_orig, hash_var) >= UMBRAL_MIN_ORIGINAL` ($\ge 30$).
       - Para cada variante previa: `hamming_distance(hash_existente, hash_var) >= UMBRAL_MIN_ENTRE_VAR` ($\ge 25$).
     - Si no cumple, descarta y vuelve a mutar con transformaciones aleatorias más agresivas hasta pasar.
  3. Activar la validación por defecto en la CLI.

### Paso 3: Implementar Publicación Aleatoria en `scripts-gemini/publicar_v2.py`
- **Archivo**: [scripts-gemini/publicar_v2.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-gemini/publicar_v2.py)
- **Acciones**:
  1. Agregar argumento `--orden` con opciones `["aleatorio", "alfabetico"]` (default: `"aleatorio"`).
  2. Al seleccionar pendientes:
     ```python
     if args.orden == "aleatorio":
         random.shuffle(pendientes)
     if args.limite > 0:
         pendientes = pendientes[:args.limite]
     ```
  3. Evitar que publicaciones del mismo tipo salgan consecutivas (evitar publicar seguidos 5 armarios o 5 bocinas).

### Paso 4: Reparar Imágenes Faltantes y Asignar Cuentas
- Ejecutar la generación de variantes con el script corregido en `scripts-gemini/`:
  ```bash
  python3 scripts-gemini/preparar_cuentas.py generar-imagenes -n 10
  ```
- Verificar que las variantes de `vtq153...` (Espejo), `vl81hh...` (Espejos) y `vddqrv...` (Lampara) se generen y cumplan la distancia $\ge 25-30$.
- Ejecutar la asignación para `alejandroantigravity1@gmail.com`:
  ```bash
  python3 scripts-gemini/preparar_cuentas.py asignar --email alejandroantigravity1@gmail.com
  ```
- Confirmar que los 3 productos se asignen correctamente sin alertas de "todos quemados".

### Paso 5: Verificación y Pruebas
- Probar el modo preview aleatorio:
  ```bash
  python3 scripts-gemini/publicar_v2.py --email alejandroantigravity1@gmail.com --preview --limite 5
  ```
- Probar la verificación de hashes con:
  ```bash
  python3 scripts-gemini/mutar_imagenes.py productos/Espejo/imagenes/Gemini_Generated_Image_vtq153vtq153vtq1.jpg --verificar
  ```
  Comprobar que el 100% de las variantes superen la distancia de seguridad.
