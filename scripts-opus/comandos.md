# 1. Importar anuncios existentes (YA HECHO — 504 productos)
python3 scripts-opus/preparar_cuentas.py importar-anuncios

# 2. Generar variantes de imágenes
python3 scripts-opus/preparar_cuentas.py generar-imagenes -n 20

# 3. Generar variantes de descripciones
python3 scripts-opus/preparar_cuentas.py generar-descripciones -n 20

# 4. Asignar productos a una cuenta
python3 scripts-opus/preparar_cuentas.py asignar --email tucuenta@gmail.com

# 5. Abrir Chrome con debugging
google-chrome --remote-debugging-port=9222

# 6. Publicar (primero preview, luego real)
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --preview
python3 scripts-opus/publicar_v2.py --email tucuenta@gmail.com --limite 5


Eliminar
# 1. Primero verificar cuáles siguen vivos
python3 scripts-opus/verificar_publicados.py --email alejandroantigravity1@gmail.com

# 2. Preview de eliminación (no elimina nada)
python3 scripts-opus/eliminar_anuncios.py --email alejandroantigravity1@gmail.com --preview

# 3. Probar eliminando 1 solo anuncio
python3 scripts-opus/eliminar_anuncios.py --email alejandroantigravity1@gmail.com --limite 1




########
Eliminar descripciones e imagenes 
hola quiero que dentro de /home/camiloueransim/maybel-ventas/renovar-anuncios/productos elimines por cada producto disponible, todas las descripciones que apareden dentro de las carpetas llamadas descripciones por ejemplo en /home/camiloueransim/maybel-ventas/renovar-anuncios/productos/aplique/descripciones elimina l
s /home/camiloueransim/maybel-ventas/renovar-anuncios/productos/aplique/descripciones
variante_001.txt  variante_004.txt  variante_007.txt  variante_010.txt
variante_002.txt  variante_005.txt  variante_008.txt
variante_003.txt  variante_006.txt  variante_009.txt y dentro de las carpetas de imagenes de cada producto borra las subcarpetas q tiene dentro junto a todo el contenido q tenga dentro pero no las imagenes q estan enlazadas a la caroeta de imagenes por ejepmlo en /home/camiloueransim/maybel-ventas/renovar-anuncios/productos/aplique/imagenes hay esto ls /home/camiloueransim/maybel-ventas/renovar-anuncios/productos/aplique/imagenes
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
'WhatsApp Image 2026-09-17 at 6.23.27 PM.jpeg', de ahi elimina  'variantes_WhatsApp Image 2026-09-17 at 6.23.21 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM (1)'
'variantes_WhatsApp Image 2026-09-17 at 6.23.24 PM (3)'
'variantes_WhatsApp Image 2026-09-17 at 6.23.25 PM'
'variantes_WhatsApp Image 2026-09-17 at 6.23.27 PM' con todo lo q tienen dentro pero no elimines 'WhatsApp Image 2026-09-17 at 6.23.21 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (1).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM (3).jpeg'
'WhatsApp Image 2026-09-17 at 6.23.24 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.25 PM.jpeg'
'WhatsApp Image 2026-09-17 at 6.23.27 PM.jpeg' y asi con cada producto dime si entiedes
cd /home/camiloueransim/maybel-ventas/renovar-anuncios

# 1) Eliminar todas las carpetas descripciones
find productos -type d -name descripciones -exec rm -rf {} +

# 2) Eliminar solo las subcarpetas dentro de cada carpeta imagenes
find productos -type d -path '*/imagenes' -print0 | while IFS= read -r -d '' d; do
  find "$d" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
done


verificacion 
find productos -type d -name descripciones -print
find productos -path '*/imagenes/*' -type d -print
find productos -path '*/imagenes/*' -type f | head