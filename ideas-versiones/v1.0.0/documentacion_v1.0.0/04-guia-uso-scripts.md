# 04 — Guía de Uso de Scripts v1.0.0

## Requisitos Previos

```bash
# Instalar dependencias
pip3 install playwright Pillow

# Instalar browsers de Playwright
playwright install chromium
```

## Ruta Base del Proyecto

```
/home/camiloueransim/maybel-ventas/renovar-anuncios/
```

Todos los comandos de esta guía se ejecutan desde esa carpeta.

---

## Paso 1: Importar Anuncios Existentes

**Solo se ejecuta una vez.** Convierte la carpeta `anuncios/` vieja al nuevo formato `productos/`.

```bash
python3 scripts-opus/preparar_cuentas.py importar-anuncios
```

**Lo que hace:**
- Lee cada carpeta `anuncios/{ID}/datos.md`
- Parsea nombre, precio, moneda, categoría y descripción
- Crea `productos/{nombre-limpio}/producto.json`
- Copia las fotos a `productos/{nombre-limpio}/imagenes/`
- Guarda la descripción en `descripcion_base.txt`

**Resultado:** ~504 carpetas de productos en `productos/`

---

## Paso 2: Generar Variantes de Imágenes

**Genera N variantes mutadas de cada foto original.**

```bash
# Generar 20 variantes por imagen (recomendado)
python3 scripts-opus/preparar_cuentas.py generar-imagenes -n 20

# Generar 10 variantes (más rápido pero menos cuentas posibles)
python3 scripts-opus/preparar_cuentas.py generar-imagenes -n 10
```

**Lo que hace:**
- Para cada producto, encuentra las fotos originales
- Llama a `mutar_imagenes.py` para generar N variantes de cada una
- Las variantes se guardan en `productos/{producto}/imagenes/variantes_{foto}/`
- Si ya existen suficientes variantes, las salta (idempotente)

**Nota:** Este paso puede tardar bastante (~504 productos × ~2.5 fotos promedio × 20 variantes). Se puede interrumpir y continuar — no regenera las que ya existen.

---

## Paso 3: Generar Variantes de Descripciones

**Genera N descripciones variadas a partir de la descripción base.**

```bash
python3 scripts-opus/preparar_cuentas.py generar-descripciones -n 20
```

**Lo que hace:**
- Lee `descripcion_base.txt` de cada producto
- Aplica sinónimos aleatorios (de `scripts-opus/descripciones/sinonimos.txt`)
- Reordena oraciones
- Añade frases de cierre (de `scripts-opus/descripciones/frases_cierre.txt`)
- Guarda en `productos/{producto}/descripciones/variante_001.txt`, etc.

**Archivos editables:**
- `scripts-opus/descripciones/sinonimos.txt` — Puedes añadir/quitar/editar sinónimos
- `scripts-opus/descripciones/frases_cierre.txt` — Puedes añadir/quitar/editar frases

---

## Paso 4: Asignar Productos a una Cuenta

**Asigna todos los productos disponibles a una cuenta, eligiendo imágenes y descripciones no usadas por nadie.**

```bash
# Asignar a una cuenta
python3 scripts-opus/preparar_cuentas.py asignar --email tucuenta@gmail.com

# Asignar a una segunda cuenta (usará variantes diferentes)
python3 scripts-opus/preparar_cuentas.py asignar --email otracuenta@gmail.com
```

**Lo que hace:**
- Revisa TODAS las cuentas existentes para saber qué recursos ya se usaron globalmente
- Para cada producto, elige un "set" de imágenes no usado (una variante de cada foto original)
- Elige una descripción no usada
- Lo guarda en `estado/cuentas/{email}.json`
- Si un producto ya está asignado a esa cuenta, no lo duplica

**Importante:** Las imágenes y descripciones se "queman" globalmente. Si asignas 5 cuentas y tienes 20 variantes, la cuenta 1 usa las v001, la cuenta 2 las v002, etc.

---

## Paso 5: Verificar Estado

```bash
# Ver estado general del sistema
python3 scripts-opus/preparar_cuentas.py estado

# Ver los pendientes de una cuenta
python3 scripts-opus/preparar_cuentas.py pendientes --email tucuenta@gmail.com
```

---

## Paso 6: Publicar

### 6a. Preparar Chrome

```bash
# Abrir Chrome con debugging (puerto 9222)
google-chrome --remote-debugging-port=9222

# O con un perfil separado
google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.config/google-chrome-debug
```

Luego en Chrome:
1. Ir a revolico.com
2. Iniciar sesión con la cuenta deseada
3. Resolver cualquier CAPTCHA de Cloudflare
4. Dejar Chrome abierto

### 6b. Preview (sin publicar realmente)

```bash
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --preview
```

Muestra qué publicaría sin hacer nada.

### 6c. Publicar de verdad

```bash
# Publicar todo lo pendiente
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com

# Publicar solo 5 anuncios (para probar)
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --limite 5

# Publicar con ráfagas de 3 y descanso de 45 minutos
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --rafaga 3 --descanso 45

# Usar un puerto de Chrome diferente
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --port 9223
```

**Parámetros del publicador:**

| Parámetro | Default | Descripción |
|---|---|---|
| `--email` | (requerido) | Email de la cuenta a publicar |
| `--preview` | false | Solo mostrar, no publicar |
| `--limite` | 0 (todos) | Máximo de anuncios por sesión |
| `--port` | 9222 | Puerto de Chrome debug |
| `--rafaga` | 5 | Anuncios por ráfaga |
| `--descanso` | 30 | Minutos de descanso entre ráfagas |

---

## Uso de mutar_imagenes.py (Standalone)

El script de mutación también se puede usar independientemente:

```bash
# Mutar una imagen específica
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 20

# Mutar todas las imágenes de una carpeta
python3 scripts-opus/mutar_imagenes.py productos/buros/imagenes/ -n 15

# Mutar con salida personalizada
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 10 -o mis_variantes/

# Mutar y verificar la efectividad (recomendado la primera vez)
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 10 --verificar
```

La verificación compara:
- Cada variante vs la original (dHash y MD5)
- Cada variante vs todas las demás variantes
- Muestra si algún par es peligrosamente similar

---

## Resumen de Comandos Completo

```bash
# ── PREPARACIÓN (una sola vez) ──
python3 scripts-opus/preparar_cuentas.py importar-anuncios
python3 scripts-opus/preparar_cuentas.py generar-imagenes -n 20
python3 scripts-opus/preparar_cuentas.py generar-descripciones -n 20

# ── POR CADA CUENTA ──
python3 scripts-opus/preparar_cuentas.py asignar --email cuenta@gmail.com
python3 scripts-opus/preparar_cuentas.py pendientes --email cuenta@gmail.com

# ── PUBLICAR ──
google-chrome --remote-debugging-port=9222  # abrir Chrome
python3 scripts-opus/publicar_v2.py --email cuenta@gmail.com --preview  # primero preview
python3 scripts-opus/publicar_v2.py --email cuenta@gmail.com --limite 5  # probar con pocos
python3 scripts-opus/publicar_v2.py --email cuenta@gmail.com  # publicar todo

# ── MONITOREO ──
python3 scripts-opus/preparar_cuentas.py estado
```
