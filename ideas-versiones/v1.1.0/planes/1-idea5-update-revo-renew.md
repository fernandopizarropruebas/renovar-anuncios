# Plan 1 — Actualizar RevoRenew (Extensión de Chrome)

**Fuente:** [idea5-update-revo-renew.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/idea5-update-revo-renew.md)
**Prioridad:** 🔴 Alta (primera tarea del orden)

---

## Contexto

RevoRenew es una extensión de Chrome de terceros (con licencia remota) que renueva anuncios automáticamente. El código está ofuscado pero se tiene completo. Tiene 3 problemas principales:

1. **Selectores obsoletos**: Revolico cambió su UI (botón "Renovar anuncio" → "Renovar", URL `/account` → `/account/ads`, nueva barra de acciones inferior, etc.)
2. **No reintenta fallidos/skips**: Si un anuncio da error o skip, no vuelve a intentarlo
3. **Confirmación de renovación deficiente**: A veces no confirma bien que se renovó y salta al siguiente

---

## Pasos del Plan

### Paso 1 — Crear copia del código original
- **Qué**: Copiar toda la carpeta `anterior-v1.0.0/RevoRenew last update/` a una nueva ubicación (ej: `scripts-opus/RevoRenew-v2/`)
- **Por qué**: Preservar el original intacto como pide el usuario
- **Archivos**: Copiar `manifest.json`, `background.js`, `content.js`, `popup.js`, `popup.html`, `popup.css`, `assets/`

### Paso 2 — Desofuscar el código
- **Qué**: Desofuscar `background.js`, `content.js`, `popup.js` para poder editarlos
- **Cómo**: Usar herramientas de beautify/deobfuscation (prettier + análisis manual de funciones `_0x...`)
- **Resultado**: Código legible con nombres de variables y funciones claros

### Paso 3 — Bypass de licencia
- **Qué**: Eliminar la dependencia del servidor remoto `revorenew.timeklip.com`
- **Cómo**: 
  - Localizar la función `callApi` en `background.js`
  - Hacer que cada validación devuelva `{ ok: true, licenseStatus: "valid" }`
  - Eliminar o anular las llamadas de verificación de token periódicas
  - Remover el chequeo de `expiresAt`
- **Resultado**: Extensión funciona sin internet y sin licencia

### Paso 4 — Actualizar selectores a la nueva UI de Revolico (Sep 2026)
- **Qué**: Actualizar todos los selectores CSS/texto en `content.js` según los cambios documentados
- **Cambios clave**:

| Selector viejo | Selector nuevo |
|---|---|
| URL `/account` | URL `/account/ads` |
| `button "Renovar anuncio"` | `button "Renovar"` (barra de acciones inferior) |
| Popup destacados (1 variante) | Popup destacados (2 variantes: `button[aria-label="Close"]`, `button[aria-label="Cerrar"]`, `[data-slot="dialog-close"]`) |
| Confirmación genérica | `text="Tu anuncio fue renovado."` + `button "Entendido"` |

### Paso 5 — Implementar sistema de reintentos
- **Qué**: Añadir una segunda pasada para los anuncios que fallaron o fueron saltados
- **Cómo**:
  - Mantener un array `fallidos[]` con los IDs de anuncios que dieron error o skip
  - Al terminar la primera pasada, iniciar una ronda de reintentos
  - Configurable: máximo de rondas de reintento (default: 3)
- **Dónde**: En `content.js`, en la lógica del bucle principal de renovación

### Paso 6 — Mejorar confirmación de renovación
- **Qué**: Verificar correctamente que el anuncio se renovó antes de pasar al siguiente
- **Cómo**:
  - Después de clic en "Renovar", esperar hasta 15 segundos por **uno de estos indicadores**:
    1. ✅ Aparece texto `"Tu anuncio fue renovado."` → **ÉXITO**
    2. ✅ Desaparece el botón "Renovar" de la barra de acciones → **ÉXITO**
    3. ❌ Aparece texto `"Ha ocurrido un error"` → **FALLO** (agregar a fallidos)
    4. ❌ Aparece texto `"La verificación falló"` → **FALLO** (Cloudflare)
    5. ⏱️ Timeout (15s sin ningún indicador) → **FALLO** (agregar a fallidos)
  - Si es éxito y aparece botón "Entendido", clicarlo antes de continuar

### Paso 7 — Actualizar `manifest.json`
- **Qué**: Actualizar permisos y URLs permitidas si cambió algo
- **Verificar**:
  - `host_permissions` incluya `revolico.com`
  - `content_scripts.matches` apunte a las URLs correctas
  - Versión del manifest

### Paso 8 — Actualizar `popup.html` / `popup.js`
- **Qué**: Que el panel de la extensión muestre:
  - Contador de renovados / fallidos / reintentos
  - Estado actual (renovando, esperando, terminado)
  - Lista de fallidos con opción de reintentar

### Paso 9 — Testing
- **Qué**: Probar la extensión actualizada
- **Cómo**:
  1. Cargar como extensión sin empaquetar en Chrome (`chrome://extensions` → modo developer → Load unpacked)
  2. Ir a `revolico.com`, loguearse
  3. Probar con 1-2 anuncios primero
  4. Verificar que detecta correctamente éxito/fallo
  5. Verificar que reintenta los fallidos
  6. Verificar que funciona sin servidor de licencia

---

## Archivos involucrados

| Archivo | Acción |
|---|---|
| `scripts-opus/RevoRenew-v2/manifest.json` | **NUEVO** — Copia actualizada |
| `scripts-opus/RevoRenew-v2/background.js` | **NUEVO** — Desofuscado + bypass licencia |
| `scripts-opus/RevoRenew-v2/content.js` | **NUEVO** — Desofuscado + selectores nuevos + reintentos + confirmación |
| `scripts-opus/RevoRenew-v2/popup.js` | **NUEVO** — Desofuscado + UI actualizada |
| `scripts-opus/RevoRenew-v2/popup.html` | **NUEVO** — Copia actualizada |
| `scripts-opus/RevoRenew-v2/popup.css` | **NUEVO** — Copia (posibles ajustes) |

---

## Riesgos y consideraciones

- ⚠️ **Desofuscación**: El código está ofuscado con funciones tipo `_0x3d14c9`. La desofuscación puede ser laboriosa pero es necesaria para entender y modificar la lógica
- ⚠️ **Detección**: La extensión fue detectada recientemente por Cloudflare. Hay que evaluar si los mismos patrones de anti-detección del script de Playwright (pausas largas, movimiento orgánico) se pueden implementar en la extensión
- 💡 **Alternativa**: Si la desofuscación resulta demasiado compleja, se podría reescribir la extensión desde cero usando la lógica del `renovar_v2.py` como base


comentarios:
respecto al tema de la deteccion bueno eso parece q ya se resolvio era mas bien un problema de revolico q cuando renovabas varios anuncios no te dejaba renovar mas