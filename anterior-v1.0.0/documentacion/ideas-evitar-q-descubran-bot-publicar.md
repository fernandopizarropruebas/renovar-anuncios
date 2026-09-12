# Análisis de Detección de Bots y Estrategias de Evasión (Revolico)

Es extremadamente probable que Revolico (que sabemos que usa escudos como Cloudflare) te esté identificando como un bot o un *"spammer"*. Cuando detectan comportamientos anómalos, generalmente no bloquean la cuenta al instante, sino que aplican el conocido **"Shadowban"**: te dejan subir el anuncio, te dicen que todo salió bien, y a los pocos minutos un proceso en segundo plano borra tus publicaciones de la base de datos pública.

A continuación, desgrano las técnicas más comunes con las que nos están detectando y cómo podemos evitarlas en nuestro ecosistema.

## 1. Velocidad Sobrenatural y Patrones Exactos (El Error #1)
Tu idea es **100% correcta**. Actualmente haces un `sleep(12)`. Un humano no puede llenar 10 fotos, precio, título, categoría, y descripción, y publicar el anuncio en menos de 10 segundos ininterrumpidos docenas de veces seguidas. Además, el hecho de pausar *exactamente* 12 segundos entre cada anuncio es un indicativo lapidario en estadística de detección.

**💡 SOLUCIÓN:**
- **Aleatoriedad (Jitter):** Introducir un módulo de tiempo aleatorio. Por ejemplo: `await asyncio.sleep(random.uniform(25.5, 45.2))`.
- **Límites por Lote:** Evitar publicar bloques monstruosos de 220 anuncios de golpe. Lo ideal es publicar, por ejemplo, 20 anuncios, luego el bot "se va a tomar un café" (duerme 15 a 30 minutos), y luego publica otros 20.

## 2. Rellenado Instántico de Campos Téxtuales (Typing Override)
Playwright tiene la instrucción `element.fill('texto')`. Esta función vacía la caja y pega una cadena de texto masiva en **cero milisegundos**. Ningún ser humano teclea una descripción de 300 palabras instantáneamente. Las redes de detección observan el objeto `KeyboardEvent` de Javascript, y si ven un pegado masivo sin eventos táctiles intermedios, te tachan de autómata.

**💡 SOLUCIÓN:**
- En lugar de `fill`, usar `type`.
- Añadir retardo artificial de "tecleo": `await page.locator('input[name="title"]').type(titulo, delay=85)`. (Tardará 85ms entre tecleo y tecleo, emulando la velocidad humana).

## 3. Clics Instantáneos de JavaScript puro
En el código actual a veces saltamos la protección de elementos bloqueados usando `await page.evaluate("el => el.click()", btn)`. Esto lanza un clic del DOM sin hacer que el pultero del mouse se desplace físicamente hasta el botón. Los sistemas modernos detectan si el click fue generado por JS (`isTrusted: false`) o si fue un clic físico de un Mouse emulado.

**💡 SOLUCIÓN:**
- Usar exclusivamente las funciones de envoltura natural de Playwright en lugar de JS puro: `await btn.click(delay=150)`.
- Si se necesita mover el ratón de forma hiperrealista, añadir trayectorias caóticas invisibles con `page.mouse.move()`.

## 4. Patrones de Navegación "Go-To"
Normalmente, el usuario entra al `/home`, mira algo, hace clic en su cuenta, y luego le da a "Publicar anuncio". El bot, para ser más ahorrativo, se teletransporta usando una inyección de URL directa sobre la página final. Esto se registra en el historial del servidor bajo los headers del `Referer` (Revolico nota que llegaste a `publicar` sin venir de ninguna otra página de manera física).

**💡 SOLUCIÓN:**
- En lugar de forzar a `page.goto(".../item/publish")`, hacer que el bot navegue naturalmente desde tu cuenta dando click al botón azul "Publicar anuncio".
- Introducir scrolls muertos al azar (hacer *scroll up* y *scroll down* en la página vacía un par de segundos).

## 5. Exceso de Peticiones a Cloudflare y Captchas
Revolico está blindado fuertemente bajo la red y los algoritmos de Cloudflare (los "Checking your browser"). Cloudflare posee técnicas de recolección de *Fingerprinting* (las huellas digitales de la pestaña del navegador). Aunque tú usas un navegador Chrome con tu propio perfil remoto, la manipulación de código subyacente envía la bandera `webdriver: true` si no se aplica con cautela.

**💡 SOLUCIÓN:**
- Instalar la librería de camuflaje de bots para Playwright (llamada `playwright-stealth`). Esta pequeña capa oculta docenas de indicadores técnicos con los que páginas como Revolico averiguan si las acciones provienen de una terminal programada en Python.

---
> [!TIP] 
> Todo este diagnóstico se resume a un principio algorítmico: **"Haz que la máquina sea más lenta, ruidosa y caótica"**. Si quieres que actualicemos nuestros scripts para inyectar estos venenos "anti-bot" (como velocidades aleatorias y tecleos simulados), dímelo y preparamos estos *parches* directo sobre tus archivos de publicar.
