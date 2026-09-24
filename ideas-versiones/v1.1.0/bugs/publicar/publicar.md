revisar bien toda la parte q conforman la publicacion de anuncios.
q el script de publicar este funcionando bien y este salteando bien las imagenes y las descripciones, y no repita imagenes por ejemplo cuando un producto tienen varias imagenes funciona mal pq no coge una imagen distinta cada vez creo oalgo pq me empieza a decir ts-opus/preparar_cuentas.py asignar --email alejandroantigravity1@gmail.com
  ⚠️  Espejo: sin sets de imágenes disponibles (todos quemados)
  ⚠️  Espejos: sin sets de imágenes disponibles (todos quemados)
  ⚠️  Lampara: sin sets de imágenes disponibles (todos quemados) cuando no deberia pasar pq cree 10 imagenes nuevas a la vez y si da error en estos deberia dar en todos y viceversa
o sea me refiero a que cuando se crean las imagenes se crean de esta forma , primero en la carpeta estan las imagenes 
'WhatsApp Image 2026-09-17 at 6.23.21 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (1).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (3).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.25 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.27 PM.jpeg'
se aplica el comando de crear imagenes
y queda algo asi

'variantes_WhatsApp Image 2026-09-17 at 6.23.21 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM (1)'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM (3)'
'variantes_WhatsApp Image 2026-09-17 at 6.23.25 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.27 PM'
'WhatsApp Image 2026-09-17 at 6.23.21 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (1).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (3).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.25 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.27 PM.jpeg'

y dentro de cada carpeta hay segun el comando de crear imagenes n copias de cada imagen original, quiero que revises si a la hora de extraer las imagenes para publicar esta cogiendo las imagenes 1 por cada carpeta o sea la logica te dice q como originalmente eran 10 imagenes a la hora de publicar uno debe publicar tambien 10 imagenes por tanto la logica es cuando yo escribo el comando python3 scripts-opus/preparar_cuentas.py generar-imagenes -n 10 por cada imagen original se debe crear una carpeta con 10 imagenes y cuando se vaya a publicar el comando de preparar cuentas /home/camiloueransim/maybel-ventas/renovar-anuncios/scripts-opus/preparar_cuentas.py le debe asignar 1 imagen de cada una y serciorarse q esa misma imagen no se la haya dado a alguien mas, dime si esta funcionanado asi ahora pq me resulta raro q haya publicado en una cuenta y a la segunda cuenta q haya publicado me dijese esto ts-opus/preparar_cuentas.py asignar --email alejandroantigravity1@gmail.com
  ⚠️  Espejo: sin sets de imágenes disponibles (todos quemados)
  ⚠️  Espejos: sin sets de imágenes disponibles (todos quemados)
  ⚠️  Lampara: sin sets de imágenes disponibles (todos quemados)
  cuando deberian quedar 9 imagenes por imagen original
  -ver si se puede verificar q entre cada imagen haya una variacion grande y anadirlo al script, o sea en /home/camiloueransim/maybel-ventas/renovar-anuncios/ideas-versiones/v1.0.0/documentacion_v1.0.0/05-anti-deteccion.md se puso q una de las formas q podia tener revolico de detectar imagenes puede ser - **MD5/SHA**: Si dos archivos son idénticos byte a byte, los detecta trivialmente
- **Hash perceptual (pHash/dHash)**: Compara la "huella visual" de la imagen. Dos fotos que se ven igual pero son archivos distintos (ej: guardada con diferente calidad JPEG) siguen siendo detectadas como iguales
- **Umbral**: Distancia de Hamming < 5-10 = "misma imagen", leete todo el documetno para mas info, me gustaria q cuando se creasen las imagenes tb se comparase entre todas ellas el grado de similitud y la q no cumpla con un umbral se elimina y se crea otra

  -saltear publicaciones cuando se vaya a publicar, o sea no hacerlo por orden alfabetico, ordenarlas aleatoriamente y empezar a publicar asi