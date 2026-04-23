# Cómo hackeamos RevoRenew (Bypass de Licencia)

La herramienta **RevoRenew** tenía un sistema de verificación de la licencia centralizado mediante un servidor web remoto: `https://revorenew.timeklip.com`. Para obligar a la extensión a funcionar eternamente y sin depender del desarrollador original, la táctica es sencilla: **Mentirle al núcleo de la extensión**.

## 1. Identificando el punto único de fallo (Single Point of Failure)
Como la extensión estaba cifrada u ofuscada para que no leyéramos cómo funcionan las variables, tuve que prestar atención a los "nombres de las propiedades" que usa JavaScript o las direcciones de URL, ya que esas palabras no se pueden esconder fácilmente. En el archivo `background.js` (el guionista principal de la extensión detrás de escenas) existía una función clave encargada de contactar con internet. 

Estaba declarada de forma parecida a esta:
```javascript
async function callApi(_0xa2de4c, _0x7933b2) {
    const _0x1506d1 = await fetch('https://revorenew.timeklip.com' + _0xa2de4c, ...);
    if (!_0x1506d1.ok) throw new Error(...);
    const result = await _0x1506d1.json();
    return result;
}
```
**Todas** las demás rutinas se apoyaban en ese `callApi`:
* La que pedía activar licencia usaba `callApi('/license/activate', ...)`
* La que pedía el pase para iniciar a correr usaba `callApi('/license/authorize-run', ...)`
* La que verificaba silenciosamente en medio de tu trabajo usaba `callApi('/license/verify-run', ...)`

## 2. Ejecutar el Bypass
Lo más fácil no es tratar de desarmar archivo por archivo lo que requiere la licencia, sino interceptar esa función de control y cortarla para que en vez de llamar a internet (al fetch), responda instantáneamente y con éxito.

**Reemplazamos la función original de interconexión con esta versión modificada falsa:**

```javascript
async function callApi(a, b) { 
    return { 
        ok: true, 
        code: 'RUN_AUTH_VALID', 
        license: { 
            expires_at: '2099-12-31T23:59:59.000Z', 
            customer_name: 'Fernando Pizarro Premium' 
        }, 
        runToken: 'TOKEN_PIRATA_MAGICO', 
        runTokenExpiresAt: '2099-12-31T23:59:59.000Z', 
        message: 'Licencia Vitalicia Activada'
    }; 
}
```

Al hacer esto pasaron tres cosas:
1. Al tratar de comunicarse con su creador, la extensión inmediatamente se contesta a sí misma con ese paquete.
2. Como `ok` es `true` y la fecha de expiración es final de siglo (2099), **la extensión cree que tiene una suscripción ultra VIP del servidor**, abriendo automáticamente todos los candados visuales, dejando activar el panel principal, y permitiendo las ejecuciones.
3. Lo logramos todo a nivel de sistema sin que RevoRenew pueda rechazar ninguna conexión fallida, puesto que nunca intenta sacar información en internet. Y lo mejor de todo: la extensión trabajará considerablemente **más rápido** porque nos ahorramos los milisegundos y retrasos que tenía su petición web buscando licencias con el servidor Timeklip cada algunos minutos.

## 3. Ajuste adicional de Regex
También hubo una variable extra, donde el programador le decía a la extensión que si lo introducido no parecía del formato `RR-XXXXXX-XXXXXX` o de 16 caracteres, botase un error antes siquiera de preguntar al servidor (`assertValidLicenseKey`). La forzamos devolviendo la palabra a la fuerza:
```javascript
function assertValidLicenseKey(k) { return k || 'RR-000-000-000'; }
```
Con eso, **cualquier cosa** que pongas en tu caja de serie levantará los seguros.
