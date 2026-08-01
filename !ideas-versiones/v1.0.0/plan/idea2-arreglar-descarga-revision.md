# Idea 2: Arreglar Descarga en Revisión

## Resumen de la Idea
Corregir el script de descarga de anuncios para que funcione correctamente cuando un anuncio está en estado "en revisión".

## Análisis del Problema
Cuando Revolico pone un anuncio "en revisión", la estructura de la página (el DOM) cambia: aparecen nuevos elementos visuales (como banners o textos informativos). El script actual asume una estructura HTML estándar para extraer imágenes, títulos y detalles, lo que provoca que recoja información o imágenes incorrectas (o de anuncios sugeridos en lugar del principal) cuando la estructura original se desplaza.

## Plan de Acción
1. **Identificación de Selectores:** Analizar las imágenes provistas (`image2.jpg` a `image5.jpg`) y/o acceder manualmente a un anuncio en estado de revisión para inspeccionar el código HTML. Esto permitirá identificar los nuevos selectores CSS o XPath correspondientes al anuncio en revisión.
2. **Lógica Condicional:** Modificar `descargar_anuncios.py` (específicamente las funciones que extraen datos usando BeautifulSoup/Playwright) para incluir una comprobación inicial: `if "en revisión" en pagina: ... else: ...`.
3. **Ajuste de Extracción:**
   - Para anuncios en revisión, apuntar explícitamente a los selectores corregidos para el título, descripción, precio e imágenes del anuncio real, evitando el contenido basura.
4. **Pruebas:** Ejecutar el script apuntando a una URL de un anuncio que sabemos está en estado de revisión para verificar que la descarga extrae únicamente los datos e imágenes correctos.
