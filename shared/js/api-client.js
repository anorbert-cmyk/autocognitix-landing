/**
 * AutoCognitix Shared API Client
 * Progressive enhancement layer — calls backend API to enrich client-side calculations.
 * @version 1.0
 */
window.ApiClient = (function() {
  var PROXY_BASE = '/proxy';
  var TIMEOUT = 10000; // 10 seconds

  function post(path, data) {
    return new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', PROXY_BASE + path, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.timeout = TIMEOUT;
      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); }
          catch(e) { reject(new Error('Invalid JSON response')); }
        } else {
          reject(new Error('API error: ' + xhr.status));
        }
      };
      xhr.onerror = function() { reject(new Error('Network error')); };
      xhr.ontimeout = function() { reject(new Error('Request timeout')); };
      xhr.send(JSON.stringify(data));
    });
  }

  function get(path, params) {
    return new Promise(function(resolve, reject) {
      var query = Object.keys(params || {}).map(function(k) {
        return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
      }).join('&');
      var url = PROXY_BASE + path + (query ? '?' + query : '');
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.timeout = TIMEOUT;
      xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); }
          catch(e) { reject(new Error('Invalid JSON response')); }
        } else {
          reject(new Error('API error: ' + xhr.status));
        }
      };
      xhr.onerror = function() { reject(new Error('Network error')); };
      xhr.ontimeout = function() { reject(new Error('Request timeout')); };
      xhr.send();
    });
  }

  return {
    // Calculator
    evaluateRepair: function(data) {
      return post('/calculator/evaluate', {
        vehicle_make: data.brand,
        vehicle_model: data.model,
        vehicle_year: data.year,
        mileage_km: data.mileage,
        condition: data.condition, // excellent/good/fair/poor
        repair_cost_huf: data.repairCost || null,
        fuel_type: data.fuel
      });
    },
    // Inspection
    evaluateInspection: function(data) {
      return post('/inspection/evaluate', {
        vehicle_make: data.brand,
        vehicle_model: data.model,
        vehicle_year: data.year,
        mileage_km: data.mileage,
        dtc_codes: data.dtcCodes,
        symptoms: data.symptoms || ''
      });
    },
    // DTC lookup
    searchDTC: function(code) {
      return get('/dtc/' + code.toUpperCase());
    },
    // Services
    searchServices: function(params) {
      return get('/services/search', params);
    }
  };
})();
