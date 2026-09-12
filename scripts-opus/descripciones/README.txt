# Cómo funciona el sistema de variación de descripciones
# ════════════════════════════════════════════════════════
#
# El script toma la descripción base del producto y le aplica
# estas transformaciones para generar variantes únicas:
#
# 1. SINÓNIMOS (sinonimos.txt)
#    Si la descripción contiene alguna palabra del banco de sinónimos,
#    hay un 50% de probabilidad de que sea reemplazada por una alternativa.
#    Ejemplo: "Vendo mueble nuevo" → "Ofrezco mueble sin estrenar"
#
# 2. REORDENAMIENTO
#    Si la descripción tiene más de 2 oraciones, hay un 40% de 
#    probabilidad de que las oraciones del medio se barajan.
#    Ejemplo: "A. B. C. D." → "A. C. B. D."
#
# 3. FRASES DE CIERRE (frases_cierre.txt)
#    Se añaden 1-2 frases aleatorias del banco al final.
#    Ejemplo: "...descripción." → "...descripción. Escríbame sin compromiso."
#
# 4. VARIACIÓN DE ESPACIADO
#    Pequeños cambios en saltos de línea para alterar el formato.
#
# ARCHIVOS EDITABLES:
#   - sinonimos.txt → Palabras y sus alternativas
#   - frases_cierre.txt → Frases que se añaden al final
#
# IMPORTANTE: Revisa que los sinónimos y frases tengan sentido
# para tus productos. Si vendes muebles, no pongas frases de
# tecnología, etc.
