# 01 — Qué es Revolico

## Descripción General

**Revolico** (revolico.com) es el principal sitio de anuncios clasificados de Cuba. Funciona como un marketplace donde vendedores publican productos y compradores los buscan. Es el equivalente cubano de Craigslist, OLX o Wallapop.

## Arquitectura Técnica

### Frontend
- Construido con **React** (SPA - Single Page Application)
- Usa **carga perezosa (lazy loading)**: los anuncios no se cargan todos de golpe, se van cargando a medida que haces scroll
- Los elementos del DOM cambian de clases CSS frecuentemente (típico de React), por lo que los selectores más confiables son **por texto** (`has-text`) en vez de por clase

### Seguridad
- Usa **Cloudflare** como protección anti-bot
- Cloudflare analiza: velocidad de clics, movimiento del mouse, fingerprint del browser, patrones de navegación
- Cuando sospecha de un bot, muestra un **challenge/captcha** (página "Just a moment..." / "Un momento...")
- Revolico también detecta **contenido duplicado**: imágenes iguales, descripciones idénticas
- Si detecta bots: **borra anuncios** y puede **banear la cuenta o el número de teléfono**

### Políticas Anti-duplicados (actualizado 2026)
- **Imágenes**: Si subes la misma imagen en diferentes anuncios o cuentas, Revolico lo detecta. Usa algún tipo de hash perceptual (pHash/dHash) — no basta con cambiar el nombre del archivo
- **Descripciones**: Textos idénticos entre anuncios/cuentas son detectados
- **Límite de renovación**: Cada anuncio solo se puede renovar una vez cada 24 horas
- **Renovación automática**: Revolico ahora tiene botón propio de "Renovar todo", por lo que la renovación automática ya no es la prioridad del proyecto

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
| Búsqueda | `https://www.revolico.com/search?q=TERMINO&category=CATEGORIA` |

### El ID del Anuncio

Cada anuncio tiene un número único de 8 dígitos que aparece al final del slug de la URL:

```
/item/mesita-de-noche-54356411?token=_
                      ↑
                    ID = 54356411
```

Extraerlo con regex en Python:
```python
import re
match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
item_id = match.group(1)  # "54356411"
```

## Selectores CSS/Texto Importantes

```python
# En /account — lista de anuncios
'a:has-text("Gestionar")'              # Link con texto Gestionar

# En /item/ID/_/manage — página de gestión
'button:has-text("Renovar anuncio")'   # Renovar
'a:has-text("Editar anuncio")'         # Editar contenido
'button:has-text("Eliminar anuncio")'  # Eliminar permanentemente

# Modales y popups
'text="Tu anuncio fue renovado."'      # Confirmación de éxito
'text="La verificación falló"'         # Error de Cloudflare
'button:has-text("Entendido")'         # Cerrar modal de éxito
'[data-slot="dialog-portal"] button'   # Cerrar popup de Destacados

# Formulario de publicar/editar
'input[name="title"]'                  # Título del anuncio
'textarea[name="description"]'         # Descripción
'input[name="price"]'                  # Precio
'select[name="currency"]'             # Moneda (USD, CUP, MLC)
'input[type="file"]'                   # Subir fotos
'button[type="submit"]'               # Botón publicar
'[data-testid*="category"]'           # Selector de categoría
```

## Cómo Conectarse a Revolico desde Python

### 1. Abrir Chrome en modo debug
```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/home/TU_USUARIO/.config/google-chrome-debug
```

- `--remote-debugging-port=9222` activa el Chrome DevTools Protocol (CDP)
- `--user-data-dir=...debug` usa un perfil separado
- La primera vez: iniciar sesión manualmente y resolver CAPTCHA de Cloudflare
- Después las cookies quedan guardadas y no vuelve a pedir login

### 2. Conectarse desde Python con Playwright
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
```

**Regla clave**: Siempre usar `connect_over_cdp` (se conecta al Chrome real con tu sesión), nunca `launch` (abriría un browser limpio que pide login).

### 3. Instalación
```bash
pip3 install playwright Pillow
playwright install chromium
```

## Múltiples Cuentas

No hay login automático confiable (Cloudflare lo detecta). El flujo es:
1. Abrir Chrome con debugging
2. Entrar manualmente a la cuenta deseada
3. Correr el script — detecta automáticamente la cuenta activa
4. Cuando termina, cambiar de cuenta manualmente en Chrome
5. Volver a correr el script

El script no necesita saber cuál cuenta es — procesa lo que encuentre en la sesión activa.
