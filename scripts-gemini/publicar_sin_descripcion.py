#!/usr/bin/env python3
"""
publicar_sin_descripcion.py — Publicador de Anuncios en Revolico SIN Descripciones
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Este script publica anuncios en Revolico dejando el campo de descripción completamente
en blanco (vacío). Se diseñó para pruebas A/B y diagnóstico: verificar si los baneos o
borrados de anuncios eran causados por similitud textual entre descripciones.

Uso:
  # Probar en modo preview (5 anuncios al azar sin publicar nada)
  python3 scripts-gemini/publicar_sin_descripcion.py --email catalogo.ventas.cuba@gmail.com --preview --limite 5

  # Publicación real (primero probar con 2 o 5)
  python3 scripts-gemini/publicar_sin_descripcion.py --email catalogo.ventas.cuba@gmail.com --limite 5

  # Publicar con ráfagas y pausas personalizadas
  python3 scripts-gemini/publicar_sin_descripcion.py --email catalogo.ventas.cuba@gmail.com --rafaga 5 --descanso 30
"""

import sys
import asyncio
from pathlib import Path

# Inyectar el argumento --sin-descripcion automáticamente si no fue pasado
if "--sin-descripcion" not in sys.argv:
    sys.argv.append("--sin-descripcion")

# Importar la lógica central de publicar_v2 en scripts-gemini
from publicar_v2 import main

if __name__ == "__main__":
    asyncio.run(main())
