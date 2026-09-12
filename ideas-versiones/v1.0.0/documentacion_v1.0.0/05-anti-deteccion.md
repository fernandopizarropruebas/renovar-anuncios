# 05 — Estrategias Anti-Detección

## Resumen

Revolico tiene múltiples capas de detección de bots y contenido duplicado. Este documento explica cada amenaza y cómo la v1.0.0 la contrarresta.

---

## 1. Detección de Imágenes Duplicadas

### Cómo detecta Revolico
- **MD5/SHA**: Si dos archivos son idénticos byte a byte, los detecta trivialmente
- **Hash perceptual (pHash/dHash)**: Compara la "huella visual" de la imagen. Dos fotos que se ven igual pero son archivos distintos (ej: guardada con diferente calidad JPEG) siguen siendo detectadas como iguales
- **Umbral**: Distancia de Hamming < 5-10 = "misma imagen"

### Qué NO funciona (lo que hacía el script viejo)
- Cambiar brillo ±3% → distancia dHash ~2-3, DETECTADA
- Recortar 2 píxeles → distancia dHash ~1-4, DETECTADA
- Solo cambiar calidad JPEG → MD5 diferente pero dHash igual, DETECTADA

### Qué SÍ funciona (v1.0.0)
`mutar_imagenes.py` aplica **múltiples transformaciones agresivas simultáneas**:

| Transformación | Intensidad | Efecto en dHash |
|---|---|---|
| **Flip horizontal** | 50% probabilidad | Distancia +40-60 (MUY efectivo) |
| **Crop agresivo** | 5-45px por lado | Distancia +15-30 |
| **Rotación** | ±3° con relleno | Distancia +10-20 |
| **Shift de hue (HSV)** | ±15° | Distancia +10-25 |
| **Brillo** | 0.88-1.12 | Distancia +3-8 |
| **Contraste** | 0.88-1.12 | Distancia +3-8 |
| **Saturación** | 0.82-1.18 | Distancia +5-10 |
| **Nitidez** | 0.7-1.5 | Distancia +2-5 |
| **Blur leve** | 0.3-0.7 radio | Distancia +2-5 |
| **Borde (padding)** | 1-6px color aleatorio | Distancia +5-15 |
| **Calidad JPEG** | 70-95 (variable) | Cambia MD5 |
| **Limpieza EXIF** | Total | Elimina metadatos |

**Resultado probado**: Distancia promedio 105/256, mínima 44/256. Todas las variantes son únicas tanto vs la original como entre sí.

### Verificación
```bash
python3 scripts-opus/mutar_imagenes.py foto.jpg -n 10 --verificar
```

Muestra:
- Distancia de cada variante vs la original
- Distancia de cada variante vs todas las demás variantes
- Pares peligrosos (si alguno tiene distancia ≤ 10)

---

## 2. Detección de Descripciones Duplicadas

### Cómo detecta Revolico
- Compara textos de descripciones entre anuncios del mismo usuario y entre usuarios diferentes
- Textos idénticos o muy similares → marca como spam

### Estrategia v1.0.0
Cada producto tiene una `descripcion_base.txt` que se varía automáticamente:

1. **Sustitución de sinónimos** (50% probabilidad por palabra): "vendo" → "ofrezco", "nuevo" → "sin uso"
2. **Reordenamiento de oraciones** (40% probabilidad): baraja oraciones del medio
3. **Frases de cierre aleatorias**: añade 1-2 frases del banco al final
4. **Variación de espaciado**: cambios en saltos de línea

### Archivos editables
- `scripts-opus/descripciones/sinonimos.txt` — formato: `palabra = alternativa1, alternativa2`
- `scripts-opus/descripciones/frases_cierre.txt` — una frase por línea

### Quemado global
Cada variante de descripción se usa UNA SOLA VEZ en todas las cuentas combinadas. Si generas 20 variantes, puedes usar la misma descripción base en 20 cuentas diferentes.

---

## 3. Cloudflare

### Cómo funciona
- Cloudflare analiza el comportamiento del navegador en tiempo real
- Si sospecha de automatización: muestra página "Just a moment..." con captcha/challenge
- Señales que detecta: clics demasiado rápidos, sin movimiento de mouse, timing perfecto, fingerprint de Playwright

### Qué hacía el script viejo (MAL)
```python
sys.exit(1)  # ← PEOR RESPUESTA POSIBLE
```
Matar el script dejaba Chrome con la página de challenge activa, sin resolver.

### Qué hace la v1.0.0 (BIEN)
```python
# Pausa de 2-5 minutos
await asyncio.sleep(random.uniform(120, 300))
# Intenta navegar de nuevo
# Si sigue activo: para el script limpiamente
# Si se resolvió: continúa publicando
```

Comportamiento:
1. Detecta Cloudflare por título de página y elementos del DOM
2. Pausa 2-5 minutos (da tiempo a resolver manualmente si estás cerca)
3. Intenta navegar a `/account` para verificar si se resolvió
4. Si después de 3 Cloudflares seguidos no se resuelve: detiene el script limpiamente
5. Guarda el estado antes de detenerse (los pendientes quedan marcados)

---

## 4. Comportamiento del Bot

### Movimiento de mouse orgánico
Antes de cada clic, el publicador mueve el mouse con:
- Punto de origen aleatorio
- 5-12 pasos intermedios
- Curva suave + ruido aleatorio (±5px)
- Velocidad variable (10-40ms entre pasos)

### Pausas
| Acción | Script viejo | v1.0.0 |
|---|---|---|
| Entre anuncios | 10-18 seg | **30-90 seg** |
| Carga de página | 4 seg fijo | **4-7 seg aleatorio** |
| Antes de escribir | instantáneo | **0.2-0.5 seg** |
| Después de escribir | instantáneo | **0.3-0.8 seg** |
| Antes de publicar | instantáneo | **1-2 seg** |
| Descanso de ráfaga | 20 min | **30 min ±1 min** |

### Ráfagas
- Publica N anuncios (default: 5)
- Descansa M minutos (default: 30)
- Los números son configurables via argumentos del CLI

### Limpieza de huellas
```javascript
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
delete window.__playwright;
```

### Método de escritura
Usa `element.fill()` de Playwright, que Chrome interpreta como autocompletado del navegador (no como pulsaciones de teclas robóticas).

---

## 5. Quemado Global de Recursos

### El problema
Si la cuenta A publica un producto con `foto_01_v005.jpg` y la cuenta B publica el mismo producto con `foto_01_v005.jpg`, Revolico detecta que son la misma imagen y puede banear ambas cuentas.

### La solución
El sistema lleva un registro global en `estado/cuentas/`. Al asignar recursos a una cuenta:

1. Lee TODOS los archivos `estado/cuentas/*.json`
2. Recopila todas las imágenes y descripciones ya usadas por cualquier cuenta
3. Solo asigna recursos que NO estén en la lista global

### Capacidad
Si generas N variantes, puedes tener N cuentas publicando el mismo producto con imágenes y descripciones completamente diferentes.

---

## 6. Resumen de Capas de Protección

```
                          Amenaza                  Contramedida
                     ┌─────────────────────────────────────────────┐
  Capa 1 - Imagen    │ Hash perceptual (pHash/dHash)  │ Mutación agresiva (flip+crop+HSV+...)  │
  Capa 2 - Texto     │ Comparación de descripciones   │ Sinónimos + reorden + frases únicas    │
  Capa 3 - Cloudflare│ Análisis de comportamiento     │ Mouse orgánico + pausas + fill()       │
  Capa 4 - Ráfagas   │ Volumen sospechoso             │ 5 anuncios + descanso 30min            │
  Capa 5 - Multi-cta │ Detección entre cuentas        │ Quemado global de recursos             │
  Capa 6 - Cloudflare│ Challenge/captcha              │ Pausa + espera + reintento             │
                     └─────────────────────────────────────────────┘
```
