/**
 * @fileoverview AutoCognitix Cookie Consent Manager
 *
 * @description
 * Privacy-first, GDPR Article 7 + ePrivacy Directive 5(3) compliant consent
 * banner. Vanilla JS, IIFE pattern. Zero external dependencies.
 *
 * @design
 * - Default state: NO cookies set, NO tracking scripts loaded.
 * - Consent is granular: Strictly Necessary (always-on) | Analytics | Marketing.
 * - Consent stored in localStorage as JSON (not a cookie), versioned for
 *   schema-driven re-prompting when the policy changes.
 * - Emits a `cookie-consent-updated` CustomEvent so analytics scripts can
 *   gate themselves; the banner itself NEVER loads tracking scripts directly.
 * - i18n: reads document.documentElement.lang at runtime; falls back to 'en'.
 *
 * @api
 * - window.CookieConsent.get()           → {analytics: bool, marketing: bool}|null
 * - window.CookieConsent.getSync()       → {analytics: bool, marketing: bool, _firstVisit?: bool}
 *                                          (never-null snapshot for late-loading scripts
 *                                           that miss the `cookie-consent-updated` event)
 * - window.CookieConsent.onReady(fn)     → fires once when consent is known
 * - window.CookieConsent.reset()         → re-opens the preferences modal
 *
 * @privacy-signals
 * Honors `navigator.globalPrivacyControl === true` (GPC, W3C draft) and
 * `navigator.doNotTrack === '1'` (legacy DNT). When either is asserted on
 * first visit, we auto-record reject-all and skip the banner.
 *
 * @cross-tab
 * Listens for the `storage` event on STORAGE_KEY. If the user accepts or
 * rejects in another tab, this tab hides its banner and refires
 * `cookie-consent-updated` so analytics gates re-evaluate.
 *
 * @compliance
 * - GDPR Article 7 — conditions for consent (specific, informed, freely given,
 *   unambiguous, withdrawable as easily as given).
 * - ePrivacy Directive Article 5(3) — prior consent required for non-essential
 *   storage/access to terminal equipment.
 * - EDPB Guidelines 05/2020 on consent — no pre-ticked boxes, reject-all must
 *   be as easy as accept-all.
 * - WCAG 2.2 AA — focus management, keyboard accessibility, contrast ≥4.5:1,
 *   min touch targets 44×44 px, role="dialog" + aria-modal + focus trap.
 *
 * @consent-schema
 * localStorage key: "ac_cookie_consent"
 * Value: { analytics: bool, marketing: bool, ts: ISO8601, v: number }
 * v=1 — when SCHEMA_VERSION constant is bumped, existing stored consent is
 *         ignored and the banner is re-shown (e.g. after a new cookie category
 *         is added or the policy materially changes).
 *
 * @consent-expiry
 * Consent is valid for 6 months (CONSENT_TTL_MS). After that the banner
 * re-appears. Per EDPB guidance, consent should be refreshed periodically to
 * remain meaningful.
 *
 * @integration
 * Add to every page <head> (before any analytics tags):
 *   <script src="/shared/js/cookie-consent.js" defer></script>
 *
 * Gate analytics in your own script:
 *   document.addEventListener('cookie-consent-updated', function(e) {
 *     if (e.detail.analytics) loadPostHog();   // your function
 *     if (e.detail.marketing) loadMetaPixel(); // your function
 *   });
 *
 * Withdraw / re-open preferences (footer link):
 *   <a href="#" onclick="CookieConsent.reset(); return false;">
 *     Cookie preferences
 *   </a>
 *
 * @version 1.0.0
 * @license MIT
 */

(function (window, document) {
  'use strict';

  /* ─────────────────────────────────────────────────────────────────────────
     CONFIGURATION
  ───────────────────────────────────────────────────────────────────────── */

  /** Bump this integer whenever a new cookie category is added or the
   *  consent schema changes materially. Stored consent with a lower version
   *  will be discarded and the banner will re-appear. */
  var SCHEMA_VERSION = 1;

  /** localStorage key used to persist consent state. */
  var STORAGE_KEY = 'ac_cookie_consent';

  /** Consent TTL: 6 months in ms (EDPB recommends periodic re-consent). */
  var CONSENT_TTL_MS = 6 * 30 * 24 * 60 * 60 * 1000;

  /* ─────────────────────────────────────────────────────────────────────────
     INTERNATIONALISATION
     All user-facing strings live here. Add more locales as needed.
  ───────────────────────────────────────────────────────────────────────── */

  var MESSAGES = {
    en: {
      bannerTitle: 'We value your privacy',
      bannerText:
        'We use cookies to keep the site running (strictly necessary) and, ' +
        'with your consent, to understand how you use it (analytics) and to ' +
        'show you relevant content across the web (marketing). No tracking ' +
        'scripts load until you choose.',
      acceptAll: 'Accept all',
      rejectAll: 'Reject all',
      managePrefs: 'Manage preferences',
      modalTitle: 'Cookie preferences',
      modalIntro:
        'Choose which categories of cookies you allow. You can change your ' +
        'mind at any time via the "Cookie preferences" link in the footer.',
      savePrefs: 'Save preferences',
      closeModal: 'Close',
      necessaryLabel: 'Strictly necessary',
      necessaryDesc:
        'Required for the site to function. Includes session management and ' +
        'CSRF protection. Cannot be disabled.',
      analyticsLabel: 'Analytics',
      analyticsDesc:
        'Helps us understand how visitors interact with the site (e.g. ' +
        'PostHog, Google Analytics). Data is pseudonymised.',
      marketingLabel: 'Marketing',
      marketingDesc:
        'Allows us to measure the effectiveness of advertising campaigns ' +
        '(e.g. Meta Pixel, LinkedIn Insight). Opt-in only.',
      alwaysActive: 'Always active',
      learnMore: 'Cookie policy',
      learnMoreHref: '/en/legal/cookie-policy.html',
    },
    hu: {
      bannerTitle: 'Fontos az adatvédelmed',
      bannerText:
        'Cookie-kat használunk az oldal működéséhez (szükséges) és – ' +
        'hozzájárulásoddal – a látogatási statisztikák elemzéséhez ' +
        '(analitika), illetve releváns tartalmak megjelenítéséhez (marketing). ' +
        'Nyomkövető szkript addig nem töltődik be, amíg nem választasz.',
      acceptAll: 'Mindet elfogadom',
      rejectAll: 'Mindet elutasítom',
      managePrefs: 'Beállítások kezelése',
      modalTitle: 'Cookie-beállítások',
      modalIntro:
        'Válaszd ki, mely cookie-kategóriákat engedélyezed. Döntésedet ' +
        'bármikor megváltoztathatod az oldal láblécében lévő ' +
        '"Cookie-beállítások" linkre kattintva.',
      savePrefs: 'Beállítások mentése',
      closeModal: 'Bezárás',
      necessaryLabel: 'Szükséges',
      necessaryDesc:
        'Az oldal működéséhez elengedhetetlen. Munkamenet-kezelést és CSRF-' +
        'védelmet tartalmaz. Nem tiltható le.',
      analyticsLabel: 'Analitika',
      analyticsDesc:
        'Segít megérteni, hogyan használják a látogatók az oldalt ' +
        '(pl. PostHog, Google Analytics). Az adatok pszeudoanonimizáltak.',
      marketingLabel: 'Marketing',
      marketingDesc:
        'Lehetővé teszi hirdetési kampányaink hatékonyságának mérését ' +
        '(pl. Meta Pixel, LinkedIn Insight). Csak opt-in alapon.',
      alwaysActive: 'Mindig aktív',
      learnMore: 'Cookie-szabályzat',
      learnMoreHref: '/hu/legal/cookie-szabalyzat.html',
    },
  };

  /* ─────────────────────────────────────────────────────────────────────────
     INTERNAL STATE
  ───────────────────────────────────────────────────────────────────────── */

  var _state = null;        // null = not yet determined
  var _readyCallbacks = []; // queued onReady() callbacks
  var _banner = null;
  var _modal = null;
  var _lastFocusedElement = null; // restored when modal closes

  /* ─────────────────────────────────────────────────────────────────────────
     HELPERS
  ───────────────────────────────────────────────────────────────────────── */

  function getLang() {
    var lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
    return MESSAGES[lang] ? lang : 'en';
  }

  function t(key) {
    return MESSAGES[getLang()][key] || key;
  }

  /* Strict, defense-in-depth deserializer.
   * Threat model: an attacker (or a buggy 3rd-party script) writes a forged
   * record to localStorage to flip analytics/marketing to true and bypass the
   * banner. JSON.parse alone gives us no type guarantees — a value of
   * `{ analytics: 1, marketing: "yes", v: 1, ts: "..." }` would coerce to
   * truthy and silently grant consent. Every field is therefore type-checked
   * and any deviation triggers a hard reject + re-prompt.
   * Also guards against clock-skew tampering (future-dated ts) and stale
   * entries past CONSENT_TTL_MS (EDPB-recommended periodic re-consent).
   * Refs: GDPR Art. 7 (unambiguous consent), OWASP Web Storage 2024. */
  function loadConsent() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      // Must be a plain object
      if (typeof parsed !== 'object' || parsed === null) return null;
      // Schema-version pin
      if (parsed.v !== SCHEMA_VERSION) return null;
      // Strict type guards on consent flags — prevents truthy-coercion attacks
      if (typeof parsed.analytics !== 'boolean') return null;
      if (typeof parsed.marketing !== 'boolean') return null;
      // ts is stored as ISO8601 string (existing schema). Validate it parses
      // to a finite, positive epoch and is not future-dated (clock-skew guard).
      if (typeof parsed.ts !== 'string' || !parsed.ts) return null;
      var tsMs = new Date(parsed.ts).getTime();
      if (!isFinite(tsMs) || tsMs <= 0) return null;
      var now = Date.now();
      // Allow 60s of harmless clock skew; anything farther in the future = bogus
      if (tsMs > now + 60 * 1000) return null;
      // TTL: drop stale consent (EDPB periodic re-consent guidance)
      if (now - tsMs > CONSENT_TTL_MS) return null;
      return parsed;
    } catch (e) {
      return null;
    }
  }

  function saveConsent(analytics, marketing) {
    var record = {
      analytics: Boolean(analytics),
      marketing: Boolean(marketing),
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
    } catch (e) {
      // localStorage may be blocked (private browsing etc); degrade gracefully
    }
    return record;
  }

  function emitEvent(state) {
    var evt;
    try {
      evt = new CustomEvent('cookie-consent-updated', { detail: state });
    } catch (e) {
      // IE11 fallback
      evt = document.createEvent('CustomEvent');
      evt.initCustomEvent('cookie-consent-updated', true, true, state);
    }
    document.dispatchEvent(evt);
  }

  function applyConsent(analytics, marketing) {
    _state = saveConsent(analytics, marketing);
    emitEvent({ analytics: _state.analytics, marketing: _state.marketing });
    // Fire queued onReady callbacks
    while (_readyCallbacks.length) {
      try { _readyCallbacks.shift()(_state); } catch (e) {}
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     FOCUS TRAP (WCAG 2.2 SC 2.1.2 — No Keyboard Trap)
     Keeps Tab/Shift+Tab cycling within the modal dialog while it is open.
  ───────────────────────────────────────────────────────────────────────── */

  function getFocusableElements(container) {
    return Array.prototype.slice.call(
      container.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), ' +
        'select:not([disabled]), textarea:not([disabled]), ' +
        '[tabindex]:not([tabindex="-1"])'
      )
    );
  }

  function trapFocus(e, container) {
    var focusable = getFocusableElements(container);
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (e.key === 'Tab' || e.keyCode === 9) {
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    if (e.key === 'Escape' || e.keyCode === 27) {
      closeModal();
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     DOM CREATION HELPERS
  ───────────────────────────────────────────────────────────────────────── */

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'class') {
          node.className = attrs[k];
        } else if (k.indexOf('data-') === 0 || k === 'aria-labelledby' ||
                   k === 'aria-describedby' || k === 'aria-modal' ||
                   k === 'aria-checked' || k === 'role' || k === 'tabindex' ||
                   k === 'for' || k === 'type' || k === 'id' ||
                   k === 'href' || k === 'target' || k === 'rel') {
          node.setAttribute(k, attrs[k]);
        } else {
          node[k] = attrs[k];
        }
      });
    }
    if (typeof children === 'string') {
      node.textContent = children;
    } else if (Array.isArray(children)) {
      children.forEach(function (c) { if (c) node.appendChild(c); });
    }
    return node;
  }

  /* Creates a toggle row for the preferences modal.
   * GDPR requirement: all non-necessary toggles default to OFF (no pre-check).
   * EDPB Guidelines 05/2020, §3.1.1. */
  function createToggleRow(id, label, desc, checked, disabled) {
    var toggleId = 'cc-toggle-' + id;
    var checkbox = el('input', {
      type: 'checkbox',
      id: toggleId,
      class: 'cc-toggle-input',
      tabindex: '0',
    });
    checkbox.checked = Boolean(checked);
    checkbox.disabled = Boolean(disabled);
    if (disabled) {
      checkbox.setAttribute('aria-checked', 'true');
    }

    var knob = el('span', { class: 'cc-toggle-knob', 'aria-hidden': 'true' });
    var track = el('label', {
      class: 'cc-toggle-track' + (disabled ? ' cc-toggle-disabled' : ''),
      for: toggleId,
    }, [knob]);

    var badge = disabled
      ? el('span', { class: 'cc-always-active' }, t('alwaysActive'))
      : track;

    var labelEl = el('div', { class: 'cc-toggle-label' }, label);
    var descEl = el('div', { class: 'cc-toggle-desc' }, desc);
    var textCol = el('div', { class: 'cc-toggle-text' }, [labelEl, descEl]);
    var controlCol = el('div', { class: 'cc-toggle-control' }, [
      disabled ? null : checkbox,
      badge,
    ]);

    return el('div', { class: 'cc-toggle-row', role: 'group', 'aria-labelledby': 'cc-label-' + id }, [
      textCol,
      controlCol,
    ]);
  }

  /* ─────────────────────────────────────────────────────────────────────────
     BANNER
  ───────────────────────────────────────────────────────────────────────── */

  function buildBanner() {
    var titleId = 'cc-banner-title';

    var title = el('p', { class: 'cc-banner-title', id: titleId }, t('bannerTitle'));
    var text = el('p', { class: 'cc-banner-text' }, t('bannerText'));
    var link = el('a', {
      href: t('learnMoreHref'),
      class: 'cc-learn-more',
      rel: 'noopener',
    }, t('learnMore'));
    var textWrap = el('div', { class: 'cc-banner-copy' }, [title, text, link]);

    var btnReject = el('button', {
      class: 'cc-btn cc-btn-outline',
      type: 'button',
      id: 'cc-reject-all',
    }, t('rejectAll'));

    var btnManage = el('button', {
      class: 'cc-btn cc-btn-secondary',
      type: 'button',
      id: 'cc-manage',
    }, t('managePrefs'));

    var btnAccept = el('button', {
      class: 'cc-btn cc-btn-primary',
      type: 'button',
      id: 'cc-accept-all',
    }, t('acceptAll'));

    /* Reject All is given equal visual weight to Accept All per EDPB guidance.
     * Both are the same size; Reject All is rendered first in DOM order so it
     * receives focus first if the user tabs through. */
    var actions = el('div', { class: 'cc-banner-actions' }, [
      btnReject,
      btnManage,
      btnAccept,
    ]);

    var inner = el('div', { class: 'cc-banner-inner' }, [textWrap, actions]);

    var banner = el('div', {
      id: 'cc-banner',
      class: 'cc-banner',
      role: 'region',
      'aria-labelledby': titleId,
    }, [inner]);

    btnAccept.addEventListener('click', function () {
      applyConsent(true, true);
      hideBanner();
    });

    btnReject.addEventListener('click', function () {
      applyConsent(false, false);
      hideBanner();
    });

    btnManage.addEventListener('click', function () {
      openModal(false, false);
    });

    return banner;
  }

  function showBanner() {
    if (_banner) return;
    _banner = buildBanner();
    document.body.appendChild(_banner);
    // Animate in
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        _banner.classList.add('cc-banner--visible');
      });
    });
  }

  function hideBanner() {
    if (!_banner) return;
    _banner.classList.remove('cc-banner--visible');
    _banner.addEventListener('transitionend', function handler() {
      _banner.removeEventListener('transitionend', handler);
      if (_banner && _banner.parentNode) {
        _banner.parentNode.removeChild(_banner);
      }
      _banner = null;
    });
  }

  /* ─────────────────────────────────────────────────────────────────────────
     PREFERENCES MODAL
  ───────────────────────────────────────────────────────────────────────── */

  function buildModal(currentAnalytics, currentMarketing) {
    var modalId = 'cc-modal';
    var titleId = 'cc-modal-title';

    var title = el('h2', { class: 'cc-modal-title', id: titleId }, t('modalTitle'));
    var intro = el('p', { class: 'cc-modal-intro' }, t('modalIntro'));

    var rowNecessary = createToggleRow(
      'necessary',
      t('necessaryLabel'),
      t('necessaryDesc'),
      true,  // always checked
      true   // disabled — cannot be turned off (ePrivacy Directive 5(3) exception)
    );

    var rowAnalytics = createToggleRow(
      'analytics',
      t('analyticsLabel'),
      t('analyticsDesc'),
      currentAnalytics,  // defaults to false (GDPR Art. 7 — no pre-tick)
      false
    );

    var rowMarketing = createToggleRow(
      'marketing',
      t('marketingLabel'),
      t('marketingDesc'),
      currentMarketing,  // defaults to false
      false
    );

    var togglesWrap = el('div', { class: 'cc-toggles' }, [
      rowNecessary,
      rowAnalytics,
      rowMarketing,
    ]);

    var btnSave = el('button', {
      class: 'cc-btn cc-btn-primary',
      type: 'button',
      id: 'cc-save-prefs',
    }, t('savePrefs'));

    var btnClose = el('button', {
      class: 'cc-modal-close',
      type: 'button',
      'aria-label': t('closeModal'),
      id: 'cc-modal-close',
    }, '\u00D7'); // ×

    var footer = el('div', { class: 'cc-modal-footer' }, [btnSave]);

    var dialog = el('div', {
      class: 'cc-modal-dialog',
      role: 'dialog',
      'aria-modal': 'true',
      'aria-labelledby': titleId,
      id: modalId,
      tabindex: '-1',
    }, [btnClose, title, intro, togglesWrap, footer]);

    var overlay = el('div', {
      class: 'cc-overlay',
      id: 'cc-overlay',
      role: 'presentation',
    });

    var wrap = el('div', { class: 'cc-modal-wrap', id: 'cc-modal-wrap' }, [overlay, dialog]);

    btnSave.addEventListener('click', function () {
      var analytics = document.getElementById('cc-toggle-analytics');
      var marketing = document.getElementById('cc-toggle-marketing');
      applyConsent(
        analytics ? analytics.checked : false,
        marketing ? marketing.checked : false
      );
      closeModal();
      hideBanner();
    });

    btnClose.addEventListener('click', closeModal);

    overlay.addEventListener('click', closeModal);

    // Keyboard handling: ESC + focus trap
    wrap._keyHandler = function (e) { trapFocus(e, dialog); };
    document.addEventListener('keydown', wrap._keyHandler);

    return wrap;
  }

  function openModal(currentAnalytics, currentMarketing) {
    if (_modal) return;
    _lastFocusedElement = document.activeElement;

    // If we have stored state, pre-fill toggles from stored state
    var stored = loadConsent();
    var a = (stored !== null) ? stored.analytics : Boolean(currentAnalytics);
    var m = (stored !== null) ? stored.marketing : Boolean(currentMarketing);

    _modal = buildModal(a, m);
    document.body.appendChild(_modal);
    document.body.style.overflow = 'hidden'; // prevent background scroll

    // Animate in
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        _modal.classList.add('cc-modal-wrap--visible');
        // Move focus to dialog (WCAG SC 2.4.3 — Focus Order)
        var dialog = document.getElementById('cc-modal');
        if (dialog) dialog.focus();
      });
    });
  }

  function closeModal() {
    if (!_modal) return;
    document.removeEventListener('keydown', _modal._keyHandler);
    _modal.classList.remove('cc-modal-wrap--visible');
    document.body.style.overflow = '';

    _modal.addEventListener('transitionend', function handler() {
      _modal.removeEventListener('transitionend', handler);
      if (_modal && _modal.parentNode) {
        _modal.parentNode.removeChild(_modal);
      }
      _modal = null;
    });

    // Restore focus to element that triggered the modal (WCAG SC 2.4.3)
    if (_lastFocusedElement && typeof _lastFocusedElement.focus === 'function') {
      _lastFocusedElement.focus();
      _lastFocusedElement = null;
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     GLOBAL PRIVACY CONTROL (GPC) + DO NOT TRACK (DNT)
     Honoring GPC is best-practice for EU users (CCPA-binding in California
     since 2021; W3C TPWG draft). DNT is the older signal. If either is
     asserted, we auto-record a "reject all" decision so the user is not
     forced to interact with a banner that can only confirm their stated
     preference. Per GDPR Art. 25 (privacy by design/default), this is the
     safest default.
     Refs: https://globalprivacycontrol.org/, EDPB Guidelines 05/2020 §3.1.2
  ───────────────────────────────────────────────────────────────────────── */
  function shouldRespectPrivacySignal() {
    try {
      if (navigator.globalPrivacyControl === true) return true;
      // DNT: '1' = opt out. Some browsers expose on window; navigator is canonical.
      var dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
      if (dnt === '1' || dnt === 'yes') return true;
      return false;
    } catch (e) {
      return false;
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     CROSS-TAB SYNC
     If the user accepts/rejects in tab A, hide the banner in tab B. Without
     this, the banner persists in background tabs and the user must click
     twice. The `storage` event only fires in OTHER tabs (never the originator),
     so no infinite loop possible.
  ───────────────────────────────────────────────────────────────────────── */
  function onStorageEvent(e) {
    if (!e || e.key !== STORAGE_KEY) return;
    // newValue === null means another tab cleared/reset consent → re-prompt.
    if (e.newValue === null) {
      _state = null;
      // If a banner is already visible, leave it; otherwise show one.
      if (!_banner) showBanner();
      return;
    }
    var consent = loadConsent();
    if (!consent) return; // Tampered/invalid write — ignore, don't disrupt UI
    _state = consent;
    hideBanner();
    if (_modal) closeModal();
    emitEvent({ analytics: consent.analytics, marketing: consent.marketing });
    while (_readyCallbacks.length) {
      try { _readyCallbacks.shift()(_state); } catch (err) {}
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────
     INIT
  ───────────────────────────────────────────────────────────────────────── */

  function init() {
    // Wire cross-tab sync once, before any state work
    try { window.addEventListener('storage', onStorageEvent); } catch (e) {}

    var stored = loadConsent();

    if (stored !== null) {
      // Consent already given and still valid — restore state and fire events
      _state = stored;
      emitEvent({ analytics: _state.analytics, marketing: _state.marketing });
      while (_readyCallbacks.length) {
        try { _readyCallbacks.shift()(_state); } catch (e) {}
      }
      return;
    }

    // No stored consent: respect GPC/DNT before showing a banner.
    if (shouldRespectPrivacySignal()) {
      // User has expressed a global "do not track" — record a reject-all
      // decision and skip the banner entirely. They can still re-open
      // preferences via CookieConsent.reset() to opt INTO analytics.
      applyConsent(false, false);
      return;
    }

    // Privacy-by-default: show banner. onReady fires only after user choice.
    showBanner();
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* ─────────────────────────────────────────────────────────────────────────
     PUBLIC API
     Exposed as window.CookieConsent (singular surface, no other globals)
  ───────────────────────────────────────────────────────────────────────── */

  /**
   * @namespace CookieConsent
   */
  window.CookieConsent = {
    /**
     * Returns the current consent state synchronously.
     * Returns null if the user has not yet made a choice.
     * @returns {{analytics: boolean, marketing: boolean}|null}
     */
    get: function () {
      if (_state === null) return null;
      return { analytics: _state.analytics, marketing: _state.marketing };
    },

    /**
     * Synchronous, never-null snapshot of the current consent state.
     *
     * Late-loading scripts (lazy-loaded analytics, deferred bundles, code that
     * runs *after* the `cookie-consent-updated` event has already fired) miss
     * the one-shot event and would otherwise see no consent signal. Use this
     * helper to read the state on demand without waiting for events.
     *
     * If no decision has been recorded yet, returns a privacy-safe default
     * (`{analytics: false, marketing: false, _firstVisit: true}`). The
     * `_firstVisit` flag lets callers distinguish "no answer yet" from an
     * explicit "rejected" decision; never load tracking on first-visit.
     *
     * @returns {{analytics: boolean, marketing: boolean, _firstVisit?: boolean}}
     */
    getSync: function () {
      var s = loadConsent();
      if (s) return { analytics: s.analytics, marketing: s.marketing };
      return { analytics: false, marketing: false, _firstVisit: true };
    },

    /**
     * Registers a callback that fires once with the consent state.
     * If consent is already known, the callback fires immediately (async).
     * Use this instead of listening for `cookie-consent-updated` when you
     * need exactly-once behaviour.
     * @param {function({analytics: boolean, marketing: boolean}): void} fn
     */
    onReady: function (fn) {
      if (typeof fn !== 'function') return;
      if (_state !== null) {
        // Already resolved — fire on next tick to keep calling code async
        var s = _state;
        setTimeout(function () { fn({ analytics: s.analytics, marketing: s.marketing }); }, 0);
      } else {
        _readyCallbacks.push(fn);
      }
    },

    /**
     * Re-opens the preferences modal. Use for a "Cookie preferences" footer
     * link or "Change my choices" UI. This is required by GDPR Art. 7(3):
     * withdrawal must be as easy as giving consent.
     */
    reset: function () {
      openModal(false, false);
    },
  };

}(window, document));
