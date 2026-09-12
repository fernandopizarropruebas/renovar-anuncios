Viewed publicar_varias_cuentas_a_la_vez.md:1-11

Siento mucho lo de los anuncios. Es muy probable que tengas razón: si de repente tienes 100 anuncios y todos terminan exactamente con la misma frase idéntica ("*mensajeria gratis en toda la habana*"), el algoritmo de Revolico detecta ese patrón exacto y lo marca como spam automatizado o contenido duplicado.

Para evitar eso, la solución clásica en el mundo de la automatización se llama **"Spintax" o Rotación Dinámica de Textos**.

Te propongo **dos maneras** de hacerlo. Léelas y me dices cuál te gusta más para programarla:

### Opción 1: Listas de frases aleatorias (Sencillo y efectivo)
En lugar de tener 1 frase fija, creamos una lista con 10 o 15 frases que signifiquen lo mismo. Cuando el bot vaya a publicar un anuncio, escoge una frase de la lista "al azar".

**Para los de más de 20 (Toda la Habana), el bot elegiría al azar entre:**
- "Mensajería gratis en toda La Habana"
- "Delivery sin costo a cualquier municipio de la capital"
- "Transporte gratuito a todos los municipios"
- "Envío libre de costo hasta la puerta de tu casa en La Habana"
- "Llevamos a domicilio gratis (Toda La Habana)"
- "El precio ya incluye la entrega a domicilio en la capital"

**Para los de 10 a 20 (Casi toda la Habana):**
- "Mensajería gratis para casi toda La Habana"
- "Delivery sin costo a zonas céntricas"
- "Envío libre de costo a la mayoría de los municipios"
- "Transporte gratuito (consultar disponibilidad según municipio)"
- "Llevamos a domicilio gratis a gran parte de la capital"

### Opción 2: Generador de combinaciones o "Spintax" (Nivel Máximo Anti-Ban)
En vez de frases completas, hacemos que el bot **"arme"** la oración uniendo pedacitos (fragmentos) que significan lo mismo. Así, las posibilidades matemáticas de repetir una frase son bajísimas.

Por ejemplo, armamos la frase uniendo: `[ACCIÓN] + [PRECIO] + [DESTINO]`

- **ACCIÓN:** (Mensajería | Delivery | Envío | Transporte | La entrega)
- **PRECIO:** (es gratis | va sin costo | no te cuesta nada | está incluida)
- **DESTINO:** (a toda La Habana | a cualquier municipio | hasta tu casa | en la capital)

El bot escoge un pedacito de cada grupo y arma oraciones como:
- *"Delivery sin costo a cualquier municipio"*
- *"Transporte incluido hasta tu casa"*
- *"Mensajería gratis a toda La Habana"*

Esto genera fácilmente más de 100 combinaciones distintas que suenan perfectamente humanas, diluyendo completamente el patrón para Revolico.

---

**¿Qué te parece?** La Opción 2 es la más segura a largo plazo para burlar a Revolico, pero la Opción 1 también funciona muy bien si tenemos suficientes frases. Dime cuál te convence y me pongo a modificar el código.