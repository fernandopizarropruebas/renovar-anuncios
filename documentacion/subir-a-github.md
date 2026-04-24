# Cómo subir tu proyecto a GitHub

Este documento te guiará paso a paso para respaldar todo tu entorno de automatización de Revolico en tu cuenta de GitHub (`fernandopizarropruebas`).

## Paso 1: Crear el repositorio vacío en GitHub

1. Entra a tu cuenta en [GitHub](https://github.com/fernandopizarropruebas/).
2. Haz clic en el botón verde **"New"** (o ve a github.com/new).
3. En **Repository name**, pon exactamente: `renovar-anuncios`
4. Puedes ponerle una descripción opcional (ej: "Scripts de automatización y scraping para Revolico").
5. Déjalo como **Public** o **Private** (según prefieras).
6. **MUY IMPORTANTE**: No marques ninguna de las casillas ("Add a README file", "Add .gitignore", etc.). Necesitamos que el repositorio nazca 100% vacío para empujar tus archivos locales actuales hacia allá.
7. Haz clic en **Create repository**.

¡Listo! Te quedará una pantalla con unas URL que usaremos en el Paso 4.

## Paso 2: Configurar qué NO queremos subir (.gitignore)

Seguramente en tu carpeta tienes imágenes descargadas (la carpeta `anuncios/`), archivos JSON del historial y cosas que pesan mucho y cambian constantemente. Es mejor NO subir los datos al repositorio, solo el código fuente.

Crea un archivo llamado `.gitignore` en la raíz de tu proyecto (`/home/camiloueransim/maybel-ventas/renovar-anuncios/.gitignore`) y pégale esto:

```bash
# Ocultar carpetas de datos masivos
anuncios/
visitas/

# Ocultar historiales personales o bases de datos de scraping
*.json
!index.json  # Si prefieres llevar registro de tu index, puedes quitar el '!'

# Archivos de caché y cosas de Python
__pycache__/
*.pyc

# Archivos temporales de tu entorno local
.gemini/
scratch/
```
*(Nota: Si quieres respaldar absolutamente todo, incluso las fotos locales y tus `.json` de historial, entonces puedes saltarte el Paso 2 o dejar el `.gitignore` casi vacío. Pero lo ideal en GitHub es subir solo código).*

## Paso 3: Inicializar Git en tu máquina

Abre tu terminal normal en la ruta de tu proyecto (`/home/camiloueransim/maybel-ventas/renovar-anuncios`) y ejecuta esto para transformar la carpeta en un repositorio de control de versiones local:

```bash
git init
```

*Si es la primera vez que usas git en esta PC, podría pedirte que configures tu nombre y correo. Si ocurre, tira estos dos comandos:*
```bash
git config --global user.name "Fernando Pizarro"
git config --global user.email "tu_correo@gmail.com"
```

## Paso 4: Enlazar tu carpeta local con el repositorio de GitHub

Para decirle a tu máquina hacia dónde debe disparar el código, agregamos la URL del repo que creaste en el Paso 1:

```bash
git remote add origin https://github.com/fernandopizarropruebas/renovar-anuncios.git
```

## Paso 5: Preparar y Subir los Archivos (Commit & Push)

Ahora vamos a empaquetar los archivos de la carpeta y subirlos a la nube:

**a) Añadir todo al paquete (excepto lo que está en el .gitignore):**
```bash
git add .
```

**b) Ponerle un "sello" o comentario a este paquete (Commit):**
```bash
git commit -m "Mi primer respaldo: Suite de scripts de automatización de Revolico"
```

**c) Cambiar el nombre a la rama principal (se recomienda decirle 'main'):**
```bash
git branch -M main
```

**d) Empujar (Subir) los códigos hacia GitHub:**
```bash
git push -u origin main
```

Te pedirá tu usuario de GitHub y tu contraseña (hoy en día GitHub requiere que pongas un *Token de acceso personal* como contraseña en lugar de la palabra secreta. Si te da error de contraseña, puedes autenticarte super fácil escribiendo `gh auth login` si tienes instalado Github CLI).

---

## Qué pasa cuando modifiques el código en el futuro

Una vez que ya has hecho este proceso para conectarte a GitHub, si tú o yo hacemos mejoras en un script en el futuro, solo tienes que lanzar tres comandos para actualizar el archivo en las nubes:

```bash
git add .
git commit -m "Añadido manejo multicuenta para JSONs"
git push
```
¡Y eso es todo, el código quedará a salvo en GitHub!
