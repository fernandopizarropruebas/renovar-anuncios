# 03 — Arquitectura de la v1.0.0

## Scripts Creados

Todos los scripts viven en `scripts-opus/` (la raíz del proyecto es `renovar-anuncios/`):

| Script | Líneas | Función |
|---|---|---|
| `mutar_imagenes.py` | ~525 | Genera variantes únicas de imágenes usando Pillow |
| `preparar_cuentas.py` | ~800 | Importa productos, genera variantes, asigna a cuentas, lleva estado |
| `publicar_v2.py` | ~480 | Publica en Revolico usando el sistema de estado |

## Estructura de Carpetas

```
renovar-anuncios/
├── scripts-opus/                    ← SCRIPTS v1.0.0 (todo el código nuevo)
│   ├── mutar_imagenes.py            ← Generador de variantes de imágenes
│   ├── preparar_cuentas.py          ← Organizador de productos por cuenta
│   ├── publicar_v2.py               ← Publicador mejorado
│   └── descripciones/               ← Banco EDITABLE de variación de texto
│       ├── sinonimos.txt            ← Palabras y alternativas
│       ├── frases_cierre.txt        ← Frases que se añaden al final
│       └── README.txt               ← Explicación del sistema
│
├── productos/                       ← DATOS DE PRODUCTOS (creado por importar-anuncios)
│   ├── buros/
│   │   ├── producto.json            ← {nombre, precio, moneda, categoria}
│   │   ├── descripcion_base.txt     ← Descripción original
│   │   ├── descripciones/           ← Variantes generadas de descripción
│   │   │   ├── variante_001.txt
│   │   │   ├── variante_002.txt
│   │   │   └── ...
│   │   └── imagenes/
│   │       ├── foto_01.jpg          ← Foto original
│   │       ├── foto_02.jpg          ← Otra foto original
│   │       ├── variantes_foto_01/   ← Variantes mutadas de foto_01
│   │       │   ├── foto_01_v001.jpg
│   │       │   ├── foto_01_v002.jpg
│   │       │   └── ...
│   │       └── variantes_foto_02/   ← Variantes mutadas de foto_02
│   │           ├── foto_02_v001.jpg
│   │           └── ...
│   ├── colchonetas/
│   └── ... (~504 carpetas de productos)
│
├── estado/                          ← SISTEMA DE ESTADO
│   ├── registro_global.json         ← Cuentas registradas
│   └── cuentas/
│       ├── cuenta1@gmail.com.json   ← Estado de cada cuenta
│       └── ...
│
├── anuncios/                        ← DATOS VIEJOS (backup, no se modifica)
│   ├── 54130535/
│   │   ├── datos.md
│   │   ├── foto_01.jpg
│   │   └── ...
│   └── index.json
│
├── publicar/                        ← SCRIPTS VIEJOS (referencia, no se usa)
│   └── publicar_anuncios_precio_original-fast.py
│
├── documentacion/                   ← DOCUMENTACIÓN VIEJA
│   └── revolico_guia_completa.md
│
├── RevoRenew last update/           ← EXTENSIÓN DE CHROME (solo referencia)
│
├── ideas-versiones/                 ← PLANIFICACIÓN
│   └── v1.0.0/
│       └── documentacion_v1.0.0/    ← ESTA DOCUMENTACIÓN
│
└── contexto.md                      ← Contexto original del proyecto
```

## Flujo de Datos

```
┌─────────────┐     importar-anuncios     ┌──────────────┐
│  anuncios/   │ ─────────────────────────→│  productos/   │
│  (viejos)    │                           │  (nuevos)     │
└─────────────┘                           └──────┬───────┘
                                                  │
                                    ┌─────────────┤
                                    ▼             ▼
                             generar-imagenes  generar-descripciones
                                    │             │
                                    ▼             ▼
                             variantes_*/     descripciones/
                             (mutadas)        (variantes txt)
                                    │             │
                                    └──────┬──────┘
                                           │
                                    asignar --email X
                                           │
                                           ▼
                                   ┌───────────────┐
                                   │   estado/      │
                                   │   cuentas/     │
                                   │   X.json       │
                                   └───────┬───────┘
                                           │
                                    publicar_v2.py
                                           │
                                           ▼
                                      Revolico.com
```

## Formato de producto.json

```json
{
  "nombre": "Buró de 100cm",
  "precio": "150",
  "moneda": "USD",
  "categoria": ["Hogar", "Muebles"],
  "id_original": "54130535"
}
```

## Formato de estado de cuenta (estado/cuentas/email.json)

```json
{
  "email": "ejemplo@gmail.com",
  "alias": "cuenta-1",
  "fecha_creacion": "2026-09-10T23:48:08",
  "publicaciones": [
    {
      "producto": "buros",
      "imagenes_usadas": [
        "variantes_foto_01/foto_01_v003.jpg",
        "variantes_foto_02/foto_02_v003.jpg"
      ],
      "descripcion_usada": "variante_003.txt",
      "fecha_asignacion": "2026-09-10T23:48:08",
      "estado": "pendiente",
      "url_revolico": null
    },
    {
      "producto": "colchonetas",
      "imagenes_usadas": ["variantes_foto_01/foto_01_v001.jpg"],
      "descripcion_usada": "variante_001.txt",
      "fecha_asignacion": "2026-09-10T23:48:08",
      "estado": "publicado",
      "url_revolico": "https://www.revolico.com/item/colchonetas-54356411",
      "fecha_publicacion": "2026-09-11T10:15:33"
    }
  ]
}
```

### Campos de cada publicación:

| Campo | Tipo | Descripción |
|---|---|---|
| `producto` | string | Nombre de la carpeta del producto en `productos/` |
| `imagenes_usadas` | lista | Rutas relativas de las imágenes asignadas (una variante por cada foto original) |
| `descripcion_usada` | string | Nombre del archivo de descripción usado |
| `estado` | string | `"pendiente"`, `"publicado"` o `"fallido"` |
| `url_revolico` | string/null | URL del anuncio publicado |
| `fecha_publicacion` | string/null | ISO timestamp de cuándo se publicó |

## Concepto Clave: "Sets" de Imágenes

Un producto puede tener múltiples fotos originales (ej: `foto_01.jpg`, `foto_02.jpg`, `foto_03.jpg`).

Cuando se generan variantes, se crean variantes independientes para **cada** foto original:
- `variantes_foto_01/foto_01_v001.jpg`, `foto_01_v002.jpg`, ...
- `variantes_foto_02/foto_02_v001.jpg`, `foto_02_v002.jpg`, ...
- `variantes_foto_03/foto_03_v001.jpg`, `foto_03_v002.jpg`, ...

Un **"set"** es un grupo de variantes con el mismo número de variante:
- Set 1: `foto_01_v001.jpg` + `foto_02_v001.jpg` + `foto_03_v001.jpg`
- Set 2: `foto_01_v002.jpg` + `foto_02_v002.jpg` + `foto_03_v002.jpg`

Cada publicación usa un set completo — así el anuncio tiene tantas fotos como el producto original.

## Concepto Clave: "Quemado Global" de Recursos

**Regla**: Una imagen o descripción usada en CUALQUIER cuenta no se puede reusar en NINGUNA otra.

¿Por qué? Revolico detecta imágenes duplicadas **entre cuentas**. Si la cuenta A y B usan la misma foto, ambas pueden ser baneadas.

El sistema lo maneja así:
1. Al asignar productos (`preparar_cuentas.py asignar`), el script lee TODOS los archivos `estado/cuentas/*.json`
2. Recopila todas las imágenes y descripciones ya usadas globalmente
3. Solo asigna recursos que NO hayan sido usados por NADIE

Si generas 20 variantes por imagen, puedes asignar el mismo producto a 20 cuentas diferentes, cada una con imágenes y descripciones únicas.
