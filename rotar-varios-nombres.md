Aquí tienes un **prompt listo para copiar y pegar** que puedes usar con cualquier IA en el futuro, junto con la explicación de cómo funciona la lógica por debajo.

---

### 📋 Prompt para copiar y pegar a la IA

```text
Actúa como un desarrollador experto en automatización. Necesito configurar el campo "nombre" en los archivos `producto.json` de un grupo de productos relacionados para que soporten rotación de títulos multi-cuenta sin colisiones.

### Contexto:
Tengo un grupo de N productos que son variantes o modelos similares (por ejemplo: [ESCRIBE AQUÍ TUS PRODUCTOS O DEJA QUE LA IA LOS LEA DE LA CARPETA]).
El sistema de publicación rota los nombres como una cola circular (el primer nombre se usa y pasa al final para la siguiente cuenta).

### Requisito Estricto:
Necesito que apliques un Cuadrado Latino (Latin Square) entre los productos y sus nombres alternativos:
1. Cada producto debe contener en su campo "nombre" (como string separado por comas) la lista de todos los N nombres posibles.
2. Cada producto debe empezar en la Ronda 1 con su nombre natural/propio.
3. REGLA FUNDAMENTAL: En cualquier ronda (posición k de la lista), NINGÚN producto puede tener el mismo nombre que otro. En cada cuenta/ronda, los N productos deben tener títulos 100% únicos (cero colisiones).
4. Ningún producto puede tener nombres repetidos dentro de su propia lista.

### Lo que debes hacer:
1. Revisa los productos objetivo y extrae sus nombres base.
2. Genera la matriz de rotación matemática usando la fórmula de desplazamiento cíclico:
   Para el producto en índice i, su lista es: [nombres[(i + j) % N] para j de 0 a N-1].
3. Escribe un script rápido para verificar matemáticamente que en cada una de las N rondas la lista de títulos tenga exactamente N elementos únicos (sin duplicados).
4. Actualiza los archivos `producto.json` de cada carpeta preservando los demás campos (precio, moneda, categoría, id_original).
5. Muestra una tabla resumen de la rotación para verificar las rondas.
```

---

### 🧠 ¿Cómo funciona esta lógica y por qué es infalible?

#### 1. El concepto: Cuadrado Latino (Latin Square)
Es un concepto algebraico y combinatorio. Imagina un tablero de ajedrez o sudoku donde:
- **Filas = Productos** (cada producto tiene su lista de nombres).
- **Columnas = Cuentas o Rondas de publicación** (qué título verá Revolico en esa tanda).

La regla es que **ningún nombre se repite ni en la misma fila ni en la misma columna**.

#### 2. La fórmula matemática
Si tienes $N$ productos ($0, 1, 2, \dots, N-1$) y una lista base de $N$ nombres:

$$\text{Nombre del producto } i \text{ en la ronda } j = \text{Nombres}[(i + j) \pmod N]$$

- En la **Ronda 1** ($j = 0$): El producto $i$ usa el nombre $i$ (su nombre propio).
- En la **Ronda 2** ($j = 1$): Cada producto avanza 1 posición. Como todos avanzan exactamente el mismo paso cíclico, **los 10 títulos resultantes siguen siendo todos distintos entre sí**.
- **Resultado:** Es **matemáticamente imposible** que dos productos choquen en la misma cuenta o ronda.