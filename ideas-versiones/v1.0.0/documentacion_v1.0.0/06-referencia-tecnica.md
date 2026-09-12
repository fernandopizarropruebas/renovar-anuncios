# 06 — Referencia Técnica

## Dependencias Python

```
playwright>=1.40
Pillow>=10.0
```

Instalación:
```bash
pip3 install playwright Pillow
playwright install chromium
```

---

## Chrome DevTools Protocol (CDP)

### Qué es
CDP es un protocolo que permite controlar Chrome desde código externo. Playwright se conecta a Chrome vía CDP para automatizar acciones.

### Cómo funciona
1. Se abre Chrome con `--remote-debugging-port=9222`
2. Chrome expone un servidor WebSocket en `http://localhost:9222`
3. Playwright se conecta con `connect_over_cdp("http://localhost:9222")`
4. A diferencia de `launch()`, esto NO abre un browser nuevo — se conecta al existente
5. Las cookies, sesiones y extensiones del Chrome real están disponibles

### Ventaja clave
El usuario inicia sesión manualmente una sola vez. Las cookies persisten. Cloudflare ve un Chrome real (no un browser de Playwright) con historial de navegación legítimo.

### Puertos
- Default: 9222
- Si necesitas múltiples Chromes simultáneos: 9222, 9223, 9224...

```bash
# Chrome 1
google-chrome --remote-debugging-port=9222 --user-data-dir=~/.config/chrome-debug-1
# Chrome 2
google-chrome --remote-debugging-port=9223 --user-data-dir=~/.config/chrome-debug-2
```

---

## Selectores CSS de Revolico (Actualizados Sep 2026)

### Formulario de Publicar (/item/publish)

```python
# Campos del formulario
'input[name="title"]'            # Título (max 120 chars)
'textarea[name="description"]'   # Descripción (max 1000 chars)
'input[name="price"]'            # Precio
'select[name="currency"]'        # Moneda (USD, CUP, MLC)
'input[type="file"]'             # Input de fotos (oculto, acepta múltiples)
'button[type="submit"]'          # Botón publicar

# Categoría
'[data-testid*="category"]'                   # Botón abrir selector de categoría
'button:has-text("Elige una categoría")'       # Alternativa del botón
# Las categorías se buscan por texto dentro del modal
```

### Página de Cuenta (/account)

```python
# Lista de anuncios
'a:has-text("Gestionar")'       # Links a gestionar cada anuncio

# Cada link tiene el formato:
# /item/{slug}-{ID}?token=_
```

### Página de Gestión (/item/{ID}/_/manage)

```python
'button:has-text("Renovar anuncio")'     # Botón renovar
'a:has-text("Editar anuncio")'           # Link editar
'button:has-text("Eliminar anuncio")'    # Botón eliminar

# Confirmaciones
'text="Tu anuncio fue renovado."'        # Modal de éxito
'button:has-text("Entendido")'           # Cerrar modal
'[data-slot="dialog-portal"] button'     # Cerrar popup de Destacados
```

### Detección de fotos subidas

```python
# Después de subir, las fotos aparecen como:
'img[src^="blob:"]'              # Blobs locales
'img[src^="data:image"]'         # Data URLs
'[class*="preview"] img'         # Dentro de contenedor preview
'[class*="thumb"] img'           # Thumbnails
'[class*="uploaded"] img'        # Contenedor uploaded
'[class*="photo"] img'           # Contenedor photo
```

### Detección de Cloudflare

```python
# Título de la página
'Just a moment'                  # En inglés
'Un momento'                     # En español

# Elementos del DOM
'#challenge-running'             # Script de challenge ejecutándose
'iframe[src*="cloudflare"]'      # iFrame de Cloudflare
'#challenge-form'                # Formulario del challenge
```

---

## Cookies de Revolico

### Autenticación
```python
# La cookie de sesión es un JWT
cookie_name = 'st-access-token'

# Extraer el email del JWT:
import base64, json
parts = cookie_value.split('.')
payload = parts[1] + '=' * (-len(parts[1]) % 4)
data = json.loads(base64.b64decode(payload).decode('utf-8'))
email = data.get("user_email") or data.get("user_name")
```

---

## Configuración de Pausas (publicar_v2.py)

```python
# En scripts-opus/publicar_v2.py, líneas ~50-60:

PAUSA_ENTRE_ANUNCIOS = (30.0, 90.0)    # Segundos entre anuncios
PAUSA_CARGA_PAGINA = (4.0, 7.0)        # Segundos tras navegar
PAUSA_CARGA_FOTOS = 12                  # Segundos esperando upload de fotos
MAX_REINTENTOS_FOTOS = 3                # Reintentos si no suben las fotos
PAUSA_CLOUDFLARE = (120, 300)           # Segundos de pausa ante Cloudflare

ANUNCIOS_POR_RAFAGA = 5                # Anuncios antes de descansar
DESCANSO_RAFAGA_MINUTOS = 30           # Minutos de descanso entre ráfagas
```

Para modificar en CLI sin tocar código:
```bash
python3 scripts-opus/publicar_v2.py --email x@y.com --rafaga 3 --descanso 45
```

---

## Configuración de Mutación de Imágenes (mutar_imagenes.py)

```python
# En scripts-opus/mutar_imagenes.py, ~líneas 30-50:

CONFIG = {
    "probabilidad_flip": 0.5,       # 50% de hacer flip horizontal
    "crop_min": 1,                   # Píxeles mínimos de recorte por lado
    "crop_max": 45,                  # Píxeles máximos de recorte por lado
    "rotacion_max": 3.0,             # Grados máximos de rotación
    "hue_shift_max": 15,             # Grados de shift en canal Hue (HSV)
    "brillo_min": 0.88,              # Multiplicador mínimo de brillo
    "brillo_max": 1.12,              # Multiplicador máximo de brillo
    "contraste_min": 0.88,
    "contraste_max": 1.12,
    "saturacion_min": 0.82,
    "saturacion_max": 1.18,
    "nitidez_min": 0.7,
    "nitidez_max": 1.5,
    "blur_probabilidad": 0.3,        # 30% de aplicar blur
    "blur_radio_max": 0.7,
    "borde_probabilidad": 0.3,       # 30% de añadir borde de color
    "borde_max": 6,                  # Píxeles de borde
    "jpeg_quality_min": 70,
    "jpeg_quality_max": 95,
}
```

---

## Estructura de Archivos Clave

### producto.json
```json
{
  "nombre": "Buró de 100cm",
  "precio": "150",
  "moneda": "USD",
  "categoria": ["Hogar", "Muebles"],
  "id_original": "54130535"
}
```

### estado/cuentas/{email}.json
```json
{
  "email": "cuenta@gmail.com",
  "alias": "cuenta-1",
  "fecha_creacion": "2026-09-10T23:48:08",
  "publicaciones": [
    {
      "producto": "buros",
      "imagenes_usadas": ["variantes_foto_01/foto_01_v003.jpg"],
      "descripcion_usada": "variante_003.txt",
      "estado": "pendiente|publicado|fallido",
      "url_revolico": null,
      "fecha_publicacion": null
    }
  ]
}
```

### estado/registro_global.json
```json
{
  "cuentas_registradas": ["cuenta1@gmail.com", "cuenta2@gmail.com"],
  "ultima_actualizacion": "2026-09-11T10:00:00",
  "estadisticas": {}
}
```

---

## Errores Comunes y Soluciones

| Error | Causa | Solución |
|---|---|---|
| `No se pudo conectar a Chrome` | Chrome no está abierto con debugging | `google-chrome --remote-debugging-port=9222` |
| `No existe la cuenta X` | No se asignó | `preparar_cuentas.py asignar --email X` |
| Cloudflare 3 veces seguidas | La sesión está quemada | Resolver captcha manualmente en Chrome, esperar 1h |
| Fotos no suben | Problema de Revolico | Se reintenta automáticamente 3 veces |
| `sin sets de imágenes disponibles` | Todas las variantes ya se usaron | Generar más variantes con `-n 30` o más |
| `descripciones agotadas` | Todas las variantes ya se usaron | Generar más con `generar-descripciones -n 30` |
