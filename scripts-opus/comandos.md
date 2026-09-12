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
