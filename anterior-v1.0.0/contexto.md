# Contexto General de Automatización para Revolico

**Fecha de actualización:** 21 de abril de 2026
**Hora:** 12:50 PM

---

## 1. Contexto General del Proyecto

Este proyecto es una **suite de herramientas de automatización y scraping** construida en Python utilizando **Playwright**. Su objetivo principal es administrar, respaldar y optimizar la gestión masiva de anuncios en la plataforma cubana de clasificados **Revolico**.

Dado que Revolico utiliza Cloudflare y sistemas de seguridad que bloquean bots tradicionales, este sistema emplea una estrategia de "puerta trasera" de desarrollo: **Chrome DevTools Protocol (CDP)**.
En lugar de abrir un navegador invisible y automatizado desde cero (que pediría login y activaría CAPTCHAs), **los scripts se conectan a un navegador Google Chrome normal que el usuario ya tiene abierto** en su entorno local con su sesión activa. Esto permite al script interactuar con la web visualmente simulando las acciones humanas (hacer clics, scrollear, llenar formularios) sin disparar las protecciones antibot de forma habitual.

## 2. Herramientas y Scripts Principales

El ecosistema se divide en varias herramientas específicas que resuelven distintos problemas de la vida real de un vendedor masivo en Revolico:

### 2.1 Mantenimiento y Posicionamiento
* **`renovar_anuncios.py`** *(Documentado en `como_funciona.md`)*
  * **Para qué sirve:** Renueva todos los anuncios expirados de la cuenta para volver a posicionarlos arriba en los resultados de búsqueda.
  * **Cómo funciona:** Entra a la cuenta, hace *scroll loop* para burlar la carga perezosa de React, obtiene todos los IDs y entra anuncio por anuncio de abajo hacia arriba (para mantener el orden visual). Hace clic en "Renovar anuncio", cierra popups molestos y tiene rutinas de reintento en caso de que Cloudflare frene temporalmente la petición con "La verificación falló".

### 2.2 Respaldo y Migración (Carpeta: `descargar-todo-y-estadisticas/`)
* **`descargar_anuncios.py`**
  * **Para qué sirve:** Actúa como herramienta de extracción y backup completo.
  * **Cómo funciona:** Lee los anuncios de tu cuenta y clona toda la información desde sus páginas públicas de manera automatizada. Guarda el Título, Precio, Descripción, Categoría y descarga hasta 20 Fotos por anuncio organizándolos en la carpeta `/anuncios/`. Toda la metadata se mapea de forma maestra en `index.json`.

* **` public_anuncios.py`** *(Ubicado en `publicar/` )*
  * **Para qué sirve:** Publica anuncios "nuevos" de forma semiautomática extrayendo los datos clonados previamente.
  * **Cómo funciona:** Lee de la base local en `anuncios/`, rellena el formulario de publicación de Revolico, sube las fotos e interactúa con los menús dinámicos de las categorías. Utiliza un registro (`publicados_en_cuenta_nueva.json`) para rastrear el progreso y evitar duplicados si la operación falla a la mitad. Útil para llevar tus anuncios a una cuenta nueva tras bloqueos.

### 2.3 Monitoreo y Análisis (Carpeta: `descargar-todo-y-estadisticas/`)
* **`rastrear_visitas.py`**
  * **Para qué sirve:** Sustituye la falta de analíticas nativas en Revolico para los vendedores.
  * **Cómo funciona:** Navega por la URL pública de cada uno de tus anuncios, identifica el patrón de texto del contador (ej: "Hace 5 horas · 2 visitas") y va guardando el progreso diariamente en un archivo `historial.json`. Al terminar, te arroja un reporte resaltando cuáles ganaron más visitas día con día.

* **`verificar_anuncios.py`**
  * **Para qué sirve:** Sistema de alarma/auditoría.
  * **Cómo funciona:** Cruza la lista de tus anuncios guardados localmente (`index.json`) con los anuncios que realmente están listados en `/account` de Revolico. Te avisa si Revolico "borró mágicamente" algún anuncio, si te falta alguno por respaldar, y te da tranquilidad de que no hay discrepancias en tu inventario digital.

### 2.4 Herramientas de Desarrollo y Diagnóstico (Carpeta: `diagnostico/`)
* **`diagnostico_publicar.py`, `diagnostico_visitas_v2.py`, etc.**
  * **Para qué sirven:** Scripts rápidos de investigación con "fuerza bruta" en el DOM.
  * **Cómo funcionan:** Extraen todos los selectores (clases, forms, inputs) y el contenido en código crudo para cuando de un día para otro Revolico actualiza su página y cambia el diseño. Esto ayuda a adaptar y arreglar el resto de scripts rápidamente sin tener que usar el inspector del navegador manualmente por horas.

---

## 3. Flujo de Trabajo Típico (Workflow Operativo)

1. **Abrir Chrome Mode Debug:** Lanzar Chrome desde la terminal pasando el flag `--remote-debugging-port=9222`.
2. **Setup manual:** Acceder a tu cuenta en Revolico si la sesión no estaba guardada.
3. **Ejecutar Rutina:** Lanzar el script deseado desde otra terminal local.
4. **Interacción robótica:** Soltar las manos del teclado; el script de Python comandará ese Chrome para hacer las tareas aburridas de scraping/clics.
5. **Reportes:** Revisión de la terminal al concluir, viendo registros locales (como `historial.json` o `ultimo_reporte.txt`).
