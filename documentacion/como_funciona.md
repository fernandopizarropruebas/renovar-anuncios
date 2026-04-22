# Cómo funciona la automatización de Revolico

## El problema que resuelve

Tienes 100, 200 o más anuncios en Revolico. Para renovar cada uno manualmente tienes que:
entrar a tu cuenta → buscar el anuncio → tocar Gestionar → cerrar el popup → tocar Renovar → esperar → tocar Entendido → repetir con el siguiente.

Con 200 anuncios eso son fácilmente 30-40 minutos de trabajo repetitivo. El script lo hace solo en ese mismo tiempo sin que toques nada.

---

## Parte 1 — El comando de Google Chrome

Cuando escribes esto en la terminal:

```
google-chrome --remote-debugging-port=9222 --user-data-dir=/home/camiloueransim/.config/google-chrome-debug
```

Estás abriendo Chrome con tres instrucciones distintas:

### `google-chrome`
Simplemente llama al programa Chrome. Como cuando haces doble clic en el ícono, pero desde la terminal.

### `--remote-debugging-port=9222`
Esta es la parte más importante. Le dice a Chrome que abra una "puerta trasera" en el puerto 9222 de tu computadora.

¿Qué es un puerto? Imagina tu computadora como un edificio con muchas puertas numeradas. Cada puerta sirve para un tipo de comunicación distinto. El puerto 80 es para páginas web normales, el 22 es para SSH, etc. El 9222 es el que Chrome usa para recibir instrucciones de automatización.

Todos los navegadores modernos tienen esta funcionalidad incorporada porque la usan los propios desarrolladores de Chrome para hacer pruebas y depurar páginas web. Se llama **Chrome DevTools Protocol (CDP)**. No es algo que hayas instalado tú — viene con Chrome de fábrica. Tú solo lo estás activando con ese parámetro.

Una vez que Chrome está escuchando en ese puerto, cualquier programa en tu misma computadora puede conectarse y decirle cosas como "ve a esta URL", "haz clic en este botón", "dime qué texto hay en la página".

### `--user-data-dir=/home/camiloueransim/.config/google-chrome-debug`
Chrome guarda tu información (contraseñas, cookies, historial, sesiones) en una carpeta llamada "perfil". Normalmente esa carpeta está en `.config/google-chrome`.

Este parámetro le dice a Chrome que use una carpeta diferente llamada `google-chrome-debug`. Hay dos razones para esto:

1. **Chrome no permite abrir el mismo perfil dos veces a la vez.** Si intentas usar tu perfil normal con debugging activo, Chrome lo bloquea porque ya está en uso.
2. **Separación de sesiones.** El perfil de debug tiene su propia sesión. La primera vez está vacío y tienes que iniciar sesión en Revolico, pero Chrome lo recuerda para las próximas veces porque guarda las cookies en esa carpeta.

---

## Parte 2 — Cómo el script se conecta a Chrome

Al principio del script hay estas líneas:

```python
browser = await p.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]
```

**`localhost`** significa "esta misma computadora". No se conecta a internet, se conecta a Chrome que está corriendo en tu propia PC.

**`9222`** es el puerto que abriste con el comando anterior.

**`connect_over_cdp`** es la función de Playwright que habla el lenguaje CDP (Chrome DevTools Protocol) — el mismo protocolo que usan las herramientas de desarrollador cuando inspeccionas una página web.

Una vez conectado, el script tiene control total sobre Chrome: puede ver la página, hacer clics, leer texto, navegar a URLs, todo.

---

## Parte 3 — Cómo encuentra todos los anuncios

```python
await page.goto("https://www.revolico.com/account")
```

Esto le dice a Chrome "ve a esta URL", igual que si tú escribieras la dirección en la barra del navegador.

Luego el script hace scroll hacia abajo en un bucle:

```python
while True:
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)
    # ... compara si aparecieron anuncios nuevos
```

**`page.evaluate()`** es el mecanismo más poderoso del script. Le permite ejecutar código JavaScript directamente dentro de Chrome, como si lo escribieras en la consola del navegador. `window.scrollTo(0, document.body.scrollHeight)` es JavaScript puro que le dice al navegador "muévete al final de la página".

¿Por qué hay que hacer scroll? Porque Revolico usa **carga perezosa** (lazy loading): no carga todos los anuncios de golpe, solo carga los que están visibles en pantalla. A medida que bajas, carga más. El script simula ese comportamiento humano de ir bajando.

Después de cada scroll, el script cuenta cuántos botones "Gestionar" hay en la página. Cuando tres scrolls seguidos no agregan anuncios nuevos, sabe que llegó al final y para.

Para identificar los anuncios usa esto:

```python
links = await page.query_selector_all('a:has-text("Gestionar")')
```

**`query_selector_all`** busca en el código HTML de la página todos los elementos que cumplan una condición. `a:has-text("Gestionar")` significa "todos los enlaces (`<a>`) que contengan el texto Gestionar". Cada uno de esos enlaces tiene en su dirección el ID único del anuncio, por ejemplo: `/item/mesita-de-noche-54356411?token=_`. El script extrae el número `54356411` con una expresión regular y lo guarda.

---

## Parte 4 — Por qué procesa de abajo hacia arriba

Revolico muestra los anuncios ordenados por fecha de renovación: el más reciente arriba. Si el script renovara de arriba hacia abajo, los primeros anuncios renovados irían subiendo pero los últimos quedarían abajo para siempre, en la misma posición que tenían antes.

Al procesar al revés (de abajo hacia arriba), el último anuncio que se renueva es el que estaba más arriba originalmente. Como es el último en subir, queda en la posición número 1. El resultado final es que todos los anuncios quedan en un orden razonable, con los que antes estaban arriba todavía arriba.

---

## Parte 5 — Cómo renueva cada anuncio

Para cada ID encontrado, el script construye la URL de gestión:

```python
url_manage = f"https://www.revolico.com/item/{item_id}/_/manage"
await page.goto(url_manage)
```

Una vez en esa página, lo primero que hace es cerrar el popup de "Más ventajas con Destacados" si aparece. Ese popup es un anuncio de pago que Revolico muestra para que pagues por destacar tu anuncio. El script lo cierra así:

```python
btn = await page.query_selector('[data-slot="dialog-portal"] button')
await btn.click()
```

**`query_selector`** busca un único elemento en el HTML. `[data-slot="dialog-portal"]` es el contenedor del popup, y `button` dentro de él es el botón X para cerrarlo. Esto funciona porque Playwright puede leer todo el código HTML de la página en tiempo real, no solo lo que se ve visualmente.

Luego busca el botón de renovar:

```python
botones = await page.query_selector_all('button:has-text("Renovar anuncio")')
await page.evaluate("el => el.click()", botones[0])
```

El clic se hace con JavaScript (`el.click()`) en vez del clic normal de Playwright. La diferencia es importante: el clic normal de Playwright simula un clic físico en coordenadas de pantalla, y si hay algún elemento encima (aunque sea invisible) lo bloquea. El clic por JavaScript se ejecuta directamente sobre el elemento sin importar qué haya encima.

---

## Parte 6 — Cómo maneja el error de Cloudflare

A veces cuando haces clic en Renovar, Cloudflare (el sistema de seguridad de Revolico) interviene y muestra "La verificación falló". Esto pasa porque detecta que las acciones son muy rápidas o el contexto del browser le parece sospechoso.

El script detecta cuál de los dos resultados apareció:

```python
if await page.query_selector('text="Tu anuncio fue renovado."'):
    # Éxito
    
if await page.query_selector('text="La verificación falló"'):
    # Hacer clic en Reintentar
    reintentar = await page.query_selector('text="Reintentar"')
    await page.evaluate("el => el.click()", reintentar)
```

`page.query_selector('text="..."')` busca un elemento que contenga exactamente ese texto. Si lo encuentra, sabe qué pasó y actúa en consecuencia. Intenta hasta 3 veces por anuncio antes de rendirse.

---

## Resumen del flujo completo

```
1. Tú abres Chrome con el puerto de debugging activado
2. Tú entras a Revolico y haces login manualmente
3. Corres el script en otra terminal
4. El script se conecta a Chrome por el puerto 9222
5. Navega a revolico.com/account
6. Hace scroll hasta cargar TODOS los anuncios (sean 100, 200 o los que sean)
7. Extrae los IDs únicos de cada anuncio
8. Los invierte (para procesar de abajo hacia arriba)
9. Por cada anuncio:
   a. Navega a su página de gestión
   b. Cierra el popup de Destacados si aparece
   c. Hace clic en Renovar anuncio
   d. Si Cloudflare falla, reintenta hasta 3 veces
   e. Confirma con Entendido
10. Al terminar muestra un resumen con cuántos renovó
```

Todo esto ocurre en el mismo Chrome que tienes abierto, con tu sesión activa, sin que Revolico pueda distinguirlo fácilmente de un usuario humano navegando (excepto por la velocidad).
