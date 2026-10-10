"""
utilidades_nombres.py — Módulo de gestión y rotación de nombres de productos
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proporciona utilidades para manejar múltiples nombres/títulos alternativos
para un producto (soporte de listas JSON o strings separados por comas),
y gestionar la cola rotativa (FIFO circular) entre cuentas y publicaciones.
"""

import json
from pathlib import Path


def parsear_nombres_producto(valor_nombre):
    """
    Parsea el campo 'nombre' de producto.json en una lista limpia de strings.
    
    Soporta:
      - Lista: ["Comoda", "vanity", "tocador"]
      - String con comas: "Comoda, vanity, tocador"
      - String simple: "Comoda"
    """
    if valor_nombre is None:
        return ["Sin título"]

    if isinstance(valor_nombre, list):
        nombres = [str(x).strip() for x in valor_nombre if str(x).strip()]
        return nombres if nombres else ["Sin título"]

    if isinstance(valor_nombre, str):
        valor_str = valor_nombre.strip()
        if not valor_str:
            return ["Sin título"]
        if "," in valor_str:
            nombres = [x.strip() for x in valor_str.split(",") if x.strip()]
            return nombres if nombres else ["Sin título"]
        return [valor_str]

    return [str(valor_nombre).strip() or "Sin título"]


def rotar_cola_nombres(lista_nombres):
    """
    Rota la lista de nombres pasando el primer elemento al final:
    [A, B, C] -> [B, C, A]
    """
    if not lista_nombres or len(lista_nombres) <= 1:
        return list(lista_nombres)
    return lista_nombres[1:] + [lista_nombres[0]]


def rotar_y_guardar_producto(ruta_producto_json):
    """
    Lee producto.json, rota la cola de nombres al siguiente elemento,
    y guarda el archivo preservando el tipo de dato original (str o list).
    
    Retorna:
      (nombre_usado, lista_nombres_rotada)
    """
    ruta = Path(ruta_producto_json)
    if not ruta.exists():
        return "Sin título", ["Sin título"]

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as e:
        print(f"    ⚠️  Error leyendo {ruta}: {e}")
        return "Sin título", ["Sin título"]

    valor_original = datos.get("nombre", "")
    es_lista = isinstance(valor_original, list)
    nombres = parsear_nombres_producto(valor_original)

    if not nombres:
        return "Sin título", ["Sin título"]

    nombre_usado = nombres[0]

    # Si solo hay 1 nombre, no hay nada que reordenar
    if len(nombres) <= 1:
        return nombre_usado, nombres

    # Rotar cola
    nombres_rotados = rotar_cola_nombres(nombres)

    if es_lista:
        datos["nombre"] = nombres_rotados
    else:
        datos["nombre"] = ", ".join(nombres_rotados)

    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"    ⚠️  Error guardando rotación en {ruta}: {e}")

    return nombre_usado, nombres_rotados


def contar_asignaciones_globales_producto(cuentas_dir, nombre_producto):
    """
    Cuenta cuántas veces un producto ha sido asignado en todas las cuentas registradas.
    """
    ruta_cuentas = Path(cuentas_dir)
    if not ruta_cuentas.exists():
        return 0

    total = 0
    for archivo in ruta_cuentas.glob("*.json"):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
                for pub in datos.get("publicaciones", []):
                    if pub.get("producto") == nombre_producto:
                        total += 1
        except Exception:
            continue

    return total
