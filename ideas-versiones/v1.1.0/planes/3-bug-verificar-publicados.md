# Plan 3 — Bug: verificar_publicados.py (Falsos positivos)

**Fuente:** [verificar_publicados.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/bugs/verificar_publicados/verificar_publicados.md)
**Prioridad:** 🟡 Media (tercera tarea del orden)

---

## Contexto del Bug

El script `verificar_publicados.py` reporta **125 vivos** cuando en realidad Revolico muestra solo **119 anuncios** activos en `/account/ads`. La doble verificación marca como "Falsa Alarma" (vivo) anuncios que en realidad están despublicados.

### Causa raíz identificada

La doble verificación navega a la URL `url_revolico` del estado JSON. Estas URLs a veces tienen formato `/item/{ID}/_/manage?action=created`. El problema es:

1. **URLs con `?action=created`**: Cuando Revolico recibe una URL con `?action=created` de un anuncio que el usuario no tiene permiso de ver, puede mostrar un mensaje de "No tienes permiso" en lugar de "Anuncio despublicado". El script no reconoce "No tienes permiso" como indicador de borrado → cuenta como "vivo" erróneamente.
2. **El script compara URLs base**: El script compara `base_expected != current_base` (sin query params), pero si Revolico no redirige sino que muestra una página de error con la misma base URL, pasa la verificación.

### Comportamiento deseado del usuario

- La URL usada en la doble verificación debe ir **solo hasta `/manage`** (sin `?action=created`), para no delatar que es un bot
- Reconocer "No tienes permiso" como indicador de borrado/despublicado

---

## Pasos del Plan

### Paso 1 — Limpiar URL en doble verificación (quitar `?action=created`)

- **Archivo**: [verificar_publicados.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/verificar_publicados.py)
- **Dónde**: Función `doble_verificacion()` (línea ~208)
- **Cambio**: Antes de navegar, strip query params de la URL:
  ```python
  # Antes:
  url = url_revolico or f"https://www.revolico.com/item/{item_id}/_/manage"
  
  # Después:
  url_base = (url_revolico or f"https://www.revolico.com/item/{item_id}/_/manage")
  url = url_base.split('?')[0]  # Quitar ?action=created u otros params
  ```

### Paso 2 — Añadir "No tienes permiso" a indicadores de borrado

- **Archivo**: [verificar_publicados.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/verificar_publicados.py)
- **Dónde**: Lista `indicadores_borrado` en `doble_verificacion()` (línea ~231)
- **Cambio**: Añadir nuevos indicadores:
  ```python
  indicadores_borrado = [
      "anuncio despublicado",
      "este anuncio no existe",
      "anuncio no encontrado",
      "no se encontró",
      "ha sido eliminado",
      "no tienes permiso",        # NUEVO
      "no tiene permiso",         # NUEVO (variante)
      "acceso denegado",          # NUEVO
      "access denied",            # NUEVO (inglés)
  ]
  ```

### Paso 3 — Verificar que el anuncio realmente se ve como "publicado"

- **Qué**: En la doble verificación, no basta con que la URL cargue. Verificar que la página muestra **contenido real del anuncio** (título, precio, descripción, botones de gestionar)
- **Lógica mejorada**:
  ```python
  # Si cargó la URL sin errores, verificar que tiene contenido real
  # Un anuncio vivo debe tener: botón Editar, botón Renovar, etc.
  tiene_contenido_real = await page.query_selector(
      'button:has-text("Editar"), button:has-text("Renovar"), a:has-text("Editar")'
  )
  if tiene_contenido_real:
      print(f"      ✅ Falsa Alarma: Anuncio con contenido real. Sigue vivo.")
      return "vivo"
  else:
      # La URL cargó pero no tiene contenido de anuncio → sospechoso
      print(f"      ⚠️  URL cargó pero sin contenido de anuncio, verificando texto...")
      # Revisar indicadores de borrado como antes
  ```

### Paso 4 — Mejorar el scroll para cargar TODOS los anuncios

- **Qué**: Actualmente `cargar_todos_los_ids()` usa `window.scrollTo(0, document.body.scrollHeight)` (scroll instantáneo). Usar scroll suave e incrementar los intentos sin cambio
- **Cambio**:
  ```python
  # Antes (línea 185):
  await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
  await asyncio.sleep(2)
  
  # Después:
  await page.evaluate("""
      window.scrollBy({ top: 600, behavior: 'smooth' });
  """)
  await asyncio.sleep(random.uniform(1.5, 3.0))
  ```
- **También**: Aumentar `sin_cambios >= 3` a `sin_cambios >= 5` para dar más oportunidades a que carguen los lazy-loaded

### Paso 5 — Log mejorado para debugging

- **Qué**: Mostrar la URL que se visitó en la doble verificación y el texto de la página si el resultado es "vivo"
- **Para**: Poder debuggear futuros falsos positivos más fácilmente

### Paso 6 — Testing

1. Ejecutar contra la cuenta `alejandroantigravity2@gmail.com`
2. Verificar que el total de "vivos confirmados" coincide con lo que muestra Revolico en `/account/ads`
3. Verificar que los 6 anuncios que antes daban "Falsa Alarma" (Estante, Lampara, Maquinas de hielo, etc.) ahora se detectan correctamente como despublicados
4. Verificar que la URL usada en doble verificación no contiene `?action=created`

---

## Archivos involucrados

| Archivo | Acción |
|---|---|
| [verificar_publicados.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/verificar_publicados.py) | **MODIFICAR** — Fix doble verificación |

---

## Resumen de cambios

```diff
# doble_verificacion():
- url = url_revolico or f"https://www.revolico.com/item/{item_id}/_/manage"
+ url_raw = url_revolico or f"https://www.revolico.com/item/{item_id}/_/manage"
+ url = url_raw.split('?')[0]  # Sin ?action=created

# indicadores_borrado:
  "ha sido eliminado",
+ "no tienes permiso",
+ "no tiene permiso",
+ "acceso denegado",

# cargar_todos_los_ids():
- await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
- await asyncio.sleep(2)
+ await page.evaluate("window.scrollBy({ top: 600, behavior: 'smooth' })")
+ await asyncio.sleep(random.uniform(1.5, 3.0))

- if sin_cambios >= 3:
+ if sin_cambios >= 5:
```
