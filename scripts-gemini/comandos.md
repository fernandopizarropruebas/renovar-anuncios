# 1. Importar anuncios existentes (YA HECHO — 504 productos)
python3 scripts-gemini/preparar_cuentas.py importar-anuncios

# 2. Generar variantes de imágenes
python3 scripts-gemini/preparar_cuentas.py generar-imagenes -n 20

# 3. Generar variantes de descripciones
python3 scripts-gemini/preparar_cuentas.py generar-descripciones -n 20

# 4. Asignar productos a una cuenta
python3 scripts-gemini/preparar_cuentas.py asignar --email tucuenta@gmail.com

# 5. Abrir Chrome con debugging
google-chrome --remote-debugging-port=9222

# 6. Publicar (primero preview, luego real)
python3 scripts-gemini/publicar_v2.py --email tucuenta@gmail.com --preview
python3 scripts-gemini/publicar_v2.py --email tucuenta@gmail.com --limite 5

# 7. Publicar SIN DESCRIPCIÓN (para prueba A/B anti-borrado)
python3 scripts-gemini/publicar_sin_descripcion.py --email tucuenta@gmail.com --preview --limite 5
python3 scripts-gemini/publicar_sin_descripcion.py --email tucuenta@gmail.com --limite 5
# O equivalentemente con flag:
# python3 scripts-gemini/publicar_v2.py --email tucuenta@gmail.com --sin-descripcion --limite 5

# 8. Publicar con DESCRIPCIONES ALEATORIAS (usa frases_cierre.txt)
python3 scripts-gemini/publicar_v2.py --email tucuenta@gmail.com --descripciones-aleatorias --preview --limite 5
python3 scripts-gemini/publicar_v2.py --email tucuenta@gmail.com --port=9223 --limite 20 --descripciones-aleatorias

# 9. Listar productos actualmente publicados en la cuenta (con scroll y total)
python3 scripts-gemini/listar_publicados.py --port=9223
python3 scripts-gemini/listar_publicados.py --port=9223 --guardar


Eliminar
# 1. Primero verificar cuáles siguen vivos
python3 scripts-gemini/verificar_publicados.py --email alejandroantigravity1@gmail.com

# 2. Preview de eliminación (no elimina nada)
python3 scripts-gemini/eliminar_anuncios.py --email alejandroantigravity1@gmail.com --preview

# 3. Probar eliminando 1 solo anuncio
python3 scripts-gemini/eliminar_anuncios.py --email alejandroantigravity1@gmail.com --limite 1




########
Eliminar descripciones e imagenes 