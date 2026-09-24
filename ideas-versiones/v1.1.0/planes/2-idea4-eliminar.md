# Plan 2 — Eliminar Recursos al Eliminar Anuncios

**Fuente:** [idea4-eliminar.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/idea4-eliminar.md)
**Prioridad:** 🟠 Alta (segunda tarea del orden)

---

## Contexto

Cuando se eliminan anuncios de Revolico (con `eliminar_anuncios.py`), las imágenes y descripciones que se usaron quedan marcadas como "quemadas" (usadas globalmente). Esto significa que al volver a asignar productos a una cuenta, esas variantes no se reutilizan, **pero tampoco se liberan**. El objetivo es:

1. Que al eliminar anuncios de Revolico, también se eliminen las variantes de imagen y descripción usadas
2. Que los scripts de imágenes y descripciones tengan opción de eliminar variantes generadas
3. Que `verificar_publicados.py` cuando detecte un anuncio despublicado por Revolico, también elimine sus recursos
4. Todo esto para que al reasignar, se generen/usen variantes frescas y no se repitan nunca

---

## Pasos del Plan

### Paso 1 — Añadir función de eliminar recursos en `preparar_cuentas.py`

- **Qué**: Añadir un subcomando para eliminar variantes de imágenes y/o descripciones generadas
- **Archivo**: [preparar_cuentas.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/preparar_cuentas.py)
- **Nuevo subcomando**: `eliminar-variantes`
- **Uso**:
  ```bash
  # Eliminar variantes de un producto específico
  python3 scripts-opus/preparar_cuentas.py eliminar-variantes --producto buros
  
  # Eliminar variantes de todos los productos
  python3 scripts-opus/preparar_cuentas.py eliminar-variantes --todos
  
  # Solo eliminar imágenes
  python3 scripts-opus/preparar_cuentas.py eliminar-variantes --todos --solo-imagenes
  
  # Solo eliminar descripciones
  python3 scripts-opus/preparar_cuentas.py eliminar-variantes --todos --solo-descripciones
  ```
- **Lógica**:
  - Recorrer `productos/{producto}/imagenes/variantes_*/` y borrar los archivos de variantes
  - Recorrer `productos/{producto}/descripciones/` y borrar los archivos `variante_*.txt`
  - NO borrar las imágenes originales ni `descripcion_base.txt`
  - Mostrar resumen de cuántos archivos se eliminaron

### Paso 2 — Añadir función de eliminar variantes en `mutar_imagenes.py`

- **Qué**: Añadir opción `--eliminar` al script standalone de mutación de imágenes
- **Archivo**: [mutar_imagenes.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/mutar_imagenes.py)
- **Uso**:
  ```bash
  # Eliminar variantes de una imagen
  python3 scripts-opus/mutar_imagenes.py productos/buros/imagenes/ --eliminar
  ```
- **Lógica**: Borrar contenido de las carpetas `variantes_*/`

### Paso 3 — Crear función helper `eliminar_recursos_publicacion()`

- **Qué**: Función reutilizable que elimina los archivos de imagen y descripción usados por una publicación específica
- **Dónde**: Puede ir en un módulo compartido o directamente en `eliminar_anuncios.py`
- **Parámetros**: `producto` (str), `imagenes_usadas` (list), `descripcion_usada` (str)
- **Lógica**:
  ```python
  def eliminar_recursos_publicacion(producto, imagenes_usadas, descripcion_usada):
      """
      Elimina del disco las variantes de imagen y descripción
      usadas por una publicación eliminada.
      """
      productos_dir = BASE_DIR / "productos" / producto
      
      # Eliminar imágenes usadas
      for img_rel in imagenes_usadas:
          img_path = productos_dir / "imagenes" / img_rel
          if img_path.exists():
              img_path.unlink()
              print(f"      🗑️ Imagen eliminada: {img_rel}")
      
      # Eliminar descripción usada
      if descripcion_usada:
          desc_path = productos_dir / "descripciones" / descripcion_usada
          if desc_path.exists():
              desc_path.unlink()
              print(f"      🗑️ Descripción eliminada: {descripcion_usada}")
  ```

### Paso 4 — Integrar en `eliminar_anuncios.py`

- **Qué**: Cuando un anuncio se elimina exitosamente de Revolico, también eliminar sus recursos del disco
- **Archivo**: [eliminar_anuncios.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/eliminar_anuncios.py)
- **Dónde**: Después de la línea `cuenta = marcar_como_eliminado(cuenta, anuncio["producto"])` (línea ~736)
- **Cambio**:
  ```python
  # Después de marcar como eliminado exitosamente:
  cuenta = marcar_como_eliminado(cuenta, anuncio["producto"])
  guardar_cuenta(args.email, cuenta)
  
  # NUEVO: Eliminar recursos (imágenes + descripción) usados
  pub_data = next(
      (p for p in cuenta["publicaciones"]
       if p["producto"] == anuncio["producto"] and p.get("estado") == "eliminado"),
      None
  )
  if pub_data:
      eliminar_recursos_publicacion(
          pub_data["producto"],
          pub_data.get("imagenes_usadas", []),
          pub_data.get("descripcion_usada")
      )
  ```

### Paso 5 — Integrar en `verificar_publicados.py`

- **Qué**: Cuando `verificar_publicados.py` detecta que Revolico borró un anuncio, también eliminar los recursos usados
- **Archivo**: [verificar_publicados.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/verificar_publicados.py)
- **Dónde**: Después de marcar como `borrado_por_revolico` (línea ~356)
- **Cambio**:
  ```python
  if resultado == "borrado":
      borrados += 1
      productos_borrados.append({"producto": item["producto"], "id": item["item_id"]})
      
      # Actualizar estado
      for p in cuenta.get("publicaciones", []):
          if p["producto"] == item["producto"] and p.get("estado") == "publicado":
              p["estado"] = "borrado_por_revolico"
              p["fecha_deteccion_borrado"] = datetime.now().isoformat()
              
              # NUEVO: Eliminar recursos usados
              eliminar_recursos_publicacion(
                  p["producto"],
                  p.get("imagenes_usadas", []),
                  p.get("descripcion_usada")
              )
              break
      guardar_cuenta(email, cuenta)
  ```

### Paso 6 — Añadir flag `--conservar-recursos` como seguridad

- **Qué**: Flag opcional en `eliminar_anuncios.py` y `verificar_publicados.py` para NO borrar recursos (por si alguien quiere preservarlos)
- **Default**: Eliminar recursos (comportamiento nuevo)
- **Uso**:
  ```bash
  # Eliminar anuncio PERO conservar sus imágenes/descripciones
  python3 scripts-opus/eliminar_anuncios.py --email x@y.com --conservar-recursos
  ```

### Paso 7 — Testing

- **Verificaciones**:
  1. Eliminar 1 anuncio → confirmar que la variante de imagen y la variante de descripción se borraron del disco
  2. Verificar que la imagen original NO se borró
  3. Verificar que `descripcion_base.txt` NO se borró
  4. Reasignar el mismo producto a la cuenta → confirmar que se genera/usa una variante nueva
  5. Con `--conservar-recursos` → confirmar que los archivos NO se borran
  6. `verificar_publicados.py` detecta un borrado por Revolico → confirmar que también limpia recursos

---

## Archivos involucrados

| Archivo | Acción |
|---|---|
| [eliminar_anuncios.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/eliminar_anuncios.py) | **MODIFICAR** — Integrar eliminación de recursos |
| [verificar_publicados.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/verificar_publicados.py) | **MODIFICAR** — Integrar eliminación de recursos al detectar borrado |
| [preparar_cuentas.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/preparar_cuentas.py) | **MODIFICAR** — Nuevo subcomando `eliminar-variantes` |
| [mutar_imagenes.py](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/mutar_imagenes.py) | **MODIFICAR** — Opción `--eliminar` |

---

## Diagrama de flujo

```
Eliminar anuncio de Revolico
         │
         ▼
  ┌──────────────────┐
  │ Marcar estado     │
  │ "eliminado" o     │
  │ "borrado_por_     │
  │  revolico"        │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Leer imagenes_    │
  │ usadas y          │
  │ descripcion_usada │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Borrar archivos   │
  │ del disco:        │
  │ - variante_img    │
  │ - variante_desc   │
  └────────┬─────────┘
           │
           ▼
  Al reasignar → se usan
  variantes frescas (o se
  regeneran si no quedan)
```
