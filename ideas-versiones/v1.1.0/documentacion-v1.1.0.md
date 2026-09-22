# Documentación Técnica v1.1.0 — Renovación de Anuncios

## Qué es la v1.1.0

La v1.1.0 añade un **script de renovación de anuncios** (`renovar_v2.py`) que reemplaza al viejo [`renovar_revolico-antifallos.py`](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/renovar_revolico-antifallos.py). El script viejo dejó de funcionar porque Revolico cambió su interfaz.

## ¿Qué cambió en Revolico? (Sep 2026)

### Cambios detectados vs el script viejo

| Aspecto | Antes (script viejo) | Ahora (Sep 2026) |
|---|---|---|
| **URL de cuenta** | `/account` | `/account/ads` |
| **Botón renovar** | Botón grande con texto "Renovar anuncio" | Icono pequeño en barra de acciones inferior con texto "Renovar" |
| **Popup de destacados** | Un solo diseño | 2 variantes visuales (según OS/resolución) |
| **Botón "Renovar todo"** | No existía | Existe pero no funciona correctamente |
| **Barra de acciones** | Solo botón de renovar | Barra con: Editar, Renovar, Compartir, Eliminar, Más |

### Selectores actualizados

```python
# ── PÁGINA /account/ads ──
# Botón "Gestionar" de cada anuncio (SIN CAMBIO)
'a:has-text("Gestionar")'

# ── PÁGINA /item/{ID}/_/manage ──

# Popup de Destacados — ambas variantes
'button[aria-label="Close"]'           # Botón ✕ (inglés)
'button[aria-label="Cerrar"]'          # Botón ✕ (español)
'[data-slot="dialog-close"]'           # Por data attribute
'[data-slot="dialog-overlay"]'         # Overlay/backdrop (para clic fuera)

# Botón Renovar (NUEVO)
'button:has-text("Renovar")'           # Ahora texto corto "Renovar"
'a:has-text("Renovar")'               # Alternativa si es link

# Confirmación de éxito
'text="Tu anuncio fue renovado."'      # Mensaje de éxito
'button:has-text("Entendido")'         # Cerrar confirmación

# Cloudflare
# Se detecta por título de página + elementos del DOM
```

## Cómo funciona el script

### Flujo principal

```
┌─────────────────────────────────┐
│ 1. Conectar a Chrome vía CDP    │
│    (puerto configurable)        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 2. Navegar a /account/ads       │
│    + Detectar Cloudflare        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 3. Scroll completo (lazy load)  │
│    Cargar TODOS los anuncios    │
│    Extraer IDs de "Gestionar"   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 4. Por cada anuncio:            │
│    a. Ir a /item/{ID}/_/manage  │
│    b. Cerrar popup Destacados   │
│    c. Clic orgánico en Renovar  │
│    d. Esperar confirmación      │
│    e. Pausa aleatoria 30-90s    │
│                                 │
│    Cada N anuncios: descanso    │
│    de 30 min entre ráfagas      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 5. Reintentar fallidos          │
│    (hasta MAX_RONDAS veces)     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ 6. Resumen final                │
└─────────────────────────────────┘
```

### Anti-detección

| Capa | Técnica | Detalle |
|---|---|---|
| **Mouse** | Movimiento orgánico | 5-12 pasos con curva ease-in-out + ruido ±5px |
| **Pausas** | Aleatorias | 30-90s entre anuncios, 4-7s carga de página, 0.3-0.8s antes de clic |
| **Ráfagas** | Límite por sesión | Default 5 anuncios, luego descanso de 30 min |
| **Cloudflare** | Pausa inteligente | 2-5 min de espera, NO sys.exit(). Max 3 consecutivos |
| **Huellas** | Limpieza | `navigator.webdriver = undefined`, elimina `__playwright` |
| **Scroll** | Suave | `behavior: 'smooth'` con pausas entre scrolls |

### Manejo de Cloudflare (vs script viejo)

**Script viejo:**
```python
sys.exit(1)  # ← MATA el script inmediatamente
```

**Script nuevo:**
```python
# 1. Detecta Cloudflare
# 2. Pausa 2-5 minutos (no hace nada)
# 3. Intenta navegar a /account/ads
# 4. Si se resolvió → continúa
# 5. Si sigue → después de 3 consecutivos, para limpiamente
# 6. Los anuncios pendientes quedan como "fallidos" para reintentar
```

## Guía de Uso

### 1. Preparar Chrome

```bash
# Abrir Chrome con debugging
google-chrome --remote-debugging-port=9222

# O con perfil separado
google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.config/chrome-debug
```

Luego en Chrome:
1. Ir a `revolico.com`
2. Iniciar sesión
3. Resolver cualquier CAPTCHA de Cloudflare
4. Dejar Chrome abierto

### 2. Ejecutar el script

```bash
# Uso básico — renovar todo
python3 scripts-opus/renovar_v2.py

# Probar con 1 solo anuncio
python3 scripts-opus/renovar_v2.py --limite 1

# Probar con 5 anuncios
python3 scripts-opus/renovar_v2.py --limite 5

# Configurar ráfagas: 3 anuncios, descanso 45 min
python3 scripts-opus/renovar_v2.py --rafaga 3 --descanso 45

# Usar otro puerto de Chrome
python3 scripts-opus/renovar_v2.py --port 9223

# Todo junto
python3 scripts-opus/renovar_v2.py --port 9222 --rafaga 5 --descanso 30 --limite 50 --max-rondas 3
```

### 3. Parámetros

| Parámetro | Default | Descripción |
|---|---|---|
| `--port` | 9222 | Puerto de Chrome debug |
| `--rafaga` | 5 | Anuncios a renovar antes de descansar |
| `--descanso` | 30 | Minutos de descanso entre ráfagas |
| `--limite` | 0 (todos) | Máximo de anuncios a procesar |
| `--max-rondas` | 5 | Rondas de reintentos para fallidos |

### 4. Configuración avanzada

Las pausas y otros parámetros se pueden ajustar editando las constantes al inicio de [`renovar_v2.py`](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/renovar_v2.py):

```python
PAUSA_ENTRE_ANUNCIOS = (30.0, 90.0)      # Min y max segundos
PAUSA_CARGA_PAGINA = (4.0, 7.0)
PAUSA_CLOUDFLARE = (120, 300)             # 2-5 minutos
MAX_CLOUDFLARES_SEGUIDOS = 3
```

## Diferencias con el script viejo

| Característica | `renovar_revolico-antifallos.py` | `renovar_v2.py` |
|---|---|---|
| **URL de cuenta** | `/account` | `/account/ads` |
| **Selector de renovar** | `button:has-text("Renovar anuncio")` | `button:has-text("Renovar")` + fallbacks |
| **Ante Cloudflare** | `sys.exit(1)` | Pausa 2-5 min + reintento |
| **Mouse** | Sin movimiento | Movimiento orgánico con curva |
| **Pausas entre anuncios** | 2 seg fijos | 30-90 seg aleatorios |
| **Popup Destacados** | 4 selectores | 6 selectores + Escape + clic overlay |
| **Scroll** | `window.scrollTo` instantáneo | `window.scrollBy` suave |
| **Ráfagas** | Sin descanso | 5 anuncios + 30 min descanso |
| **Limpieza huellas** | No | `navigator.webdriver`, `__playwright` |
| **Argumentos CLI** | Solo `--port=` | argparse completo |
| **Resumen** | Básico | Con duración, hora inicio/fin |

---

## Cambio de estrategia: Eliminar + Republicar

La renovación de Revolico devuelve error ("Ha ocurrido un error. Por favor, inténtalo de nuevo.") tanto con el script como manualmente. **Nueva estrategia**: eliminar los anuncios y republicarlos con `publicar_v2.py`.

Ciclo: **publicar → esperar días → eliminar → republicar → repetir**

---

## Script: eliminar_anuncios.py

Elimina **solo** los anuncios que están marcados como `"publicado"` en el sistema de estado (`estado/cuentas/{email}.json`). No toca anuncios publicados manualmente.

### Flujo de eliminación en Revolico

El proceso de eliminar tiene 2 modales que **a veces aparecen ambos, a veces solo uno**:

1. **Modal 1**: "¿Estás seguro que deseas eliminar este anuncio?" → Botones: **Eliminar** (rojo) / Cancelar
2. **Modal 2**: "¿A quién le vendiste este anuncio?" → Seleccionar **"Eliminar sin indicar comprador"** → Botones: **Eliminar** (rojo) / Cancelar

El script maneja todas las combinaciones automáticamente y verifica que el anuncio realmente se eliminó.

### Uso

```bash
# Preview (ver qué eliminaría)
python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com --preview

# Eliminar 1 para probar
python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com --limite 1

# Eliminar todos los publicados de una cuenta
python3 scripts-opus/eliminar_anuncios.py --email cuenta@gmail.com
```

### Parámetros

| Parámetro | Default | Descripción |
|---|---|---|
| `--email` | (requerido) | Email de la cuenta |
| `--preview` | false | Solo mostrar, no eliminar |
| `--limite` | 0 (todos) | Máximo de anuncios a eliminar |
| `--port` | 9222 | Puerto de Chrome debug |
| `--rafaga` | 500 | Anuncios por ráfaga |
| `--descanso` | 30 | Minutos de descanso entre ráfagas |

### Qué hace con el estado

Cuando elimina un anuncio, lo marca como `"estado": "eliminado"` y añade `"fecha_eliminacion"`.

---

## Script: verificar_publicados.py

Verifica cuáles anuncios marcados como `"publicado"` en el sistema de estado **realmente siguen vivos** en Revolico. Detecta si Revolico está borrando anuncios silenciosamente.

### Uso

```bash
# Verificar una cuenta
python3 scripts-opus/verificar_publicados.py --email cuenta@gmail.com

# Verificar TODAS las cuentas
python3 scripts-opus/verificar_publicados.py --todas
```

### Qué hace

- Navega a la URL de cada anuncio publicado
- Si no existe (404, redirect, "no encontrado") → marca como `"borrado_por_revolico"`
- Muestra resumen: cuántos vivos, cuántos borrados, % de anuncios eliminados por Revolico

### Estados posibles de una publicación

| Estado | Significado |
|---|---|
| `pendiente` | Asignado pero no publicado aún |
| `publicado` | Publicado exitosamente en Revolico |
| `fallido` | Falló al publicar |
| `eliminado` | Eliminado por `eliminar_anuncios.py` |
| `borrado_por_revolico` | Revolico lo borró (detectado por `verificar_publicados.py`) |

---

## Errores comunes

| Error | Causa | Solución |
|---|---|---|
| `No se pudo conectar a Chrome` | Chrome no está abierto con debugging | `google-chrome --remote-debugging-port=9222` |
| 3 Cloudflares seguidos | La sesión está "quemada" | Resolver captcha manualmente, esperar 1h |
| No se encontró botón Renovar | Ya renovado hoy o cambio en UI | Normal si ya renovaste |
| No se encontró botón Eliminar | Cambio en UI de Revolico | Verificar manualmente en Chrome |
| 0 anuncios encontrados | No logueado en Revolico | Verificar sesión en Chrome |
| No hay publicados para eliminar | Ya se eliminaron todos | Verificar `estado/cuentas/{email}.json` |

## Estructura de archivos

```
renovar-anuncios/
├── scripts-opus/
│   ├── renovar_v2.py               ← v1.1.0 (renovar — no funciona por bug de Revolico)
│   ├── eliminar_anuncios.py        ← v1.1.0 (eliminar publicados)
│   ├── verificar_publicados.py     ← v1.1.0 (verificar qué sigue vivo)
│   ├── mutar_imagenes.py           ← v1.0.0
│   ├── preparar_cuentas.py         ← v1.0.0
│   ├── publicar_v2.py              ← v1.0.0
│   └── descripciones/              ← v1.0.0
├── estado/
│   ├── registro_global.json
│   └── cuentas/
│       ├── alejandroantigravity1@gmail.com.json
│       ├── alejandroantigravity2@gmail.com.json
│       ├── catalogo.ventas.cuba@gmail.com.json
│       └── catalogo2.ventas.cuba@gmail.com.json
├── renovar_revolico-antifallos.py  ← VIEJO (obsoleto)
├── ideas-versiones/
│   ├── v1.0.0/                     ← Documentación v1.0.0
│   └── v1.1.0/
│       ├── idea1.md                ← Idea original (renovar)
│       ├── idea2.md                ← Cambio de estrategia (eliminar+republicar)
│       ├── imagenes/               ← Capturas del flujo
│       └── documentacion-v1.1.0.md ← ESTA DOCUMENTACIÓN
└── ...
```
