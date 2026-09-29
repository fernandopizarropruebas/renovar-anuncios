# Plan 5 — Renovar Usando "Editar y Guardar"

**Fuente:** [idea3-renovar-usando-editar.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/idea3-renovar-usando-editar.md)
**Prioridad:** 🟢 Normal (última tarea del orden)

---

## Contexto

El botón "Renovar" de Revolico da errores frecuentes ("Ha ocurrido un error. Por favor, inténtalo de nuevo."). Existe una alternativa: **editar el anuncio y guardarlo sin cambiar nada** tiene el mismo efecto que renovar — el anuncio sube a la parte superior de los resultados como si fuera nuevo.

### Flujo manual (según imágenes del usuario)

1. Ir a `/account/ads` → lista de anuncios
2. Clic en **"Gestionar"** de un anuncio
3. En la página de gestión → clic en **"Editar"**
4. En la página de edición → scroll abajo → clic en **"Guardar"** (sin cambiar nada)
5. Volver a la lista y repetir con el siguiente

### Riesgo

Este método tiene los mismos riesgos que publicar: si Revolico detecta que la imagen o descripción ya existe en otra publicación, puede borrar el anuncio. Sin embargo, como solo se guarda sin cambiar nada, el riesgo es menor que republicar.

---

## Pasos del Plan

### Paso 1 — Crear nuevo script `renovar_editar.py`

- **Ubicación**: `scripts-opus/renovar_editar.py`
- **Base**: Usar la estructura de `renovar_v2.py` como plantilla (misma conexión CDP, anti-detección, ráfagas, Cloudflare)
- **Diferencia clave**: En vez de clic en "Renovar", hace: Editar → Scroll → Guardar

### Paso 2 — Implementar flujo de "Editar y Guardar"

La función principal `renovar_via_editar(page, item_id)` debe hacer:

```python
async def renovar_via_editar(page, item_id):
    """
    Renueva un anuncio usando la estrategia de Editar → Guardar.
    """
    # 1. Navegar a /item/{ID}/_/manage
    url = f"https://www.revolico.com/item/{item_id}/_/manage"
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(random.uniform(4.0, 7.0))
    
    # 2. Verificar Cloudflare
    if await detectar_cloudflare(page):
        return "cloudflare"
    
    await limpiar_huellas(page)
    
    # 3. Cerrar popup de Destacados
    await asyncio.sleep(random.uniform(1.0, 2.0))
    await cerrar_popup_destacados(page)
    
    # 4. Buscar y clicar botón "Editar"
    selectores_editar = [
        'a:has-text("Editar")',
        'button:has-text("Editar")',
        'a:text-is("Editar")',
        'button:text-is("Editar")',
    ]
    
    boton_editar = None
    for sel in selectores_editar:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            boton_editar = el
            break
    
    if not boton_editar:
        print("    ⚠️  No se encontró el botón Editar")
        return None
    
    # Clic orgánico en Editar
    await clic_organico(page, boton_editar)
    
    # 5. Esperar que cargue la página de edición
    await asyncio.sleep(random.uniform(4.0, 7.0))
    
    # Verificar que estamos en la página de edición
    # (debe haber un formulario con campos como título, descripción, etc.)
    formulario = await page.query_selector(
        'input[name="title"], textarea[name="description"], button[type="submit"]'
    )
    if not formulario:
        print("    ⚠️  No se cargó la página de edición")
        return False
    
    # 6. Scroll suave hasta abajo (para llegar al botón Guardar)
    await page.evaluate("""
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    """)
    await asyncio.sleep(random.uniform(2.0, 4.0))
    
    # 7. Buscar y clicar botón "Guardar" / "Publicar" / Submit
    selectores_guardar = [
        'button[type="submit"]',
        'button:has-text("Guardar")',
        'button:has-text("Publicar")',
        'button:has-text("Actualizar")',
    ]
    
    boton_guardar = None
    for sel in selectores_guardar:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            boton_guardar = el
            break
    
    if not boton_guardar:
        print("    ⚠️  No se encontró el botón Guardar/Publicar")
        return False
    
    # Clic orgánico en Guardar
    await clic_organico(page, boton_guardar)
    
    # 8. Esperar confirmación
    await asyncio.sleep(random.uniform(3.0, 5.0))
    
    # Verificar que se guardó (redirect a manage, o mensaje de éxito)
    # ...
    
    return True
```

### Paso 3 — Implementar verificación de éxito al guardar

Después de clicar "Guardar", verificar que se guardó correctamente:

- **Indicador 1**: Redirige a `/item/{ID}/_/manage` (vuelta a la página de gestión) → ✅ Éxito
- **Indicador 2**: Aparece un toast/notificación de éxito ("Anuncio actualizado", "Cambios guardados") → ✅ Éxito
- **Indicador 3**: Sigue en la página de edición con errores visibles → ❌ Fallo
- **Indicador 4**: Cloudflare → reintento

```python
# Verificación de éxito:
for _ in range(10):
    await asyncio.sleep(1.0)
    
    # ¿Redirigió a manage?
    if "/manage" in page.url and "/edit" not in page.url and "/publish" not in page.url:
        return True
    
    # ¿Redirigió a account?
    if "/account" in page.url:
        return True
    
    # ¿Hay mensaje de error?
    error = await page.query_selector('text="Ha ocurrido un error"')
    if error:
        return False
    
    # ¿Cloudflare?
    if await detectar_cloudflare(page):
        return "cloudflare"

# Timeout
return False
```

### Paso 4 — CLI y parámetros

- Mismos parámetros que `renovar_v2.py`:
  ```
  --port      Puerto de Chrome (default: 9222)
  --rafaga    Anuncios por ráfaga (default: 500)
  --descanso  Minutos entre ráfagas (default: 30)
  --limite    Máximo de anuncios (default: 0 = todos)
  --max-rondas  Rondas de reintento (default: 5)
  ```

### Paso 5 — Reutilizar lógica compartida

- Copiar de `renovar_v2.py`:
  - `limpiar_huellas()`
  - `mover_mouse_organico()`
  - `clic_organico()`
  - `scroll_suave()`
  - `detectar_cloudflare()`
  - `manejar_cloudflare()`
  - `cerrar_popup_destacados()`
  - `cargar_todos_los_anuncios()` (con los fixes del Plan 4)
  - `procesar_lista()` (adaptada para usar `renovar_via_editar` en vez de `renovar_anuncio`)

> 💡 **Nota**: Idealmente se debería refactorizar a un módulo compartido `utils_revolico.py`, pero por ahora copiar es más rápido y menos riesgoso.

### Paso 6 — Pausas más largas (precaución)

Este método es más "pesado" que renovar porque:
- Carga la página de edición (carga adicional al servidor)
- Hace submit del formulario (petición POST)

Usar pausas algo más largas:
```python
PAUSA_ENTRE_ANUNCIOS = (45.0, 120.0)  # Más que renovar (30-90)
PAUSA_CARGA_PAGINA = (5.0, 8.0)       # Más que renovar (4-7)
```

### Paso 7 — Testing

1. Probar con `--limite 1` → verificar que:
   - Navega a `/manage`
   - Cierra popup de destacados
   - Clica "Editar"
   - Carga la página de edición
   - Hace scroll hasta abajo
   - Clica "Guardar"
   - Detecta éxito/fallo correctamente
2. Probar con `--limite 5` → verificar flujo completo con pausas
3. Verificar que el anuncio realmente subió a la parte superior en Revolico

---

## Archivos involucrados

| Archivo | Acción |
|---|---|
| `scripts-opus/renovar_editar.py` | **NUEVO** — Script de renovación via editar+guardar |

---

## Diagrama de flujo

```
┌───────────────────────┐
│ 1. /account/ads       │
│    Scroll + extraer   │
│    IDs de "Gestionar" │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 2. /item/{ID}/_/manage│
│    Cerrar popup       │
│    Destacados         │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 3. Clic "Editar"      │
│    → Carga formulario │
│    de edición         │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 4. Scroll hasta abajo │
│    Clic "Guardar"     │
│    (sin cambiar nada) │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│ 5. Verificar éxito    │
│    → Siguiente        │
│    anuncio             │
└───────────────────────┘
```

---

## Consideraciones

- ⚠️ **Detección de duplicados**: Aunque no se cambia nada, al "guardar" Revolico puede re-validar imágenes y descripciones. Si coinciden con otro anuncio activo, podría borrar el anuncio
- ⚠️ **Más lento**: Cada anuncio requiere cargar 2 páginas (manage + edición) en vez de 1
- ✅ **Ventaja**: Funciona aunque el botón "Renovar" esté roto
- 💡 **Puede combinarse**: Usar `renovar_v2.py` como primera opción, y `renovar_editar.py` como fallback para los que dieron error con el método directo
