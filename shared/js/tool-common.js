/**
 * AutoCognitix - Shared Tool Utilities
 * Form handling, result rendering, animations, input validation, DTC DB loader.
 *
 * i18n: all user-facing strings live in the MESSAGES table below.
 * Locale is auto-detected from <html lang="..">; falls back to HU.
 *
 * Back-compat: every public function on ToolCommon.* from v1.0 is preserved.
 */

/* ─── Locale + i18n table ───────────────────────────────────────────── */
var LANG = (function() {
  try {
    var l = (document.documentElement.lang || 'hu').toLowerCase();
    return l.indexOf('en') === 0 ? 'en' : 'hu';
  } catch(e) { return 'hu'; }
})();

var MESSAGES = {
  hu: {
    // Select placeholders
    selectBrand: 'Válassz márkát...',
    selectModel: 'Válassz modellt...',
    chooseBrandFirst: 'Előbb válassz márkát',
    yearPlaceholder: 'Évjárat...',

    // DTC validation
    emptyDTC: 'Üres hibakód',
    invalidDTCFormat: 'Érvénytelen formátum: {code}. Helyes: P0420, C0035',

    // Odometer anomaly
    unusuallyHighMileage: 'Szokatlanul magas futás ({kmPerYear} km/év). Ellenőrizd az adatot!',
    aboveAverageMileage: 'Átlag feletti futás ({kmPerYear} km/év).',
    zeroKmOldCarUnusual: '0 km egy {age} éves autón szokatlan.',
    unusuallyLowMileage: 'Szokatlanul alacsony futás ({kmPerYear} km/év). Lehetséges óraállás visszatekerés.',

    // Numeric range
    invalidNumber: '{field} érvénytelen szám.',
    tooSmall: '{field} nem lehet kisebb mint {min}.',
    tooLarge: '{field} nem lehet nagyobb mint {max}.',

    // Currency / units
    currencyUnit: ' Ft',

    // DTC DB fallback marker (consumed by renderDTCInfo)
    enFallbackPrefix: '[EN] '
  },
  en: {
    selectBrand: 'Select brand...',
    selectModel: 'Select model...',
    chooseBrandFirst: 'Please select brand first',
    yearPlaceholder: 'Year...',

    emptyDTC: 'Empty DTC code',
    invalidDTCFormat: 'Invalid format: {code}. Correct: P0420, C0035',

    unusuallyHighMileage: 'Unusually high mileage ({kmPerYear} km/year). Please verify!',
    aboveAverageMileage: 'Above-average mileage ({kmPerYear} km/year).',
    zeroKmOldCarUnusual: '0 km on a {age}-year-old car is unusual.',
    unusuallyLowMileage: 'Unusually low mileage ({kmPerYear} km/year). Possible odometer rollback.',

    invalidNumber: '{field} is not a valid number.',
    tooSmall: '{field} cannot be smaller than {min}.',
    tooLarge: '{field} cannot be larger than {max}.',

    currencyUnit: ' HUF',

    enFallbackPrefix: '[EN] '
  }
};

/** i18n lookup with {placeholder} interpolation. */
function t(key, vars) {
  var tbl = MESSAGES[LANG] || MESSAGES.hu;
  var tpl = tbl[key];
  if (tpl === undefined) tpl = MESSAGES.hu[key];
  if (tpl === undefined) return key;
  if (!vars) return tpl;
  return tpl.replace(/\{(\w+)\}/g, function(_, k) {
    return vars[k] !== undefined ? String(vars[k]) : '{' + k + '}';
  });
}

/* ─── ToolCommon public API ─────────────────────────────────────────── */
var ToolCommon = {

  /** Current UI locale ('hu' | 'en'). Exposed for callers that branch on it. */
  LANG: LANG,

  /** Translate a key. Exposed so page inline scripts can reuse the table. */
  t: t,

  /** Populate a <select> from an array of {id, label} or strings */
  populateSelect: function(selectEl, options, placeholder) {
    // Clear safely without innerHTML.
    while (selectEl.firstChild) selectEl.removeChild(selectEl.firstChild);
    if (placeholder) {
      var ph = document.createElement('option');
      ph.value = '';
      ph.textContent = placeholder;
      ph.disabled = true;
      ph.selected = true;
      selectEl.appendChild(ph);
    }
    options.forEach(function(opt) {
      var o = document.createElement('option');
      if (typeof opt === 'string') {
        o.value = opt;
        o.textContent = opt;
      } else {
        o.value = opt.id || opt.value;
        o.textContent = opt.label || opt.name;
      }
      selectEl.appendChild(o);
    });
  },

  /** Setup brand -> model cascade */
  setupBrandModelCascade: function(brandSelectId, modelSelectId) {
    var brandEl = document.getElementById(brandSelectId);
    var modelEl = document.getElementById(modelSelectId);
    if (!brandEl || !modelEl || !window.VehicleDB) return;

    var brands = Object.keys(VehicleDB.brands).sort();
    this.populateSelect(brandEl, brands, t('selectBrand'));

    brandEl.addEventListener('change', function() {
      var brand = brandEl.value;
      var data = VehicleDB.brands[brand];
      if (data) {
        ToolCommon.populateSelect(modelEl, data.models, t('selectModel'));
        modelEl.disabled = false;
      } else {
        // Clear and rebuild with a single disabled placeholder.
        while (modelEl.firstChild) modelEl.removeChild(modelEl.firstChild);
        var ph = document.createElement('option');
        ph.value = '';
        ph.textContent = t('chooseBrandFirst');
        ph.disabled = true;
        ph.selected = true;
        modelEl.appendChild(ph);
        modelEl.disabled = true;
      }
    });
  },

  /** Populate year select (descending) */
  populateYearSelect: function(selectId, minYear, maxYear) {
    var el = document.getElementById(selectId);
    if (!el) return;
    var opts = [];
    for (var y = maxYear; y >= minYear; y--) {
      opts.push({ id: String(y), label: String(y) });
    }
    this.populateSelect(el, opts, t('yearPlaceholder'));
  },

  /** Format number as HUF (currency stays Ft — HUF is the underlying currency in both locales). */
  formatHUF: function(num) {
    if (num === null || num === undefined) return '-';
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' Ft';
  },

  /** Format percentage */
  formatPct: function(num) {
    return (num >= 0 ? '+' : '') + (num * 100).toFixed(1) + '%';
  },

  /** Show/hide element with animation */
  showResult: function(id) {
    var el = document.getElementById(id);
    if (el) {
      el.style.display = 'block';
      el.offsetHeight; // force reflow
      el.classList.add('visible');
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  hideResult: function(id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.remove('visible');
      el.style.display = 'none';
    }
  },

  /** Animate a number counting up */
  animateNumber: function(el, target, duration, formatter) {
    if (!el) return;
    var start = 0;
    var startTime = null;
    formatter = formatter || function(v) { return Math.round(v); };

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      var current = start + (target - start) * eased;
      el.textContent = formatter(current);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }
    requestAnimationFrame(step);
  },

  /** Get verdict color class */
  getVerdictClass: function(score, thresholds) {
    if (score >= thresholds.good) return 'verdict-good';
    if (score >= thresholds.warning) return 'verdict-warning';
    return 'verdict-bad';
  },

  /** Simple form validation */
  validateRequired: function(fields) {
    var valid = true;
    fields.forEach(function(f) {
      var el = document.getElementById(f.id);
      if (!el) return;
      var wrapper = el.closest('.form-group');
      if (!el.value || el.value === '') {
        if (wrapper) wrapper.classList.add('error');
        valid = false;
      } else {
        if (wrapper) wrapper.classList.remove('error');
      }
    });
    return valid;
  },

  /** Nav dropdown toggle */
  initNavDropdown: function() {
    document.querySelectorAll('.nav-dropdown-trigger').forEach(function(trigger) {
      trigger.addEventListener('click', function(e) {
        if (window.innerWidth <= 991) {
          e.preventDefault();
          var dropdown = trigger.closest('.nav-dropdown');
          if (dropdown) dropdown.classList.toggle('open');
        }
      });
    });
    // Close on click outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.nav-dropdown')) {
        document.querySelectorAll('.nav-dropdown.open').forEach(function(d) {
          d.classList.remove('open');
        });
      }
    });
  },

  // --- Input Validation Functions ---

  /** DTC format validation */
  validateDTC: function(code) {
    var pattern = /^[PBCU]\d{4}$/i;
    if (!code || code.length === 0) return { valid: false, warning: t('emptyDTC') };
    var upper = code.toUpperCase().trim();
    if (!pattern.test(upper)) return { valid: false, warning: t('invalidDTCFormat', { code: code }) };
    return { valid: true, code: upper };
  },

  /** Odometer anomaly detection */
  detectOdometerAnomaly: function(km, year) {
    var currentYear = new Date().getFullYear();
    var age = Math.max(currentYear - year, 0);
    if (age === 0) return null;
    var kmPerYear = km / age;
    if (kmPerYear > 40000) return { level: 'high', message: t('unusuallyHighMileage', { kmPerYear: Math.round(kmPerYear) }) };
    if (kmPerYear > 25000) return { level: 'medium', message: t('aboveAverageMileage', { kmPerYear: Math.round(kmPerYear) }) };
    if (km === 0 && age > 2) return { level: 'high', message: t('zeroKmOldCarUnusual', { age: age }) };
    if (kmPerYear < 1000 && age > 3) return { level: 'medium', message: t('unusuallyLowMileage', { kmPerYear: Math.round(kmPerYear) }) };
    return null;
  },

  /** Numeric range validation */
  validateNumericRange: function(value, min, max, fieldName) {
    var num = parseFloat(value);
    if (isNaN(num)) return { valid: false, message: t('invalidNumber', { field: fieldName }) };
    if (num < min) return { valid: false, message: t('tooSmall', { field: fieldName, min: min }) };
    if (max !== null && num > max) return { valid: false, message: t('tooLarge', { field: fieldName, max: max }) };
    return { valid: true, value: num };
  },

  // --- DTC Database (loaded async from static JSON) ---

  _dtcDB: null,
  _dtcLazyAttached: false,

  /**
   * Eager loader — kept for back-compat.
   * Prefer lazyLoadDTCDatabase() which defers the 641 KB XHR until the user
   * focuses a DTC input or the browser goes idle.
   */
  loadDTCDatabase: function() {
    if (this._dtcDB) return Promise.resolve(this._dtcDB);
    var self = this;
    return new Promise(function(resolve) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/shared/data/dtc-database.json', true);
      xhr.onload = function() {
        if (xhr.status === 200) {
          try {
            var data = JSON.parse(xhr.responseText);
            if (data._meta && data._meta.source === 'fallback') { resolve(null); return; } // fallback stub
            self._dtcDB = data;
            resolve(data);
          } catch(e) { resolve(null); }
        } else { resolve(null); }
      };
      xhr.onerror = function() { resolve(null); };
      xhr.timeout = 5000;
      xhr.ontimeout = function() { resolve(null); };
      xhr.send();
    });
  },

  /**
   * Lazy DTC preloader — attach this once on DOMContentLoaded.
   * Triggers on first interaction with any DTC input on the page; if no DTC
   * input exists we still preload during idle time (~5s after load).
   * Safety-net timer fires after 10s even if the user never touches the input.
   * Idempotent: safe to call multiple times.
   *
   * @param {string} [selector] Optional CSS selector overriding the default.
   */
  lazyLoadDTCDatabase: function(selector) {
    if (this._dtcDB || this._dtcLazyAttached) return;
    this._dtcLazyAttached = true;
    var self = this;
    var sel = selector || 'input[name="dtc"], input[id*="dtc"], input[id*="Dtc"], input[data-dtc]';
    var inputs = document.querySelectorAll(sel);
    function trigger() { self.loadDTCDatabase(); }

    if (inputs.length === 0) {
      if ('requestIdleCallback' in window) {
        requestIdleCallback(trigger, { timeout: 5000 });
      } else {
        setTimeout(trigger, 3000);
      }
      return;
    }

    inputs.forEach(function(el) {
      el.addEventListener('focus', trigger, { once: true, passive: true });
      el.addEventListener('input', trigger, { once: true, passive: true });
    });

    // Safety net: preload even if the user never touches the input.
    if ('requestIdleCallback' in window) {
      requestIdleCallback(trigger, { timeout: 10000 });
    } else {
      setTimeout(trigger, 8000);
    }
  },

  /**
   * Return raw entry {en, hu, category, generic, severity} or null.
   * hu may be null for codes not yet translated (see _meta.hu_coverage_percent).
   */
  getDTCInfo: function(code) {
    if (!this._dtcDB) return null;
    return this._dtcDB[code.toUpperCase()] || null;
  },

  /**
   * Locale-aware description renderer.
   * HU locale: returns entry.hu when present; else "[EN] " + entry.en.
   * EN locale: returns entry.en.
   * Returns null when the code is not in the DB.
   *
   * Implements the data-engineer fallback contract from
   * shared/data/dtc-database.json _meta.hu_fallback_marker.
   */
  renderDTCInfo: function(code) {
    var entry = this.getDTCInfo(code);
    if (!entry) return null;
    if (LANG === 'hu') {
      if (entry.hu) return entry.hu;
      if (entry.en) return t('enFallbackPrefix') + entry.en;
      return null;
    }
    return entry.en || null;
  },

  // --- Utility Functions ---

  /** Escape HTML to prevent XSS */
  escapeHTML: function(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  // --- Metamorphic Self-Test (development only) ---

  /** Run self-tests to verify core functions */
  selfTest: function() {
    if (typeof console === 'undefined') return;
    var pass = 0, fail = 0;

    // MR1: Older car should be worth less
    if (typeof window.VehicleDB !== 'undefined') {
      var v1 = window.VehicleDB.getBaseValue('Volkswagen', 2020);
      var v2 = window.VehicleDB.getBaseValue('Volkswagen', 2019);
      if (v1 > v2) { pass++; } else { console.warn('[MR1 FAIL] 2020 VW (' + v1 + ') should be > 2019 VW (' + v2 + ')'); fail++; }

      var v3 = window.VehicleDB.getBaseValue('Volkswagen', 2015);
      if (v2 > v3) { pass++; } else { console.warn('[MR1 FAIL] 2019 VW (' + v2 + ') should be > 2015 VW (' + v3 + ')'); fail++; }
    }

    // Validation self-tests
    var dtc1 = ToolCommon.validateDTC('P0420');
    if (dtc1.valid) { pass++; } else { console.warn('[DTC FAIL] P0420 should be valid'); fail++; }

    var dtc2 = ToolCommon.validateDTC('hello');
    if (!dtc2.valid) { pass++; } else { console.warn('[DTC FAIL] "hello" should be invalid'); fail++; }

    var dtc3 = ToolCommon.validateDTC('b0100');
    if (dtc3.valid && dtc3.code === 'B0100') { pass++; } else { console.warn('[DTC FAIL] "b0100" should normalize to B0100'); fail++; }

    var odo1 = ToolCommon.detectOdometerAnomaly(500000, 2020);
    if (odo1 && odo1.level === 'high') { pass++; } else { console.warn('[ODO FAIL] 500k km on 2020 should be high anomaly'); fail++; }

    console.log('[ToolCommon selfTest] lang=' + LANG + ' — ' + pass + ' passed, ' + fail + ' failed');
  }
};

// Init dropdown on page load
document.addEventListener('DOMContentLoaded', function() {
  ToolCommon.initNavDropdown();
});

// Run self-tests only in development (localhost or window.__DEV__).
// Prevents console noise for real users and keeps the test harness from
// tripping any analytics that watch for unexpected console.* output.
(function gatedSelfTest() {
  try {
    var host = location.hostname;
    var isDev = host === 'localhost'
      || host === '127.0.0.1'
      || host === '::1'
      || (typeof window.__DEV__ !== 'undefined' && window.__DEV__);
    if (isDev) ToolCommon.selfTest();
  } catch(e) { /* non-browser env */ }
})();
