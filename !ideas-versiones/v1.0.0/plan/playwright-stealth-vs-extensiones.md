# Playwright Stealth vs Extensiones de Chrome

## 1. ¿Qué es Playwright Stealth y cómo funciona?

`playwright-stealth` (basado en `puppeteer-extra-plugin-stealth`) es una librería diseñada para camuflar navegadores automatizados y borrar cualquier rastro de que están siendo controlados por un script. 

Cuando inicias Playwright normalmente, deja muchas "pistas" en el navegador. `playwright-stealth` interviene justo antes de que la página cargue y parchea el navegador para que parezca de uso común. Algunas de las modificaciones clave que hace son:

- **Oculta la bandera Webdriver:** Elimina o falsea `navigator.webdriver` (la métrica número 1 que usa Cloudflare).
- **Parchea `window.chrome`:** Los navegadores Chrome iniciados por humanos tienen un objeto `window.chrome` con mucha información. Playwright a veces no lo tiene o lo tiene distinto; el stealth lo falsifica a la perfección.
- **Falsifica Plugins y Permisos:** Los bots suelen no tener plugins instalados. Stealth simula tener los plugins normales de un usuario.
- **Evade comprobaciones de Hardware (WebGL):** Cloudflare revisa cómo el navegador renderiza gráficos para detectar tarjetas gráficas "falsas" de servidores en la nube. Stealth parchea esto.

## 2. ¿Cómo evita que Cloudflare te bloquee?

Cuando entras a Revolico, Cloudflare envía silenciosamente un script de JavaScript a tu navegador (como el famoso *Turnstile*). Este script lanza una serie de "preguntas trampa" al navegador.

Si usas **Playwright normal**:
- Cloudflare: "¿Eres un Webdriver?" -> Navegador: "Sí".
- Cloudflare: "¡Bot detectado! Bloquear conexión o lanzar Captcha infinito."

Si usas **Playwright + Stealth**:
- Cloudflare: "¿Eres un Webdriver?" -> Navegador parcheado: "No, soy un Chrome normal."
- Cloudflare: "Muéstrame tus plugins" -> Navegador parcheado: "Aquí tienes, Chrome PDF Viewer, etc."
- Cloudflare: "Todo parece en orden. Eres un humano, puedes pasar a Revolico."

## 3. Comparativa: Stealth vs Extensiones (RevoRenew)

Ambas opciones tienen ventajas y desventajas a la hora de burlar los sistemas:

| Característica | Playwright + Stealth | Extensiones de Chrome (RevoRenew) |
| :--- | :--- | :--- |
| **Naturaleza Técnica** | Navegador automatizado, "disfrazado" para parecer humano mediante engaños a JS. | Navegador 100% humano. El código de la extensión corre aislado (Content Scripts). |
| **Detección Técnica (Cloudflare)** | **Baja.** Burla casi todo, pero es un juego del gato y el ratón. Si Cloudflare actualiza su IA, a veces hay que actualizar la librería Stealth. | **Nula.** Cloudflare no ve a la extensión, solo ve a un humano usando un Chrome normal. |
| **Control del Navegador** | **Absoluto.** Playwright puede interceptar peticiones de red, borrar caché profunda, abrir y cerrar pestañas, y manejar múltiples cuentas a la vez fácilmente desde Python. | **Limitado.** Depende de las reglas de Google (Manifest V3). Es complejo manejar múltiples sesiones o interceptar red libremente. |
| **Curva de Aprendizaje / Migración** | **Rápida.** Si ya tienes scripts en Python, solo es añadir 2-3 líneas de código para importar la librería Stealth. | **Lenta.** Tendrías que reescribir toda la lógica de Python y Playwright a JavaScript para inyectarlo como extensión. |
| **Detección de Comportamiento (Revolico)** | **Alta**, si no programas tiempos aleatorios y navegación humana. | **Alta**, si la extensión hace clics robóticos y rápidos. |

## 4. Conclusión para tu Proyecto

Dado que ya tienes el sistema estructurado en Python con Playwright (como `renovar_revolico-antifallos.py`), **la decisión más lógica y eficiente es integrar `playwright-stealth`**.

Migrar a una extensión de Chrome te daría una ligera ventaja técnica frente a Cloudflare a largo plazo, pero a un costo de desarrollo altísimo (reescribir todo). Con `playwright-stealth`, el esfuerzo es mínimo y el resultado contra Cloudflare será inmediato: los errores que estás sufriendo al renovar deberían desaparecer drásticamente.

Sin embargo, como mencionamos antes, integrar Stealth resuelve el problema de Cloudflare, pero **no el de Revolico**. Para que Revolico no te borre anuncios, igual deberás modificar tus scripts para que hagan clics pausados, vuelvan a la pantalla de "Mi Cuenta" y alteren las imágenes sutilmente.
