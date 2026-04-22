# Revolico — Guía Completa de Automatización

## Qué es Revolico y cómo funciona por dentro

Revolico (revolico.com) es el principal sitio de anuncios clasificados de Cuba.
Está construido con **React** en el frontend y usa **carga perezosa (lazy loading)**,
lo que significa que no muestra todos los anuncios de golpe — los va cargando
a medida que el usuario hace scroll. Esto es importante para la automatización
porque hay que simular ese scroll para obtener la lista completa.

El sistema de seguridad del sitio usa **Cloudflare**, que detecta bots mediante
análisis de comportamiento: velocidad de clics, movimiento del mouse, fingerprint
del browser, etc. No se puede saltar automáticamente, pero sí se puede trabajar
con él usando un browser real con sesión humana activa.

---

## Infraestructura base

### El comando para abrir Chrome

```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/home/TU_USUARIO/.config/google-chrome-debug
```

**Qué hace cada parte:**

- `google-chrome` — Abre el navegador desde la terminal
- `--remote-debugging-port=9222` — Activa el Chrome DevTools Protocol (CDP),
  una puerta trasera oficial que Chrome tiene incorporada. Permite que programas
  externos envíen instrucciones: "ve a esta URL", "haz clic aquí", "lee este texto"
- `--user-data-dir=...debug` — Usa una carpeta de perfil separada. Chrome no
  permite abrir el mismo perfil dos veces, y necesitas una carpeta distinta
  para activar el debugging

**La primera vez:** el perfil está vacío, debes iniciar sesión en Revolico
manualmente y resolver el CAPTCHA de Cloudflare. A partir de ahí las cookies
quedan guardadas en esa carpeta y no vuelve a pedirte login.

### Conectarse desde Python

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
```

Siempre usar `connect_over_cdp` — esto se une al Chrome ya abierto con tu
sesión, en vez de abrir un browser limpio sin cookies.

**Regla importante:** siempre navegar con `page.goto()` propio, nunca usar
la página que el usuario tiene abierta directamente. La URL puede tener
`#google_vignette` al final (un popup de Google que causa redirección) y rompe
el script. Ejemplo correcto:

```python
await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
await asyncio.sleep(10)  # Esperar que se estabilice completamente
```

### Instalación

```bash
pip3 install playwright
playwright install chromium
```

---

## Estructura de URLs

| Página | URL |
|---|---|
| Inicio | `https://www.revolico.com/` |
| Mi cuenta / mis anuncios | `https://www.revolico.com/account` |
| Gestionar anuncio | `https://www.revolico.com/item/{ID}/_/manage` |
| Ver anuncio público | `https://www.revolico.com/item/slug-{ID}` |
| Publicar nuevo | `https://www.revolico.com/item/publish` |
| Login | `https://www.revolico.com/login` |
| Logout | `https://www.revolico.com/logout` |

### El ID del anuncio

Cada anuncio tiene un número único de 8 dígitos. Aparece al final del slug:

```
/item/mesita-de-noche-54356411?token=_
                      ↑
                    ID = 54356411
```

Extraerlo con regex:

```python
import re
match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
item_id = match.group(1)  # "54356411"
```

Con el ID puedes construir la URL de gestión directamente:
`https://www.revolico.com/item/54356411/_/manage`

---

## Cargar todos los anuncios (lazy loading)

Revolico solo carga los anuncios visibles en pantalla. Para obtener todos
hay que hacer scroll hasta el fondo y detectar cuándo no aparecen más:

```python
async def cargar_todos_los_ids(page):
    ids_vistos = set()
    sin_cambios = 0

    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()
        for el in links:
            href = await el.get_attribute("href")
            if href:
                match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
                if match:
                    ids_actuales.add(match.group(1))

        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break  # 3 scrolls sin cambios = llegamos al final
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
            print(f"  {len(ids_vistos)} anuncios cargados...")

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

    return list(ids_vistos)
```

Funciona para cualquier cantidad: 50, 100, 200, 300+ anuncios.

---

## Selectores de la interfaz

Revolico usa React. Los elementos no siempre tienen IDs fijos, pero sí
tienen textos consistentes. Lo más confiable es buscar por texto:

```python
# En /account — lista de anuncios
'a:has-text("Gestionar")'              # Link con texto Gestionar

# En /item/ID/_/manage — página de gestión
'button:has-text("Renovar anuncio")'   # Renovar
'button:has-text("Destacar anuncio")'  # Pago por destacar (premium)
'a:has-text("Editar anuncio")'         # Editar contenido
'button:has-text("Eliminar anuncio")'  # Eliminar permanentemente
'a:has-text("Ver tu anuncio")'         # Ver versión pública

# Modales y popups
'text="Tu anuncio fue renovado."'      # Confirmación de éxito
'text="La verificación falló"'         # Error de Cloudflare
'text="Reintentar"'                    # Botón tras fallo de Cloudflare
'button:has-text("Entendido")'         # Cerrar modal de éxito
'[data-slot="dialog-portal"] button'   # Cerrar popup de Destacados

# Formulario de publicar/editar
'input[name="title"]'                  # Título del anuncio
'textarea[name="description"]'         # Descripción
'input[name="price"]'                  # Precio
```

---

## Obstáculos y cómo resolverlos

### 1. Popup de "Más ventajas con Destacados"
Aparece al entrar a la página de gestión. Cubre el botón Renovar.

```python
async def cerrar_popup(page):
    selectores = [
        'button[aria-label="Close"]',
        'button[aria-label="Cerrar"]',
        '[data-slot="dialog-close"]',
        '[data-slot="dialog-portal"] button',
    ]
    for sel in selectores:
        btn = await page.query_selector(sel)
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            return True
    return False
```

### 2. Overlay que bloquea clics
Cuando hay un `div` semitransparente encima, el clic normal de Playwright
falla con timeout. Solución: clic por JavaScript que ignora overlays:

```python
# En vez de: await boton.click()
await page.evaluate("el => el.click()", boton)
```

### 3. Error de Cloudflare ("La verificación falló")
Ocurre aleatoriamente. El script debe detectarlo y reintentar:

```python
async def intentar_con_reintentos(page, accion_fn, max_intentos=3):
    for intento in range(1, max_intentos + 1):
        if intento > 1:
            print(f"  Reintentando ({intento}/{max_intentos})...")

        await accion_fn()  # Ejecutar la acción (ej: clic en Renovar)
        await asyncio.sleep(2)

        if await page.query_selector('text="Tu anuncio fue renovado."'):
            return True

        fallo = await page.query_selector('text="La verificación falló"')
        if fallo:
            reintentar = await page.query_selector('text="Reintentar"')
            if reintentar:
                await page.evaluate("el => el.click()", reintentar)
                await asyncio.sleep(3)
            continue

    return False
```

### 4. google_vignette en la URL
Cloudflare/Google inyecta `#google_vignette` causando redirección que destruye
el contexto de ejecución. Solución: siempre navegar con `page.goto()` propio
en lugar de usar la página que el usuario tiene abierta.

### 5. Límite de renovación (24 horas)
Cada anuncio solo se puede renovar una vez cada 24 horas. Si ya fue renovado,
el botón no aparece. El script debe detectar la ausencia del botón y marcarlo
como "ya renovado" sin lanzar error:

```python
botones = await page.query_selector_all('button:has-text("Renovar anuncio")')
if not botones:
    print("  Ya renovado hoy")
    continue  # Pasar al siguiente anuncio
```

---

## Patrón base para cualquier script

```python
import asyncio
import re
from playwright.async_api import async_playwright

async def cerrar_popup(page):
    for sel in ['[data-slot="dialog-portal"] button',
                'button[aria-label="Close"]',
                'button[aria-label="Cerrar"]']:
        btn = await page.query_selector(sel)
        if btn:
            await btn.click()
            await asyncio.sleep(1)
            return True
    return False

async def cargar_todos_los_ids(page):
    ids_vistos = set()
    sin_cambios = 0
    while True:
        links = await page.query_selector_all('a:has-text("Gestionar")')
        ids_actuales = set()
        for el in links:
            href = await el.get_attribute("href")
            if href:
                match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
                if match:
                    ids_actuales.add(match.group(1))
        if ids_actuales == ids_vistos:
            sin_cambios += 1
            if sin_cambios >= 3:
                break
        else:
            sin_cambios = 0
            ids_vistos = ids_actuales
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
    return list(ids_vistos)

async def main():
    async with async_playwright() as p:
        # 1. Conectar al Chrome con sesión activa
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # 2. Navegar a la cuenta
        await page.goto("https://www.revolico.com/account", wait_until="domcontentloaded")
        await asyncio.sleep(10)

        # 3. Cargar todos los IDs
        ids = await cargar_todos_los_ids(page)
        print(f"Total: {len(ids)} anuncios")

        # 4. Procesar cada uno
        for i, item_id in enumerate(ids):
            print(f"[{i+1}/{len(ids)}] ID {item_id}")
            await page.goto(
                f"https://www.revolico.com/item/{item_id}/_/manage",
                wait_until="domcontentloaded"
            )
            await asyncio.sleep(3)
            await cerrar_popup(page)

            # === TU LÓGICA AQUÍ ===

asyncio.run(main())
```

---

## Ideas de scripts que se pueden hacer

### Ya hecho
- **Renovar todos los anuncios** — renueva de abajo hacia arriba para
  que los anuncios que estaban más abajo suban primero, dejando todos
  en buen orden al terminar

### Fáciles de implementar
- **Scraping de precios propios** — recorrer todos tus anuncios y
  extraer título, precio, categoría, fecha de publicación y guardarlo
  en un CSV o JSON para análisis
- **Monitor de visitas** — entrar a cada anuncio y extraer el contador
  de visitas, guardarlo con fecha para ver tendencias
- **Actualizar precios en lote** — dado un CSV con ID y nuevo precio,
  recorrer cada anuncio, entrar a editar y cambiar el precio
- **Eliminar anuncios en lote** — dada una lista de IDs, eliminarlos todos
  automáticamente

### Más complejos
- **Scraping de competidores** — buscar una categoría específica, recorrer
  todas las páginas de resultados y extraer todos los anuncios con sus
  precios para análisis de mercado
- **Replicar anuncio en múltiples categorías** — publicar el mismo anuncio
  en varias categorías automáticamente
- **Monitor de anuncios nuevos** — verificar cada X minutos si aparecieron
  anuncios nuevos en una búsqueda específica y notificar
- **Exportar todos los anuncios propios** — guardar título, descripción,
  precio, fotos e ID de todos los anuncios en archivos locales como backup

---

## Cómo manejar múltiples cuentas

No hay login automático confiable (Cloudflare lo detecta). El flujo recomendado:

1. Abres Chrome con el comando de debugging
2. Entras manualmente a la cuenta que quieras
3. Corres el script — detecta automáticamente la cuenta activa y cuántos
   anuncios tiene
4. Cuando termina, cambias de cuenta manualmente en Chrome
5. Vuelves a correr el script

El script no necesita saber cuál cuenta es — simplemente procesa lo que
encuentre en `/account` de la sesión activa.

---

## Velocidad y pausas recomendadas

Las pausas son importantes para no disparar los filtros de Cloudflare:

| Acción | Pausa recomendada |
|---|---|
| Después de `goto` a cualquier página | `asyncio.sleep(3)` |
| Después de `page.goto` a la cuenta | `asyncio.sleep(10)` |
| Entre scroll y scroll | `asyncio.sleep(2)` |
| Después de cerrar popup | `asyncio.sleep(1)` |
| Después de clic en Renovar | `asyncio.sleep(2)` |
| Entre anuncios procesados | `asyncio.sleep(2)` |
| Después de error de Cloudflare, antes de reintentar | `asyncio.sleep(3)` |

Si hay muchos errores de Cloudflare seguidos, aumentar las pausas a 4-5 segundos.

---

## Extraer datos de una página de anuncio

Para scraping, los datos de interés están accesibles así:

```python
# En la página pública de un anuncio: /item/slug-ID
titulo = await page.query_selector('h1')
texto_titulo = await titulo.inner_text() if titulo else ""

precio = await page.query_selector('[class*="price"], [data-testid*="price"]')
texto_precio = await precio.inner_text() if precio else ""

descripcion = await page.query_selector('[class*="description"]')
texto_desc = await descripcion.inner_text() if descripcion else ""

# Fecha de publicación / última renovación
fecha = await page.query_selector('time')
attr_fecha = await fecha.get_attribute("datetime") if fecha else ""

# URL de las fotos
imagenes = await page.query_selector_all('img[src*="revolico"]')
urls_fotos = [await img.get_attribute("src") for img in imagenes]
```

Para búsquedas y scraping masivo, construir la URL de búsqueda:
```
https://www.revolico.com/search?q=TERMINO&category=CATEGORIA
```

---

## Notas finales

- **El CAPTCHA** (botón de Cloudflare) solo aparece al iniciar sesión por primera
  vez con el perfil de debug. Una vez resuelto, no vuelve a pedirse en esa carpeta.
- **Revolico cambia su interfaz** ocasionalmente. Si un selector deja de funcionar,
  inspeccionar el elemento en Chrome (clic derecho → Inspeccionar) para ver
  el nuevo selector.
- **Los errores de Cloudflare** son aleatorios, no hay patrón claro. Con 3 reintentos
  por anuncio se resuelve la mayoría. Una tasa de éxito del 90-95% es normal.
- **El orden de los anuncios** en `/account` es por fecha de última renovación
  (más reciente arriba). Procesar de abajo hacia arriba deja todo en buen orden.
