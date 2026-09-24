/**
 * RevoRenew v2 — content.js
 * 
 * Reescritura limpia basada en la lógica original de RevoRenew 0.3.3.5.
 * Actualizado para la nueva UI de Revolico (Sep 2026).
 * 
 * Cambios principales vs la versión original:
 *   1. Selectores actualizados (/account/ads, botón "Renovar" en barra inferior, etc.)
 *   2. Sistema de reintentos para anuncios fallidos/skipped
 *   3. Mejor detección de renovación exitosa (toast, desaparición de botón)
 *   4. Código limpio y legible
 */

// ═══════════════════════════════════════════════════════════════
//  CONSTANTES DE ESTADO (deben coincidir con background.js)
// ═══════════════════════════════════════════════════════════════

const STORAGE_DEFAULTS = {
  runState: 'idle',
  processedIds: [],
  renewedIds: [],
  notReadyIds: [],
  skippedIds: [],
  errorIds: [],
  queue: [],
  lastProcessedId: null,
  startedAt: null,
  updatedAt: null,
  currentItemId: null,
  lastResult: null,
  lastError: null,
  summary: '',
  connectionMode: 'normal'
};

// ═══════════════════════════════════════════════════════════════
//  CONFIGURACIÓN DE TIMING
// ═══════════════════════════════════════════════════════════════

function getTimingProfile(mode = 'normal') {
  if (mode === 'slow') {
    return {
      pageSettleRounds: 18,
      pageSettleSleepMs: 900,
      collectPasses: 8,
      collectSleepMs: 2400,
      preInspectLoops: 12,
      preInspectSleepMs: 1400,
      postClickLoops: 20,
      postClickSleepMs: 1400,
      modalCloseSleepMs: 1800,
      manageRetryLoops: 2,
      accountReloadOnEmpty: true
    };
  }
  return {
    pageSettleRounds: 8,
    pageSettleSleepMs: 500,
    collectPasses: 5,
    collectSleepMs: 1400,
    preInspectLoops: 6,
    preInspectSleepMs: 800,
    postClickLoops: 12,
    postClickSleepMs: 1000,
    modalCloseSleepMs: 1200,
    manageRetryLoops: 1,
    accountReloadOnEmpty: false
  };
}

// ═══════════════════════════════════════════════════════════════
//  UTILIDADES BÁSICAS
// ═══════════════════════════════════════════════════════════════

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function dedupe(arr = []) {
  return [...new Set((arr || []).filter(Boolean))];
}

/**
 * Extrae el ID numérico del anuncio de una URL.
 * Soporta formatos: /item/57493855/... o slug-57493855?...
 */
function getItemIdFromUrl(url = location.href) {
  const match = url.match(/\/item\/(\d+)/);
  return match ? match[1] : null;
}

/**
 * Detecta si estamos en /account o /account/ads
 */
function isAccountPage() {
  return /\/account(?:\/ads)?(?:$|[/?#])/.test(location.pathname + location.search);
}

/**
 * Detecta si estamos en una página de gestión /item/{ID}/_/manage
 */
function isManagePage() {
  return /\/item\/\d+\/.*\/manage(?:$|[/?#])/.test(location.pathname + location.search) ||
         /\/item\/\d+\/_\/manage(?:$|[/?#])/.test(location.pathname + location.search);
}

/**
 * Verifica si un elemento es visible en pantalla.
 */
function isVisible(el) {
  if (!el) return false;
  const style = window.getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return style.display !== 'none' &&
         style.visibility !== 'hidden' &&
         Number(style.opacity || '1') > 0 &&
         rect.width > 0 &&
         rect.height > 0;
}

/**
 * Devuelve todos los elementos clicables visibles de la página.
 */
function clickableElements() {
  return [...document.querySelectorAll('button, a, [role="button"], [data-testid="renovate-button"]')]
    .filter(isVisible);
}

/**
 * Devuelve el texto completo del body.
 */
function pageText() {
  return (document.body?.innerText || '').trim();
}

// ═══════════════════════════════════════════════════════════════
//  COMUNICACIÓN CON BACKGROUND.JS
// ═══════════════════════════════════════════════════════════════

async function getState() {
  const stored = await chrome.storage.local.get(STORAGE_DEFAULTS);
  return { ...STORAGE_DEFAULTS, ...stored };
}

async function updateState(patch) {
  return chrome.runtime.sendMessage({ type: 'CONTENT_STATE_UPDATE', patch });
}

async function assertRunAuthorization(opts = {}) {
  const result = await chrome.runtime.sendMessage({
    type: 'VERIFY_RUN_AUTH',
    allowCached: opts.allowCached !== false,
    allowReauthorize: opts.allowReauthorize !== false
  });

  if (result?.ok) return result;

  const errorMsg = result?.error || 'La autorización de ejecución ya no es válida.';
  await updateState({
    runState: 'paused',
    currentItemId: null,
    lastError: errorMsg,
    summary: 'Ejecución pausada: ' + errorMsg
  });
  return null;
}

// ═══════════════════════════════════════════════════════════════
//  BÚSQUEDA DE BOTONES
// ═══════════════════════════════════════════════════════════════

/**
 * Busca un elemento clicable con texto exacto.
 */
function findButtonByExactText(text) {
  return clickableElements().find(el => (el.textContent || '').trim() === text);
}

/**
 * Busca el botón de renovar en la página de gestión.
 * Actualizado para la nueva UI de Revolico (Sep 2026):
 *  - Primero busca por data-testid
 *  - Luego busca por texto exacto "Renovar" (nuevo) o "Renovar anuncio" (viejo)
 */
function findRenewButton() {
  // 1. Buscar por data-testid (el más confiable)
  const byTestId = document.querySelector('[data-testid="renovate-button"]:not([disabled])');
  if (byTestId && isVisible(byTestId)) return byTestId;

  // 2. Buscar entre todos los elementos clicables por texto
  return clickableElements().find(el => {
    const text = (el.textContent || '').trim();
    return !el.disabled && (
      text === 'Renovar' ||           // ← NUEVO en Sep 2026
      text === 'Renovar anuncio' ||    // ← VIEJO (fallback)
      text === 'Re-publicar' ||
      text === 'Renovar anuncio destacado'
    );
  });
}

/**
 * Simula un clic humano en un elemento con eventos de mouse reales.
 */
function dispatchHumanClick(el) {
  if (!el) return false;
  el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  ['pointerdown', 'mousedown', 'mouseup', 'click'].forEach(type => {
    el.dispatchEvent(new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window
    }));
  });
  return true;
}

// ═══════════════════════════════════════════════════════════════
//  CARGA DE PÁGINA
// ═══════════════════════════════════════════════════════════════

/**
 * Espera a que la página tenga suficiente contenido cargado.
 */
async function waitForPageSettled(timing) {
  for (let i = 0; i < timing.pageSettleRounds; i++) {
    if (document.body && document.body.innerText.length > 300) return true;
    await sleep(timing.pageSettleSleepMs);
  }
  return false;
}

// ═══════════════════════════════════════════════════════════════
//  RECOLECCIÓN DE IDs DESDE /account/ads
// ═══════════════════════════════════════════════════════════════

/**
 * Hace scroll y recopila todos los IDs de anuncios desde los links de la página.
 * Actualizado: busca links a /item/ que contengan un ID numérico.
 */
async function collectAllIds(timing) {
  const passes = timing.collectPasses;
  const allIds = new Set();
  let noChangeCount = 0;

  for (let i = 0; i < passes; i++) {
    // Buscar todos los links a anuncios
    const links = [...document.querySelectorAll('a[href*="/item/"]')];
    const prevSize = allIds.size;

    links.forEach(link => {
      const href = link.href || '';
      // Excluir links a /item/publish
      if (!href.includes('/item/') || href.includes('/item/publish')) return;

      // Extraer ID: formato -57493855? o /item/57493855/
      const match = href.match(/-(\d{6,})(?:\?|$)/) || href.match(/\/item\/(\d{6,})(?:\/|\?|$)/);
      if (match) allIds.add(match[1]);
    });

    if (allIds.size === prevSize) {
      noChangeCount += 1;
    } else {
      noChangeCount = 0;
    }

    if (noChangeCount >= 2) break;

    // Scroll hacia abajo para cargar más (lazy loading)
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' });
    await sleep(timing.collectSleepMs);
  }

  // Volver arriba
  window.scrollTo({ top: 0, behavior: 'smooth' });
  return [...allIds];
}

// ═══════════════════════════════════════════════════════════════
//  INSPECCIÓN DE PÁGINA DE GESTIÓN
// ═══════════════════════════════════════════════════════════════

/**
 * Analiza la página de gestión /item/{ID}/_/manage para determinar 
 * qué acciones están disponibles y qué estado tiene el anuncio.
 */
async function inspectManagePage() {
  const text = pageText();
  const buttons = clickableElements().map(el => ({
    text: (el.textContent || '').trim(),
    aria: (el.getAttribute('aria-label') || '').trim(),
    disabled: !!el.disabled
  }));
  const textLower = text.toLowerCase();

  // Indicadores de que el anuncio no se puede renovar todavía
  const notReadyPhrases = [
    'podrás renovar',
    'renovar nuevamente más tarde',
    'aun no puedes renovar',
    'aún no puedes renovar',
    'todavía no puedes renovar',
    'todavia no puedes renovar',
    'renovar nuevamente mas tarde',
    'debes esperar',
    'disponible en',
    'disponible nuevamente',
    'faltan',
    'horas',
    'minutos',
    'podra renovar'
  ];

  return {
    // ¿Hay botón de renovar visible?
    hasRenew: !!findRenewButton(),

    // ¿Hay botón de "Reintentar"?
    hasRetry: buttons.some(b => b.text.includes('Reintentar')),

    // ¿La renovación fue exitosa?
    hasSuccess: /Tu anuncio fue renovado\.|Anuncio renovado|renovado con éxito/i.test(text),

    // ¿Hay botón "Entendido" (cierre de modal de éxito)?
    hasUnderstood: buttons.some(b => b.text === 'Entendido'),

    // ¿Tiene los botones de gestión normales? (indica que la página cargó bien)
    // Actualizado para la nueva UI: ahora busca botones individuales en barra inferior
    hasManageActions: (
      /Editar/i.test(text) ||
      /Eliminar/i.test(text) ||
      /Renovar/i.test(text) ||
      /Compartir/i.test(text) ||
      /Gestiona tu anuncio/i.test(text)
    ),

    // ¿Hay que iniciar sesión?
    hasLogin: /iniciar sesi[oó]n/i.test(text) || /\/login/.test(location.href),

    // ¿Hay un challenge de Cloudflare?
    hasCloudflare: /just a moment/i.test(document.title) ||
                   /challenges\.cloudflare\.com/i.test(location.href),

    // ¿El anuncio no está listo para renovar?
    hasNotReady: notReadyPhrases.some(phrase => textLower.includes(phrase)),

    // Muestras para debug
    bodySample: text.slice(0, 1200),
    buttonsSample: buttons.slice(0, 10)
  };
}

// ═══════════════════════════════════════════════════════════════
//  CERRAR POPUP DE DESTACADOS
// ═══════════════════════════════════════════════════════════════

/**
 * Cierra el popup de "Anuncios Destacados" que aparece al entrar a /manage.
 * Actualizado para las 2 variantes visuales de Revolico (Sep 2026).
 */
async function closeHighlightPopup() {
  // Selectores del botón ✕ de cerrar (ambas variantes)
  const closeSelectors = [
    'button[aria-label="Close"]',
    'button[aria-label="Cerrar"]',
    '[data-slot="dialog-close"]',
    '[data-slot="dialog-portal"] button:first-child',
    'div[role="dialog"] button[aria-label="Close"]',
    'div[role="dialog"] button[aria-label="Cerrar"]'
  ];

  for (const selector of closeSelectors) {
    try {
      const btn = document.querySelector(selector);
      if (btn && isVisible(btn)) {
        dispatchHumanClick(btn);
        await sleep(500);
        return true;
      }
    } catch (e) {
      // Continuar con el siguiente selector
    }
  }

  // Fallback: clic en el overlay/backdrop
  try {
    const overlay = document.querySelector('[data-slot="dialog-overlay"]');
    if (overlay && isVisible(overlay)) {
      overlay.click();
      await sleep(500);
      return true;
    }
  } catch (e) {}

  // Último recurso: tecla Escape
  try {
    document.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Escape',
      code: 'Escape',
      bubbles: true
    }));
    await sleep(500);
    const dialog = document.querySelector('div[role="dialog"]');
    if (!dialog || !isVisible(dialog)) return true;
  } catch (e) {}

  return false;
}

// ═══════════════════════════════════════════════════════════════
//  FINALIZAR PROCESAMIENTO DE UN ANUNCIO
// ═══════════════════════════════════════════════════════════════

/**
 * Registra el resultado del procesamiento de un anuncio y lo quita de la cola.
 */
async function finalizeItem(itemId, outcome, detail) {
  const state = await getState();
  const queue = [...(state.queue || [])];
  const newQueue = queue.filter(id => id !== itemId);
  const processedIds = dedupe([...(state.processedIds || []), itemId]);

  const patch = {
    queue: newQueue,
    processedIds,
    lastProcessedId: itemId,
    currentItemId: null,
    lastResult: {
      itemId,
      outcome,
      detail,
      at: new Date().toISOString()
    },
    lastError: outcome === 'error' ? detail : null,
    summary: itemId + ': ' + detail
  };

  // Añadir a la lista correspondiente
  if (outcome === 'renewed') {
    patch.renewedIds = dedupe([...(state.renewedIds || []), itemId]);
  } else if (outcome === 'not_ready') {
    patch.notReadyIds = dedupe([...(state.notReadyIds || []), itemId]);
  } else if (outcome === 'skipped') {
    patch.skippedIds = dedupe([...(state.skippedIds || []), itemId]);
  } else if (outcome === 'error') {
    patch.errorIds = dedupe([...(state.errorIds || []), itemId]);
  }

  await updateState(patch);
}

// ═══════════════════════════════════════════════════════════════
//  NAVEGACIÓN
// ═══════════════════════════════════════════════════════════════

/**
 * Navega a la página de cuenta /account/ads.
 * Actualizado: URL ahora es /account/ads en vez de /account.
 */
async function goToAccount() {
  const state = await getState();
  if (state.runState !== 'running') return;
  location.href = 'https://www.revolico.com/account/ads';
}

// ═══════════════════════════════════════════════════════════════
//  LÓGICA DE /account/ads
// ═══════════════════════════════════════════════════════════════

/**
 * Maneja la lógica cuando estamos en /account/ads:
 * 1. Recopila los IDs de anuncios haciendo scroll
 * 2. Filtra los ya procesados
 * 3. Navega al primero de la cola
 */
async function handleAccountPage() {
  const state = await getState();
  const timing = getTimingProfile(state.connectionMode);

  await waitForPageSettled(timing);

  if (state.runState !== 'running') return;

  // Verificar autorización
  const auth = await assertRunAuthorization({ allowCached: true, allowReauthorize: true });
  if (!auth) return;

  let queue = [...(state.queue || [])];

  // Si la cola está vacía, recolectar IDs desde la página
  if (!queue.length) {
    await updateState({ summary: 'Extrayendo IDs desde /account...' });
    const allIds = await collectAllIds(timing);
    const pending = allIds.filter(id => !(state.processedIds || []).includes(id));
    queue = dedupe(pending);
    await updateState({
      queue,
      summary: queue.length
        ? 'Cola lista: ' + queue.length + ' anuncio(s) pendientes.'
        : 'No se detectaron anuncios pendientes desde /account.'
    });
  }

  // Verificar estado actualizado
  const updatedState = await getState();
  if (updatedState.runState !== 'running') return;

  // Si no hay anuncios pendientes, terminar
  if (!queue.length) {
    await updateState({
      runState: 'completed',
      currentItemId: null,
      summary: 'Proceso terminado. No quedan anuncios en cola.'
    });
    return;
  }

  // Navegar al primer anuncio de la cola
  const nextId = queue[0];
  await updateState({
    currentItemId: nextId,
    summary: 'Abriendo gestión del anuncio ' + nextId + '...'
  });
  location.href = 'https://www.revolico.com/item/' + nextId + '/_/manage';
}

// ═══════════════════════════════════════════════════════════════
//  CERRAR MODAL DE ÉXITO
// ═══════════════════════════════════════════════════════════════

async function maybeCloseSuccessModal(timing) {
  const btn = findButtonByExactText('Entendido');
  if (btn) {
    dispatchHumanClick(btn);
    await sleep(timing.modalCloseSleepMs);
  }
}

// ═══════════════════════════════════════════════════════════════
//  INTENTO DE RENOVACIÓN
// ═══════════════════════════════════════════════════════════════

/**
 * Intenta renovar un anuncio individual.
 * 
 * Flujo:
 *   1. Espera a que la página cargue
 *   2. Cierra popup de Destacados si aparece
 *   3. Verifica el estado del anuncio
 *   4. Hace clic en el botón Renovar
 *   5. Verifica el resultado (éxito/fallo)
 *   6. Navega de vuelta a /account/ads
 */
async function attemptRenew(itemId) {
  // Verificar autorización
  const auth = await assertRunAuthorization({ allowCached: true, allowReauthorize: true });
  if (!auth) return;

  const state = await getState();
  const timing = getTimingProfile(state.connectionMode);

  // ── Esperar a que la página cargue y cerrar popup de Destacados ──
  await sleep(1500); // Dar tiempo al popup de aparecer
  await closeHighlightPopup();
  await sleep(500);

  // ── Inspeccionar la página ──
  let info = await inspectManagePage();

  // Esperar más si la página aún no tiene contenido
  for (let i = 0; i < timing.preInspectLoops; i++) {
    if (info.hasRetry || info.hasRenew || info.hasSuccess ||
        info.hasUnderstood || info.hasCloudflare || info.hasLogin) break;
    await sleep(timing.preInspectSleepMs);
    info = await inspectManagePage();
  }

  // ── Manejar casos especiales ──

  // Cloudflare
  if (info.hasCloudflare) {
    await finalizeItem(itemId, 'error', 'Bloqueado por Cloudflare/verificación manual.');
    await goToAccount();
    return;
  }

  // Login requerido
  if (info.hasLogin) {
    await finalizeItem(itemId, 'error', 'Sesión no válida o login requerido.');
    await goToAccount();
    return;
  }

  // Reintentar (Revolico devolvió error)
  if (info.hasRetry) {
    await finalizeItem(itemId, 'error', 'Revolico devolvió "Reintentar" tras intentar renovar.');
    await goToAccount();
    return;
  }

  // No se puede renovar todavía (tiene que esperar)
  if (!info.hasRenew) {
    if (info.hasNotReady) {
      await finalizeItem(itemId, 'not_ready',
        'Anuncio detectado como no renovable todavía en esta visita.');
      await goToAccount();
      return;
    }

    // No hay botón pero la página cargó → skip
    const reason = info.hasManageActions
      ? 'Página de gestión no confirmó acción renovable; se marca como skip.'
      : 'Sin botón renovable visible; se marca como skip.';
    await finalizeItem(itemId, 'skipped', reason);
    await goToAccount();
    return;
  }

  // ── Renovar ──

  // Verificar autorización fresca antes de la acción
  const freshAuth = await assertRunAuthorization({ allowCached: false, allowReauthorize: true });
  if (!freshAuth) return;

  await updateState({ summary: 'Intentando renovar ' + itemId + '...' });

  // Clic en el botón Renovar
  const clicked = dispatchHumanClick(findRenewButton());
  if (!clicked) {
    await finalizeItem(itemId, 'error', 'No se pudo hacer click al botón de renovar.');
    await goToAccount();
    return;
  }

  // ── Esperar resultado ──
  for (let i = 0; i < timing.postClickLoops; i++) {
    await sleep(timing.postClickSleepMs);
    info = await inspectManagePage();
    if (info.hasSuccess || info.hasUnderstood || info.hasRetry) break;

    // NUEVO: Verificar si el botón Renovar desapareció (indica éxito)
    if (!findRenewButton() && info.hasManageActions) break;
  }

  // ── Evaluar resultado ──

  // Si Revolico devolvió "Reintentar" → la renovación falló
  if (info.hasRetry) {
    await finalizeItem(itemId, 'error',
      'La página mostró "Reintentar"; no se confirmó renovación.');
    await goToAccount();
    return;
  }

  // Si hay mensaje de éxito o botón "Entendido"
  if (info.hasSuccess || info.hasUnderstood) {
    await maybeCloseSuccessModal(timing);

    // Verificar que el botón de renovar realmente desapareció
    const renewStillThere = !!findRenewButton();
    if (!renewStillThere) {
      await finalizeItem(itemId, 'renewed',
        'Renovación confirmada por modal/estado posterior.');
      await goToAccount();
      return;
    }
  }

  // Verificación final: ¿el botón de renovar desapareció?
  const renewButtonGone = !findRenewButton();
  if (renewButtonGone) {
    await finalizeItem(itemId, 'renewed',
      'El botón de renovar desapareció después del click.');
  } else {
    await finalizeItem(itemId, 'skipped',
      'No se pudo confirmar la renovación; el botón sigue visible.');
  }

  await goToAccount();
}

// ═══════════════════════════════════════════════════════════════
//  CONTINUACIÓN DEL PROCESO
// ═══════════════════════════════════════════════════════════════

/**
 * Punto de entrada principal. Decide qué hacer según la página actual.
 */
async function continueRunIfNeeded() {
  const state = await getState();
  if (state.runState !== 'running') return;

  // Verificar autorización
  const auth = await assertRunAuthorization({ allowCached: true, allowReauthorize: true });
  if (!auth) return;

  // Si estamos en /account o /account/ads
  if (isAccountPage()) {
    await handleAccountPage();
    return;
  }

  // Si estamos en una página de gestión /item/{ID}/_/manage
  if (isManagePage()) {
    const currentId = getItemIdFromUrl();
    if (!currentId) {
      await updateState({ summary: 'No se pudo leer el ID actual desde la URL.' });
      return;
    }

    // Si ya fue procesado, ir al siguiente
    if ((state.processedIds || []).includes(currentId)) {
      await goToAccount();
      return;
    }

    await updateState({
      currentItemId: currentId,
      summary: 'Procesando anuncio ' + currentId + '...'
    });
    await attemptRenew(currentId);
    return;
  }

  // En cualquier otra página
  await updateState({
    summary: 'Abre Revolico en /account para iniciar o reanudar.'
  });
}

// ═══════════════════════════════════════════════════════════════
//  BOOT — INICIALIZACIÓN
// ═══════════════════════════════════════════════════════════════

/**
 * Inicializa el content script. Solo se ejecuta una vez por página.
 */
async function boot() {
  // Escuchar mensajes del background/popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    (async () => {
      // PING — verificar que el content script está vivo
      if (msg?.command === 'PING') {
        sendResponse({ ok: true, page: location.href });
        return;
      }

      // START — iniciar el proceso
      if (msg?.command === 'START') {
        const auth = await assertRunAuthorization({ allowCached: false, allowReauthorize: true });
        if (!auth) {
          sendResponse({ ok: false, error: 'La autorización backend no está disponible.' });
          return;
        }
        await updateState({ summary: 'Inicio solicitado desde popup.' });
        await continueRunIfNeeded();
        sendResponse({ ok: true });
        return;
      }

      // RESUME — reanudar
      if (msg?.command === 'RESUME') {
        const auth = await assertRunAuthorization({ allowCached: false, allowReauthorize: true });
        if (!auth) {
          sendResponse({ ok: false, error: 'La autorización backend no está disponible.' });
          return;
        }
        await updateState({ summary: 'Reanudando ejecución...' });
        await continueRunIfNeeded();
        sendResponse({ ok: true });
        return;
      }

      // PAUSE
      if (msg?.command === 'PAUSE') {
        await updateState({ summary: 'Pausado por el usuario.' });
        sendResponse({ ok: true });
        return;
      }

      // STOP
      if (msg?.command === 'STOP') {
        await updateState({
          currentItemId: null,
          summary: 'Detenido por el usuario.'
        });
        sendResponse({ ok: true });
        return;
      }

      sendResponse({ ok: false, error: 'Comando desconocido.' });
    })().catch(err => {
      sendResponse({ ok: false, error: err.message || String(err) });
    });

    return true; // Mantener el canal de mensajes abierto para respuesta async
  });

  // Esperar 1 segundo y luego continuar si hay una ejecución en curso
  await sleep(1000);
  await continueRunIfNeeded();
}

// ═══════════════════════════════════════════════════════════════
//  PUNTO DE ENTRADA — Evitar doble boot
// ═══════════════════════════════════════════════════════════════

if (!window.__revolicoRenewExtensionBooted) {
  window.__revolicoRenewExtensionBooted = true;
  boot();
}