/**
 * AutoCognitix - Shared Tool Utilities
 * Form handling, result rendering, animations
 */
var ToolCommon = {

  /** Populate a <select> from an array of {id, label} or strings */
  populateSelect: function(selectEl, options, placeholder) {
    selectEl.innerHTML = '';
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
    this.populateSelect(brandEl, brands, 'Valassz markat...');

    brandEl.addEventListener('change', function() {
      var brand = brandEl.value;
      var data = VehicleDB.brands[brand];
      if (data) {
        ToolCommon.populateSelect(modelEl, data.models, 'Valassz modellt...');
        modelEl.disabled = false;
      } else {
        modelEl.innerHTML = '<option value="">Elobb valassz markat</option>';
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
    this.populateSelect(el, opts, 'Evjarat...');
  },

  /** Format number as Hungarian HUF */
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
    if (!code || code.length === 0) return { valid: false, warning: 'Üres hibakód' };
    var upper = code.toUpperCase().trim();
    if (!pattern.test(upper)) return { valid: false, warning: 'Érvénytelen formátum: ' + code + '. Helyes: P0420, C0035' };
    return { valid: true, code: upper };
  },

  /** Odometer anomaly detection */
  detectOdometerAnomaly: function(km, year) {
    var currentYear = new Date().getFullYear();
    var age = Math.max(currentYear - year, 0);
    if (age === 0) return null;
    var kmPerYear = km / age;
    if (kmPerYear > 40000) return { level: 'high', message: 'Szokatlanul magas futás (' + Math.round(kmPerYear) + ' km/év). Ellenőrizd az adatot!' };
    if (kmPerYear > 25000) return { level: 'medium', message: 'Átlag feletti futás (' + Math.round(kmPerYear) + ' km/év).' };
    if (km === 0 && age > 2) return { level: 'high', message: '0 km egy ' + age + ' éves autón szokatlan.' };
    if (kmPerYear < 1000 && age > 3) return { level: 'medium', message: 'Szokatlanul alacsony futás (' + Math.round(kmPerYear) + ' km/év). Lehetséges óraállás visszatekerés.' };
    return null;
  },

  /** Numeric range validation */
  validateNumericRange: function(value, min, max, fieldName) {
    var num = parseFloat(value);
    if (isNaN(num)) return { valid: false, message: fieldName + ' érvénytelen szám.' };
    if (num < min) return { valid: false, message: fieldName + ' nem lehet kisebb mint ' + min + '.' };
    if (max !== null && num > max) return { valid: false, message: fieldName + ' nem lehet nagyobb mint ' + max + '.' };
    return { valid: true, value: num };
  },

  // --- DTC Database (loaded async from static JSON) ---

  _dtcDB: null,

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
            if (data._meta) { resolve(null); return; } // fallback stub
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

  getDTCInfo: function(code) {
    if (!this._dtcDB) return null;
    return this._dtcDB[code.toUpperCase()] || null;
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

    console.log('[ToolCommon selfTest] ' + pass + ' passed, ' + fail + ' failed');
  }
};

// Init dropdown on page load
document.addEventListener('DOMContentLoaded', function() {
  ToolCommon.initNavDropdown();
});

// Run self-tests on load (development only)
ToolCommon.selfTest();
