# RevoRenew (V2)

Extensión MV3 simple para Chrome/Chromium que intenta renovar anuncios desde Revolico usando la propia UI del sitio.

## Qué hace esta V1
- Trabaja sobre `https://www.revolico.com/account`
- Extrae IDs detectando enlaces `a[href*="/item/"]`
- Navega a `https://www.revolico.com/item/<ID>/_/manage`
- Busca el botón **"Renovar anuncio"** / `data-testid="renovate-button"`
- Registra resultado por anuncio en `chrome.storage.local`
- Vuelve a `/account` para seguir con el siguiente

## Qué NO promete esta V1
- No garantiza renovar todos los anuncios
- Si la UI no confirma la acción, marca `skip` o `error`
- No resuelve login, Cloudflare ni verificaciones manuales
- No incluye licencias, monetización ni backend

## Estado persistido
La extensión guarda en `chrome.storage.local`:
- `runState`
- `processedIds`
- `renewedIds`
- `skippedIds`
- `errorIds`
- `queue`
- `lastProcessedId`
- `startedAt`
- `updatedAt`

Además guarda algunos campos auxiliares (`currentItemId`, `lastResult`, `summary`, etc.) para mostrar mejor el estado en el popup.

## Instalación manual en Chrome / Chromium
1. Abre Chrome o Chromium.
2. Ve a `chrome://extensions/`
3. Activa **Developer mode**.
4. Pulsa **Load unpacked**.
5. Selecciona esta carpeta:
   - `/root/.openclaw/workspace/revolico-renew-extension`
6. Verifica que aparezca la extensión **Revolico Renew Extension**.

## Cómo probarla
1. Abre sesión manualmente en Revolico.
2. Navega a `https://www.revolico.com/account`
3. Espera a que cargue la lista de anuncios.
4. Haz click en el icono de la extensión.
5. Pulsa **Iniciar**.
6. Observa el popup:
   - **Estado**
   - total procesados
   - renovados
   - skip
   - errores
   - cola pendiente
7. Si necesitas parar:
   - **Pausar**: congela el flujo y conserva checkpoint
   - **Reanudar**: continúa con la cola actual
   - **Detener**: deja el checkpoint guardado y corta la ejecución
8. Si quieres reiniciar desde cero, vuelve a abrir el popup y pulsa **Iniciar** otra vez. Esa acción resetea la corrida y reconstruye la cola desde `/account`.

## Flujo esperado
1. En `/account`, la extensión hace scroll y recolecta IDs visibles
2. Construye la cola evitando IDs ya procesados en la corrida actual
3. Abre la página `/_/manage` de cada anuncio
4. Intenta renovar
5. Si detecta éxito por modal o porque desaparece el botón, marca `renewed`
6. Si no hay botón renovable claro, marca `skipped`
7. Si aparece `Reintentar`, login o bloqueo, marca `error`
8. Regresa a `/account` y sigue

## Límites actuales
- Depende de la estructura actual de Revolico
- El regex de extracción de IDs usa heurística basada en enlaces `/item/`
- La confirmación de éxito usa heurísticas de texto y desaparición del botón
- Si Revolico cambia textos, selectores o flujo modal, habrá que ajustar `content.js`
- No procesa varias pestañas en paralelo; V1 asume una sola pestaña de trabajo

## Archivo clave
- `content.js`: lógica principal en páginas de Revolico
- `background.js`: control de estado y mensajes popup ↔ pestaña
- `popup.*`: controles manuales y resumen
- `manifest.json`: configuración MV3

## Recomendación operativa
Usarla primero con pocos anuncios y supervisión manual en una pestaña visible de Revolico.
