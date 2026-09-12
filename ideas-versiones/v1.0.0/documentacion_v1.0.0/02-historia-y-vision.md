# 02 — Historia y Visión del Proyecto

## ¿Qué es este proyecto?

Este proyecto automatiza la **publicación y gestión de anuncios en Revolico** para un negocio de venta de muebles y productos del hogar importados. El objetivo es mantener una presencia masiva en la plataforma con cientos de productos publicados simultáneamente desde múltiples cuentas.

## El Negocio

- Se venden muebles, electrodomésticos, adornos y productos del hogar
- Los productos son importados (no fabricados localmente)
- Se venden en Cuba, con entrega en La Habana
- Precios en USD y CUP
- Hay ~500 productos diferentes con ~1300 fotos

## Lo que existía antes de la v1.0.0

### Script de Renovación Original (`publicar/`)
- **`publicar_anuncios_precio_original-fast.py`**: Script de Playwright que leía datos de `anuncios/` y publicaba en Revolico
- Tenía hash-busting de imágenes rudimentario (cambio de 1 píxel de brillo + recorte de 2px) que resultó **insuficiente** contra la detección de Revolico
- Inyectaba frases de despedida al final de las descripciones
- Usaba ráfagas de 10 anuncios con descanso de 20 min
- **Problema grave**: ante Cloudflare hacía `sys.exit(1)`, matando el script y potencialmente levantando sospechas

### Extensión RevoRenew (`RevoRenew last update/`)
- Extensión de Chrome para renovar anuncios automáticamente
- Hacía clic en "Renovar anuncio" en la página de gestión
- No publicaba anuncios nuevos, solo renovaba existentes
- Ahora menos necesaria porque Revolico tiene botón nativo de "Renovar todo"

### Estructura de datos vieja (`anuncios/`)
- Carpeta `anuncios/{ID}/` con:
  - `datos.md`: Información del producto en formato Markdown
  - `foto_01.jpg`, `foto_02.jpg`, etc.
- `anuncios/index.json`: Lista de todos los anuncios con sus títulos e IDs
- **Problemas**: Formato poco práctico (MD en vez de JSON), sin separación entre datos y estado

## ¿Por qué se necesitaba la v1.0.0?

### Problemas Detectados

1. **Imágenes detectadas como duplicadas**: El hash-busting del script viejo (±3% brillo, recorte 2px) era tan sutil que Revolico lo detectaba. Resultado: anuncios borrados y cuentas baneadas
2. **Una sola cuenta**: Todo se publicaba desde una cuenta, haciéndola blanco fácil de ban
3. **Sin gestión de estado**: No había forma de saber qué se publicó, en qué cuenta, con qué imagen. Si se baneaba la cuenta, se perdía todo el tracking
4. **Cloudflare mal manejado**: `sys.exit(1)` ante un challenge era la peor respuesta posible (Chrome queda con la página de challenge activa)
5. **Descripciones idénticas**: La misma descripción se usaba en todas las cuentas, facilitando la detección
6. **Sin multi-foto**: El publicador subía una sola foto por anuncio, pero Revolico permite varias
7. **Imágenes reutilizadas entre cuentas**: Si la cuenta A y la cuenta B usaban la misma foto, Revolico lo detectaba

### Objetivo de la v1.0.0

Crear un sistema completo de **publicación multi-cuenta con anti-detección** que:
1. Mute agresivamente las imágenes para que no se detecten como duplicadas
2. Varíe las descripciones automáticamente
3. Lleve un registro de qué se publicó, dónde, con qué imagen y descripción
4. No reutilice NUNCA una imagen o descripción entre cuentas
5. Maneje Cloudflare con pausas inteligentes en vez de abortar
6. Publique TODAS las fotos de un producto (multi-foto)
7. Use pausas más largas y movimiento orgánico del mouse

## Visión a Futuro

- **v1.1**: Login automático multi-cuenta (si se puede esquivar Cloudflare)
- **v1.2**: Renovación automática integrada (reemplazar RevoRenew)
- **v1.3**: Generación de descripciones con IA (más naturales que sinónimos)
- **v2.0**: Panel web para gestionar todo desde el navegador

## Ruta del Proyecto

```
/home/camiloueransim/maybel-ventas/renovar-anuncios/
```

## Tecnologías Usadas

| Tecnología | Uso |
|---|---|
| **Python 3** | Lenguaje principal de todos los scripts |
| **Playwright** | Automatización de Chrome (vía CDP) |
| **Pillow (PIL)** | Manipulación de imágenes (mutación) |
| **Chrome CDP** | Conexión al navegador real del usuario |
| **JSON** | Formato de datos y estado |
