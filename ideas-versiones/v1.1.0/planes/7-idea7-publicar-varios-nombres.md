# Plan 7 — Publicación con Rotación de Nombres/Títulos Multi-Cuenta

**Fuente:** [idea-7_publicar-varios-nombres.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/idea-7_publicar-varios-nombres.md)  
**Documentación base:** [documentacion_v1.0.0](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.0.0/documentacion_v1.0.0/README.md)  
**Scripts a modificar:** EXCLUSIVAMENTE en `scripts-gemini/` (`preparar_cuentas.py` y `publicar_v2.py`) — NO tocar `scripts-opus/`  
**Estado:** Completado ✅  

---

## 1. Diagnóstico y Análisis del Requerimiento

### 1.1. El Problema Actual
En la carpeta `productos/`, existen carpetas que representan variantes o modelos del mismo tipo de mueble (por ejemplo: `comoda`, `vanity`, `coqueta`, `mesa de maquillaje`, `tocador`). Cada una tiene actualmente en su `producto.json`:
```json
{
  "nombre": "Comoda"
}
```
Cuando el sistema publica este producto en múltiples cuentas (o en sucesivas publicaciones), **siempre usa el mismo título literal ("Comoda")**.

**Inconvenientes:**
1. **Riesgo anti-spam/detección de Revolico:** Títulos idénticos repetidos en distintas cuentas facilitan que los algoritmos de detección sospechen de cuentas vinculadas o contenido duplicado.
2. **Menor alcance comercial:** Los compradores en Cuba buscan con términos alternativos ("tocador", "vanity", "coqueta", "mesa de maquillaje"). Si siempre se publica bajo un solo término, se pierden búsquedas clave.

### 1.2. La Propuesta del Usuario
En [idea-7_publicar-varios-nombres.md](file:///home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.1.0/idea-7_publicar-varios-nombres.md), el usuario plantea:
- Configurar en `producto.json`:
  `"nombre": "Comoda,vanity,tocador,mesa de maquillaje"`
- La primera vez que se publique en una cuenta, usar `"Comoda"`.
- Al publicarse con éxito, pasar `"Comoda"` al final de la cola: `["vanity", "tocador", "mesa de maquillaje", "Comoda"]`.***apunte***:aunq se publiquen sin exito y de error aun asi deben saltar siempre al siguiente nombre, o sea si vanity falla en la cuenta fernandoantigravity1, no debe reusarse en fernandoantigravity2, en esta debe ir tocadores por ejemplo
- La siguiente publicación/cuenta usará `"vanity"`, luego `"tocador"`, etc.
- Cuando se agoten, vuelve a empezar cíclicamente (cola FIFO rotativa).

---

## 2. Análisis Técnico: "¿Se puede hacer o hay algo mejor?"

### 2.1. Evaluación de Alternativas de Diseño

| Criterio | Opción A: Rotación física directa en `producto.json` | Opción B: Rotación sólo por índice matemático en `estado/` | Opción C (Recomendada): **Híbrida Integrada (Asignación + Publicación + Rotación)** |
|---|---|---|---|
| **Mecanismo** | Cada vez que se publica, reescribe `producto.json` rotando el orden del string/lista. | Deja `producto.json` estático; calcula `index = total_asignados % len(nombres)`. | `preparar_cuentas.py asignar` pre-asigna el título rotativo en `cuenta.json` para visibilidad previa, y `publicar_v2.py` lo ejecuta (rotando `producto.json` al confirmar éxito). |
| **Visibilidad en Preview** | ❌ Solo se ve el siguiente título para una cuenta a la vez. Cuentas asignadas previamente no saben su título hasta que la anterior publique. | ⚠️ Se calcula al vuelo, pero `producto.json` no refleja visualmente cuál fue el último usado. | ✅ En `--preview` o `pendientes`, cada cuenta muestra exactamente el título que le corresponde antes de publicar. |
| **Resiliencia ante fallos** | Si falla la publicación a mitad de camino, no debe reescribirse el archivo. | No hay riesgo de alterar archivos fuente. | Seguro: solo rota si la publicación fue confirmada con éxito (`nueva_url != None`). |
| **Compatibilidad hacia atrás** | Requiere que el usuario adapte formatos. | Requiere que el usuario adapte formatos. | 100% retrocompatible: si `"nombre"` es un string simple sin comas, funciona exactamente como hoy sin alterar nada. |

### 2.2. Diseño de la Solución Recomendada (Opción C)

1. **Soporte de dos formatos en `producto.json`:**
   - **Formato Texto con comas (rápido y simple):**
     ```json
     {
       "nombre": "Comoda, vanity, tocador, mesa de maquillaje",
       "precio": "300",
       "moneda": "USD",
       "categoria": ["Ropa y Accesorios", "Belleza, Maquillaje y Perfumes"]
     }
     ```
   - **Formato Lista JSON (estructurado, ideal si un título lleva comas internas):**
     ```json
     {
       "nombre": [
         "Comoda clásica",
         "Vanity moderno",
         "Tocador con espejo",
         "Mesa de maquillaje"
       ]
     }
     ```
   - **Formato Clásico (string único, retrocompatible):**
     ```json
     {
       "nombre": "Comoda"
     }
     ```

2. **Flujo de Asignación en `preparar_cuentas.py asignar`:**
   - Cuando se asigna un producto a una cuenta (`cuentaX@gmail.com`), el script revisa cuántas veces se ha asignado ese producto en las demás cuentas registradas.
   - Selecciona el siguiente nombre según el turno: `nombres[num_asignaciones % len(nombres)]`.
   - Guarda el campo `"titulo_usado"` directamente en el objeto de la publicación en `estado/cuentas/{email}.json`:
     ```json
     {
       "producto": "comoda",
       "titulo_usado": "vanity",
       "imagenes_usadas": ["variantes_foto_01/foto_01_v002.jpg"],
       "descripcion_usada": "variante_002.txt",
       "fecha_asignacion": "2026-10-10T12:00:00",
       "estado": "pendiente",
       "url_revolico": null
     }
     ```

3. **Flujo de Publicación en `publicar_v2.py`:**
   - **Prioridad de Título:**
     1. Si la publicación en `cuenta.json` ya tiene `"titulo_usado"`, usa ese valor.
     2. Si no lo tiene (cuentas ya existentes creadas antes de esta mejora): lee `producto.json`, toma el primer nombre disponible y lo asigna.
   - **Modo Preview (`--preview`):**
     - Muestra el producto indicando:
       `[ 1] comoda                                    300 USD`
       `      🏷️ Título: "vanity" (de 4 opciones: vanity, tocador, mesa de maquillaje, Comoda)`
       `      🖼️ 1 foto(s)  📝 variante_002.txt`
   - **Confirmación / Resultado de Publicación:**
     - **Rotación inmediata y obligatoria:** Según el apunte del usuario, **incluso si la publicación falla o da error**, el título intentado se consume y **siempre se rota al siguiente nombre** para que ninguna otra cuenta intente usar ese mismo nombre.
     - Actualiza `producto.json` rotando la cola: `nombres[1:] + [nombres[0]]` (el usado/intentado pasa al final).
     - Si era string con comas, guarda `", ".join(nombres_rotados)`. Si era lista, guarda la lista rotada.
     - Marca la publicación en `cuenta.json` (`"publicado"` o `"fallido"`) con su `"titulo_usado"` registrado.

---

## 3. Plan de Acción Paso a Paso

### Paso 1: Crear utilidades de gestión de nombres (`scripts-gemini/utilidades_nombres.py` o módulo compartido)

Funciones auxiliares puras y robustas:
1. `parsear_nombres_producto(valor_nombre) -> list[str]`:
   - Si es `list`: limpia espacios de cada elemento `[x.strip() for x in valor_nombre if x.strip()]`.
   - Si es `str`:
     - Si contiene `,`: divide por comas y limpia espacios `[x.strip() for x in valor_nombre.split(",") if x.strip()]`.
     - Si no contiene `,`: retorna `[valor_nombre.strip()]`.
   - Si está vacío o no existe: retorna `["Sin título"]`.

2. `rotar_cola_nombres(lista_nombres: list[str]) -> list[str]`:
   - Si `len(lista_nombres) <= 1`: retorna la lista sin cambios.
   - Si `len(lista_nombres) > 1`: retorna `lista_nombres[1:] + [lista_nombres[0]]`.

3. `actualizar_producto_con_rotacion(ruta_producto_json: Path, nuevo_orden: list[str], formato_original: type)`:
   - Lee `producto.json`.
   - Si el original era `str`: guarda `", ".join(nuevo_orden)`.
   - Si el original era `list`: guarda `nuevo_orden`.
   - Escribe el JSON manteniendo formato (`ensure_ascii=False, indent=2`).

---

### Paso 2: Actualizar `scripts-gemini/preparar_cuentas.py`

1. **En `cmd_asignar`:**
   - Durante el recorrido de productos a asignar:
     - Cargar `producto.json`.
     - Parsear la lista de nombres con `parsear_nombres_producto(datos.get("nombre"))`.
     - Contar cuántas asignaciones previas globales existen para este producto en `CUENTAS_DIR`.
     - Seleccionar el título: `titulo_elegido = nombres[asignaciones_previas % len(nombres)]`.
     - Incluir `"titulo_usado": titulo_elegido` en el diccionario de la publicación guardada en `cuenta.json`.
2. **En `cmd_pendientes` y log de consola:**
   - Mostrar el título asignado junto al nombre de la carpeta:
     `📦 comoda (🏷️ "vanity") 🖼️ 2 foto(s) 📝 variante_002.txt`

---

### Paso 3: Actualizar `scripts-gemini/publicar_v2.py`

1. **Lectura y visualización del título:**
   - En `publicar_anuncio()`:
     - Recibir `titulo` explícito (en vez de extraerlo a ciegas de `datos_producto["nombre"]`).
     - Aplicar corte seguro `titulo[:120]` para respetar los límites de Revolico.
   - En el ciclo de `main()`:
     - Obtener `titulo = pub.get("titulo_usado")`.
     - Si `not titulo`: obtenerlo de `datos_producto` tomando el primer nombre de la cola.
     - Mostrar en el log:
       `📝 Título: "vanity" (300 USD) — 3 foto(s)`
2. **En modo `--preview`:**
   - Mostrar claramente el título que se enviará al formulario de Revolico para cada anuncio pendiente.
3. **Rotación tras éxito en publicación:**
   - Cuando `nueva_url` sea confirmada:
     - Rotar la lista de nombres en `producto.json`.
     - Asegurar que `pub["titulo_usado"] = titulo`.
     - Guardar `cuenta.json` y guardar `producto.json`.

---

### Paso 4: Pruebas y Verificación

1. **Prueba de Parseo:**
   - Probar con string único: `"Comoda"`.
   - Probar con string separado por comas: `"Comoda, vanity, tocador, mesa de maquillaje"`.
   - Probar con lista JSON: `["Comoda", "vanity", "tocador", "mesa de maquillaje"]`.
2. **Prueba de `--preview`:**
   - Ejecutar `python3 scripts-gemini/publicar_v2.py --email <cuenta> --preview` y confirmar que los títulos se muestran correctamente sin modificar ningún archivo.
3. **Prueba de Asignación Multi-cuenta:**
   - Simular asignación a 2 cuentas distintas y verificar que la cuenta 1 recibe `"Comoda"` y la cuenta 2 recibe `"vanity"`.
4. **Prueba de Rotación Física:**
   - Verificar que al publicarse un anuncio, `producto.json` rota el primer elemento al final de la cola y que el archivo queda limpio y bien formateado.

---

### Paso 5: Actualización de `productos/comoda/producto.json`

- Configurar el producto de prueba inicial según el requerimiento del usuario:
  ```json
  {
    "nombre": "Comoda, vanity, tocador, mesa de maquillaje",
    "precio": "300",
    "moneda": "USD",
    "categoria": [
      "Ropa y Accesorios",
      "Belleza, Maquillaje y Perfumes"
    ],
    "id_original": "890659"
  }
  ```

---

## 4. Matriz de Casos Borde

| Caso Borde | Comportamiento Esperado |
|---|---|
| **Publicación fallida (timeout, Cloudflare, error)** | **SÍ rotar igualmente.** Según requerimiento, el nombre intentado se consume/rota al final de la cola para que la siguiente cuenta/intento tome el próximo nombre disponible. |
| **Cuenta antigua ya asignada (sin campo `titulo_usado`)** | Fallback automático: toma el primer nombre disponible en `producto.json`. |
| **Título con más de 120 caracteres** | Se trunca con `titulo[:120]` antes de ingresar al formulario de Revolico. |
| **Espacios accidentales en las comas (`"Comoda ,  vanity  "`)** | Se limpian con `.strip()` quedando `"Comoda"` y `"vanity"`. |
| **Solo 1 nombre configurado** | Funciona de manera idéntica al sistema actual, sin rotar ni dar error. |
