# Plan 4 — Bug: renovar_v2.py (Scroll incompleto + Detección de éxito)

**Fuente:** [renovar_v2_1.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/bugs/renovar_v2/renovar_v2_1.md)
**Prioridad:** 🟡 Media (cuarta tarea del orden)

---

## Bugs reportados

### Bug 1: Scroll no carga todos los anuncios
- **Síntoma**: En una cuenta con 450 anuncios, solo detecta los primeros ~100
- **Causa**: La función `cargar_todos_los_anuncios()` usa `scroll_suave()` que hace scroll de 400-800px por paso, pero `MAX_SCROLLS_SIN_CAMBIO = 4` es muy bajo. Los anuncios se cargan por lazy loading y a veces tardan más de 4 scrolls en aparecer
- **Otra causa**: El `ids_actuales == ids_vistos` compara sets completos. Si un scroll no carga nada nuevo (porque el lazy load tarda), se incrementa `sin_cambios` prematuramente

### Bug 2: No detecta cuando renueva exitosamente
- **Síntoma**: Muestra `❌ Falló — se reintentará` aunque SÍ renovó el anuncio
- **Causa**: El `wait_for_selector` busca el texto `"Tu anuncio fue renovado."` pero la confirmación puede ser:
  - Un toast/notificación temporal que aparece y desaparece rápidamente
  - El botón "Renovar" desaparece de la barra de acciones (indicando que ya se renovó)
  - Un cartelito verde breve que dice "Renovado" (según la imagen del bug)
- **El selector actual es incorrecto**:
  ```python
  # MALO: Busca ambos textos como un solo selector combinado
  await page.wait_for_selector(
      'text="Tu anuncio fue renovado.", text="La verificación falló"',
      timeout=15000,
  )
  ```
  Esto NO funciona como un "OR" en Playwright. Se necesita usar `page.wait_for_selector` con selectores separados o `page.expect_event`.

---

## Pasos del Plan

### Paso 1 — Fix del scroll para cargar todos los anuncios

- **Archivo**: [renovar_v2.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/renovar_v2.py)
- **Función**: `cargar_todos_los_anuncios()` (línea ~275)
- **Cambios**:

  1. **Aumentar `MAX_SCROLLS_SIN_CAMBIO`** de 4 a 8:
     ```python
     MAX_SCROLLS_SIN_CAMBIO = 8
     ```
  
  2. **Actualizar correctamente `ids_vistos`**: El código actual reemplaza `ids_vistos` por `ids_actuales` en vez de hacer unión. Si un scroll pierde algunos elementos visibles (porque salieron del viewport), se pierden IDs:
     ```python
     # Antes (línea ~308-309):
     sin_cambios = 0
     ids_vistos = ids_actuales  # ← BUG: reemplaza en vez de unir
     
     # Después:
     sin_cambios = 0
     ids_vistos = ids_vistos | ids_actuales  # ← Unión acumulativa
     ```
  
  3. **Añadir scroll final al fondo absoluto** para asegurar que se llegó al final:
     ```python
     # Después del bucle while, un scroll final para confirmar
     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
     await asyncio.sleep(3)
     # Una última extracción
     links = await page.query_selector_all('a:has-text("Gestionar")')
     for el in links:
         href = await el.get_attribute("href")
         if href:
             match = re.search(r'-(\d+)\?', href) or re.search(r'/item/(\d+)', href)
             if match:
                 ids_vistos.add(match.group(1))
     ```
  
  4. **Aumentar pausa entre scrolls** para dar tiempo al lazy loading:
     ```python
     # Antes:
     PAUSA_SCROLL = (0.8, 1.5)
     
     # Después:
     PAUSA_SCROLL = (1.5, 3.0)
     ```

### Paso 2 — Fix de detección de renovación exitosa

- **Archivo**: [renovar_v2.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/renovar_v2.py)
- **Función**: `renovar_anuncio()` (línea ~322)
- **Cambios**:

  1. **Reemplazar el `wait_for_selector` roto** por un polling manual con múltiples indicadores:
     ```python
     # ANTES (línea ~413-417) — SELECTOR INCORRECTO:
     await page.wait_for_selector(
         'text="Tu anuncio fue renovado.", text="La verificación falló"',
         timeout=15000,
     )
     
     # DESPUÉS — Polling con múltiples indicadores:
     renovacion_exitosa = False
     renovacion_fallida = False
     
     for _ in range(15):  # 15 intentos × 1s = 15s timeout
         await asyncio.sleep(1.0)
         
         # Indicador 1: Texto de éxito
         exito = await page.query_selector('text="Tu anuncio fue renovado."')
         if exito:
             renovacion_exitosa = True
             break
         
         # Indicador 2: Toast/notificación de "Renovado"
         toast = await page.query_selector('text="Renovado"')
         if toast:
             renovacion_exitosa = True
             break
         
         # Indicador 3: El botón "Renovar" desapareció (ya se renovó)
         boton_sigue = False
         for sel in ['button:has-text("Renovar")', 'button:text-is("Renovar")']:
             el = await page.query_selector(sel)
             if el:
                 try:
                     if await el.is_visible():
                         boton_sigue = True
                         break
                 except:
                     pass
         if not boton_sigue:
             # El botón ya no está → se renovó exitosamente
             renovacion_exitosa = True
             break
         
         # Indicador 4: Error
         error = await page.query_selector('text="La verificación falló"')
         error2 = await page.query_selector('text="Ha ocurrido un error"')
         if error or error2:
             renovacion_fallida = True
             break
     ```

  2. **Actualizar la sección de verificación de resultado** (línea ~422-448):
     ```python
     # Usar las variables del polling en vez de query_selector de nuevo
     if renovacion_exitosa:
         # Cerrar modal de confirmación si existe
         try:
             entendido = await page.query_selector('button:has-text("Entendido")')
             if entendido and await entendido.is_visible():
                 await asyncio.sleep(random.uniform(0.5, 1.0))
                 await page.evaluate("el => el.click()", entendido)
                 await asyncio.sleep(random.uniform(0.5, 1.0))
         except Exception:
             pass
         return True
     
     if renovacion_fallida:
         return False
     
     # Cloudflare
     if await detectar_cloudflare(page):
         return "cloudflare"
     
     # Timeout sin indicador claro → fallo
     return False
     ```

### Paso 3 — Mejorar detección de "Ha ocurrido un error"

- **Qué**: Añadir detección del mensaje de error de Revolico que dice "Ha ocurrido un error. Por favor, inténtalo de nuevo."
- **Dónde**: En la verificación de resultado de `renovar_anuncio()`
- **Acción**: Cuando se detecta este error, marcar como fallido para reintentar

### Paso 4 — Testing

1. Probar con una cuenta que tenga **muchos anuncios** (450+) → verificar que los carga todos
2. Probar renovar 3-5 anuncios → verificar que detecta correctamente:
   - ✅ Renovación exitosa (toast, desaparición del botón)
   - ❌ Error de Revolico ("Ha ocurrido un error")
   - ⏭️ Ya renovado hoy
3. Verificar que los fallidos se reintentan en la ronda siguiente

---

## Archivos involucrados

| Archivo | Acción |
|---|---|
| [renovar_v2.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/renovar_v2.py) | **MODIFICAR** — Fix scroll + detección de éxito |

---

## Resumen de cambios

```diff
# Constantes:
- MAX_SCROLLS_SIN_CAMBIO = 4
+ MAX_SCROLLS_SIN_CAMBIO = 8

- PAUSA_SCROLL = (0.8, 1.5)
+ PAUSA_SCROLL = (1.5, 3.0)

# cargar_todos_los_anuncios():
- ids_vistos = ids_actuales
+ ids_vistos = ids_vistos | ids_actuales

# renovar_anuncio():
- await page.wait_for_selector(
-     'text="Tu anuncio fue renovado.", text="La verificación falló"',
-     timeout=15000,
- )
+ # Polling manual con múltiples indicadores de éxito/fallo
+ for _ in range(15):
+     # Check: texto éxito, toast "Renovado", botón desapareció, error
```
