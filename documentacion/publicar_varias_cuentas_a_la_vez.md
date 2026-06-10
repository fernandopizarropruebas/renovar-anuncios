# Guía: Publicar en Múltiples Cuentas de Revolico a la Vez

El script de publicación (`publicar_anuncios-humano.py`) está programado para soportar múltiples conexiones al mismo tiempo. Para lograr publicar en varias cuentas de manera simultánea, la clave está en iniciar navegadores de Chrome que estén completamente aislados entre sí.

Esto se logra asignándole a cada navegador un **puerto de depuración** (`--remote-debugging-port`) diferente y una **carpeta de datos de usuario** (`--user-data-dir`) diferente para que cada uno guarde sus propias sesiones (cookies) de Revolico.

---

## Pasos para publicar en 2 cuentas simultáneamente

### 1. Abrir los navegadores independientes

Necesitas abrir una terminal distinta para mantener abierto cada navegador.

**En la Terminal 1 (Para la Cuenta A):**
Abre el primer navegador apuntando al puerto por defecto `9222`:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/home/camiloueransim/.config/google-chrome-debug
```
*Inicia sesión en la **Cuenta A** de Revolico en este navegador.*

**En la Terminal 2 (Para la Cuenta B):**
Abre el segundo navegador cambiando el puerto al `9223` y creando una nueva carpeta de perfil (ej. `google-chrome-debug-cuenta2`):
```bash
google-chrome --remote-debugging-port=9223 --user-data-dir=/home/camiloueransim/.config/google-chrome-debug-cuenta2
```
*Inicia sesión en la **Cuenta B** de Revolico en este navegador.*

---

### 2. Ejecutar los scripts simultáneamente

Con los dos navegadores listos y con sus sesiones abiertas, ahora usas otras terminales para lanzar el script de publicación y le dices a qué puerto conectarse usando el parámetro `--port`.

**En la Terminal 3 (Bot para la Cuenta A):**
Ejecuta el bot indicándole que se conecte al primer navegador:
```bash
python3 publicar/publicar_anuncios-humano.py --port=9222
```

**En la Terminal 4 (Bot para la Cuenta B):**
Ejecuta el bot indicándole que se conecte al segundo navegador:
```bash
python3 publicar/publicar_anuncios-humano.py --port=9223
```

---

## ¿Qué sucederá?
Tendrás dos scripts ejecutándose en paralelo. El primer script controlará exclusivamente el Chrome del puerto 9222 y el segundo controlará el del puerto 9223. Publicarán tus anuncios al mismo tiempo sin que se crucen los datos, reduciendo drásticamente el tiempo de trabajo.

> **💡 Consejo para escalar:** Puedes hacer esto con 3, 4 o más cuentas simultáneas. Solo asegúrate de inventar un puerto distinto (ej. `9224`, `9225`) y una carpeta de usuario distinta (`...-cuenta3`, `...-cuenta4`) para cada nueva instancia de Chrome que abras.
