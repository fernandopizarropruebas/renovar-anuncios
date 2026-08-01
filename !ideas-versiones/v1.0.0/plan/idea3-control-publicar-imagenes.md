# Idea 3: Control Publicar e Imágenes

## Resumen de la Idea
Brindar control granular sobre qué publicar, imitar el flujo de un humano tras cada publicación y alterar sutilmente las imágenes para evitar detección de duplicados por Revolico.

## Análisis del Problema
1. **Falta de Control de Rango:** Actualmente se publica todo de corrido. Se necesita especificar desde qué anuncio hasta cuál publicar, o los últimos X.
2. **Comportamiento Robótico:** Al finalizar una publicación, el script salta inmediatamente a la siguiente. Un usuario real haría clic para volver al inicio o a su perfil antes de publicar el siguiente.
3. **Detección de Imágenes Duplicadas:** Revolico detecta la publicación de anuncios idénticos (incluso con distinto título) analizando las imágenes, probablemente usando algoritmos de *Perceptual Hashing* (pHash) o IA, marcando los anuncios para revisión.

## Plan de Acción
1. **Implementar Filtros de Rango:**
   - Modificar la lógica del script de publicación (`/publicar/...`) para que acepte parámetros como `inicio`, `fin` o `ultimos_n`.
   - Adaptar la lectura del JSON/lista de anuncios para que solo itere sobre el subconjunto de anuncios seleccionado.
2. **Modificar Flujo de Navegación (Flujo Humano):**
   - Tras hacer clic en publicar y confirmar, programar a Playwright para que haga clic en el logo de Revolico o en la sección de cuenta, volviendo a la pantalla principal.
   - Insertar tiempos de espera aleatorios (`random.uniform(3, 8)`) antes de iniciar el flujo de la siguiente publicación.
3. **Algoritmo de Ofuscación de Imágenes:**
   - Integrar la librería `Pillow` (PIL) o `OpenCV` en Python.
   - Antes de subir cada imagen, pasarla por una función que la altere de forma invisible al ojo humano para cambiar su "hash":
     - Opción A: Añadir ruido aleatorio muy leve.
     - Opción B: Cambiar el tamaño de la imagen imperceptiblemente (ej. recortar 1-2 píxeles de un borde).
     - Opción C: Modificar metadatos (EXIF).
     - Opción D: Modificar imperceptiblemente el contraste o brillo.
   - Aplicar estos cambios de forma aleatoria por cada vez que se sube una foto.
