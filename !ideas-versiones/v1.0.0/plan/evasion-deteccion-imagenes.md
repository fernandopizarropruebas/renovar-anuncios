# Evasión de Detección de Imágenes Duplicadas

## ¿Cómo detectan los sitios de clasificados las fotos repetidas?

Las plataformas como Revolico (y en general, casi todos los marketplaces modernos) utilizan tres niveles para detectar si estás subiendo exactamente lo mismo varias veces para hacer spam:

1. **Hash Criptográfico (MD5, SHA-256):** Es la forma más básica de revisión. Verifica si el *archivo informático* es el mismo. 
   - **¿Lo engañas con captura de pantalla?** Sí, 100%. Un solo píxel cambiado altera todo el hash.

2. **Hash Perceptual (pHash, dHash):** Este es el "gran jefe". A diferencia del anterior, el pHash reduce la imagen a una cuadrícula en blanco y negro (digamos 8x8 o 16x16) y analiza la estructura visual (dónde hay luz, dónde hay sombra, las formas generales).
   - **¿Lo engañas con captura de pantalla y un recorte ligero?** **NO**. El pHash está diseñado exactamente para aguantar recortes pequeños, marcas de agua suaves y cambios de resolución. Te detectarán como duplicado.

3. **Inteligencia Artificial (Visión Computacional):** Identifica objetos. Si subes la foto de un "iPhone en una mesa azul", la IA etiquetará el contenido independientemente de cómo lo recortes. No suelen usarse para banear fotos exactas a menos que busquen imágenes inapropiadas o contenido de marca, debido al alto coste computacional.

---

## ¿Hacer captura de pantalla y recortar es suficiente?

**La respuesta corta es: Probablemente no sea suficiente** si Revolico utiliza un filtro de *Hash Perceptual* moderadamente bueno. 

Si solo haces una captura y recortas un poquito los bordes, el patrón de contrastes de la foto seguirá siendo casi idéntico. El algoritmo dirá: *"Esta foto tiene un 95% de similitud visual con esta otra, es spam"*. Y el anuncio pasará a revisión o será borrado.

---

## Técnicas efectivas para burlar el Hash Perceptual (con 1 sola foto)

Si tienes una sola foto y necesitas exprimirla para crear varios anuncios sin que te los tumben, debes hacer modificaciones que alteren drásticamente el análisis matricial del algoritmo, sin que el ojo humano lo perciba como una mala foto.

### 1. Espejado (Flip Horizontal) - ⭐ Muy Recomendado
Voltear la foto horizontalmente (efecto espejo). 
- **Por qué funciona:** Destruye completamente el pHash tradicional. Lo que estaba a la izquierda pasa a la derecha, por lo que la matriz de luz/sombra cambia por completo.
- **Advertencia:** No lo uses si el producto tiene letras muy grandes y legibles, ya que se verán al revés.

### 2. Rotación + Zoom (Recorte agresivo) - ⭐ Recomendado
Rotar la imagen entre 3 y 5 grados, y luego aplicar zoom para recortar los bordes vacíos que deja la rotación.
- **Por qué funciona:** Modifica la alineación de todas las líneas rectas de la imagen y cambia drásticamente qué parte de la imagen cae en qué cuadrante del análisis perceptual.

### 3. Alteración Global de Color
Aumentar o disminuir el brillo, el contraste, y cambiar ligeramente la saturación o la temperatura (más cálida o más fría).
- **Por qué funciona:** Modifica la estructura de iluminación que algoritmos como el dHash usan para calcular las diferencias entre píxeles adyacentes.

### 4. Modificación de Geometría / Marcos
Ponerle un marco grueso de distintos colores a la foto, o añadirle stickers gráficos ("¡Oferta!", "¡Nuevo!") en distintos lugares.
- **Por qué funciona:** Introduce una cantidad enorme de píxeles radicalmente diferentes en zonas donde antes no los había, rompiendo el porcentaje de similitud.

---

## La Solución para Automatizar (Aplicarlo al Bot)

Como quieres automatizar esto con el bot (Idea 3), no necesitas hacer capturas de pantalla a mano. 

La solución es integrar en tu script de Python (usando la librería `Pillow` o `OpenCV`) un **Generador de Variaciones**. Cada vez que el bot vaya a publicar la foto `zapato.jpg`, el script en una fracción de segundo podría:
1. Voltearla aleatoriamente (50% de probabilidad).
2. Girarla aleatoriamente un número al azar entre -3 y +3 grados.
3. Modificar el brillo al azar entre -10% y +10%.
4. Subir esta versión alterada, y luego borrarla de tu disco.

De esta forma, puedes subir el mismo anuncio 20 veces, y para los algoritmos de detección de Revolico serán 20 fotos totalmente diferentes, mientras que para el cliente final seguirá viéndose igual.
