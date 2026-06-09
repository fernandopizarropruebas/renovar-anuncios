quiero que te leas  /home/camiloueransim/maybel-ventas/renovar-anuncios/publicar/publicar_anuncios-humano.py, es el anuncio que sirve para publicar, esta hecho cuidadosamente para que revolico no lo detecte como un bot, entonces lo que       yo quiero es hacerte una pregunta es posible cambiarle los precios a los anuncios que ahi se ven? por ejemplo el metodo que yo quiero es que se divida entre 50 el precio del anuncio se tome la parte entera de ese resultado, se le sume 1 y se multiplique por 5 y se le sume al valor que tenia originalmente y ese sera el nuevo precio por ejemplo si valia 30 el resultado es 30/50=0+1*5=5+30=35 y si valia 40 el resultado es 40/50=0+1*5=5+40=45 y si valia 75 el resultado es 75/50=1+1*5=10+75=85. o sea debe funcionar igual que hasya ahora lo unico q cambia es que cuando vaya a poner precio haga este calculo primero, para subirle los precios a las cosas

-lo otro es que me gustaria que pongas a partir de de 10 usd que se le sumen al precio original se ponga en la descripcion del anuncio mensajeria gratis para casi toda la habana y a partir de 20 usd q se le sume al precio original que diga en la descripcion mensajeriaaa gratis en toda la habana

-3tengo duda si lo q esta hecho hasta ahora esta vinculado a un numero de telefono que era el que tenia antes 54261836, pq para estas cuentas usare otro
---
**Respuestas:**

¡Hola! Aquí tienes las respuestas a tus consultas:

1. **Sobre cambiar los precios matemáticamente:**
   **Sí, es totalmente posible.** En el script `publicar_anuncios-humano.py`, actualmente extrae el precio. Podemos modificar el código para que, justo antes de rellenar el formulario, tome ese precio original numérico y aplique tu fórmula: `incremento = (int(Precio / 50) + 1) * 5` y luego `NuevoPrecio = Precio + incremento`. 

2. **Sobre agregar el texto de mensajería según el incremento:**
   **Sí, también es muy fácil.** Ya que calcularemos el incremento en el paso anterior, podemos añadir unas líneas de código que hagan lo siguiente:
   - Si `incremento >= 20`: Añade al final de la descripción "*mensajeria gratis en toda la habana*".
   - Si `incremento >= 10` y `incremento < 20`: Añade "*mensajeria gratis para casi toda la habana*".

3. **Sobre el número de teléfono (54261836):**
   He revisado a fondo el código y **NO**, el script de automatización no tiene tu número de teléfono `54261836` "quemado" o guardado en el código. 
   El bot solo interactúa con Revolico usando la sesión de Chrome que tengas abierta. Si el número de teléfono se publica automáticamente, es porque Revolico lo toma del perfil de la cuenta que estás usando, o porque el número está escrito en el texto de las descripciones (`datos.md`).
   Para las cuentas nuevas, el bot simplemente usará la información de la cuenta en la que hayas iniciado sesión en ese Chrome. No tienes que preocuparte de que el bot "recuerde" tu número viejo.

**¿Quieres que aplique la matemática de los precios y la lógica de la mensajería en tu código `publicar_anuncios-humano.py` ahora mismo?**