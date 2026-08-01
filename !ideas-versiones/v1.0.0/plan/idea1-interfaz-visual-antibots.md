# Idea 1: Interfaz Visual y Antibots

## Resumen de la Idea
Crear una aplicación visual para gestionar las cuentas y anuncios de forma paralela, mejorando las técnicas antibots frente a alternativas como RevoRenew.

## Análisis y Stack Tecnológico Propuesto
Para crear una interfaz visual que controle instancias de Chrome (vía Playwright) y ejecute los scripts de Python, la mejor arquitectura es una **Aplicación Web Local**:
- **Backend:** Python con `FastAPI`. Servirá como puente entre la interfaz de usuario y los scripts actuales (Playwright). Permitirá lanzar las instancias de Chrome (`--remote-debugging-port`), leer los JSON de anuncios publicados y exponer endpoints para renovar, publicar, etc.
- **Frontend:** HTML, CSS y Javascript (React o Vanilla) para crear una interfaz hermosa, dinámica y similar a Revolico, desde la que se puedan seleccionar cuentas y visualizar qué está publicado y qué no.

**Playwright vs Inyección en Navegador (RevoRenew):**
- RevoRenew probablemente opere como una extensión de Chrome o inyectando scripts directamente en la consola de una sesión de usuario. Esto es "natural" a los ojos de los sistemas anti-bots porque no levanta las banderas típicas de automatización (`navigator.webdriver`).
- **Playwright** usa el protocolo de depuración. Sistemas como Cloudflare lo detectan si no se ocultan los rastros. Para que Playwright sea indetectable:
  1. Utilizar librerías como `playwright-stealth`.
  2. Rotar o evitar repetir patrones exactos (tiempos aleatorios, clics no lineales).
  3. Mantener el uso de perfiles reales (`--user-data-dir`).
- Evitar detecciones de Revolico por contenido: Sí, cambiar el texto, agregar variables de despedida y rotar categorías es fundamental para evitar bloqueos por spam, independientemente de la herramienta (Playwright o RevoRenew).

## Plan de Acción
1. **Definir Stack y Estructura:** Iniciar un proyecto FastAPI + Frontend web en una nueva carpeta del proyecto.
2. **Controlador de Cuentas:** Crear el sistema que ejecute los comandos de `google-chrome --remote-debugging-port` por cada cuenta y permita conectarse a ellos en paralelo.
3. **Lectura de Datos:** Integrar la lectura de los archivos JSON (`publicados_en_...json`) para mostrar en la UI los anuncios publicados vs no publicados.
4. **Desarrollo de la UI:** Crear la pantalla principal interactiva con selección de acciones (publicar, renovar, eliminar) mapeadas a los scripts correspondientes.
5. **Mejora Antibot en Playwright:** Integrar `playwright-stealth` y aumentar la base de textos/despedidas dinámicas en el script de publicación.
