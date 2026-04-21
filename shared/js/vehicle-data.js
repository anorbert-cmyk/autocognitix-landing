/**
 * AutoCognitix - Hungarian Vehicle Market Database
 * Top 25 brands with models, segments, and base MSRP for depreciation
 *
 * CURRENT_YEAR is computed once at script load from the runtime clock.
 * Exposed on VehicleDB so tool pages and tests can share the same reference.
 */
var VDB_CURRENT_YEAR = new Date().getFullYear();

window.VehicleDB = {
  /** Current year reference used by depreciation math. Exposed for testability. */
  CURRENT_YEAR: VDB_CURRENT_YEAR,

  brands: {
    "Suzuki": {
      models: ["Swift", "Vitara", "SX4", "SX4 S-Cross", "Ignis", "Baleno", "Jimny", "Alto", "Splash", "Wagon R+"],
      segment: "budget",
      avgMsrp: 5500000
    },
    "Opel": {
      models: ["Astra", "Corsa", "Insignia", "Mokka", "Crossland", "Grandland", "Zafira", "Meriva", "Vectra", "Combo"],
      segment: "mainstream",
      avgMsrp: 7500000
    },
    "Volkswagen": {
      models: ["Golf", "Passat", "Polo", "Tiguan", "Touran", "T-Roc", "Caddy", "Transporter", "Arteon", "ID.3"],
      segment: "mainstream",
      avgMsrp: 9500000
    },
    "Skoda": {
      models: ["Octavia", "Fabia", "Superb", "Kodiaq", "Karoq", "Kamiq", "Rapid", "Roomster", "Yeti", "Scala"],
      segment: "mainstream",
      avgMsrp: 8000000
    },
    "Ford": {
      models: ["Focus", "Fiesta", "Mondeo", "Kuga", "Puma", "EcoSport", "S-Max", "Galaxy", "C-Max", "Transit Connect"],
      segment: "mainstream",
      avgMsrp: 8000000
    },
    "Toyota": {
      models: ["Corolla", "Yaris", "RAV4", "C-HR", "Auris", "Avensis", "Aygo", "Camry", "Land Cruiser", "Hilux"],
      segment: "mainstream",
      avgMsrp: 9000000
    },
    "BMW": {
      models: ["3-as (E90/F30/G20)", "1-es (F20/F40)", "5-os (F10/G30)", "X1", "X3", "X5", "2-es", "4-es", "7-es", "i3"],
      segment: "premium",
      avgMsrp: 15000000
    },
    "Audi": {
      models: ["A3", "A4", "A6", "Q3", "Q5", "Q7", "A1", "A5", "TT", "Q2"],
      segment: "premium",
      avgMsrp: 14000000
    },
    "Mercedes-Benz": {
      models: ["C-osztaly", "A-osztaly", "E-osztaly", "GLA", "GLC", "GLB", "B-osztaly", "CLA", "S-osztaly", "Vito"],
      segment: "premium",
      avgMsrp: 16000000
    },
    "Renault": {
      models: ["Clio", "Megane", "Scenic", "Captur", "Kadjar", "Kangoo", "Laguna", "Fluence", "Twingo", "Koleos"],
      segment: "mainstream",
      avgMsrp: 6500000
    },
    "Peugeot": {
      models: ["208", "308", "3008", "2008", "508", "5008", "206", "207", "301", "Partner"],
      segment: "mainstream",
      avgMsrp: 7000000
    },
    "Citroen": {
      models: ["C3", "C4", "C5 Aircross", "Berlingo", "C4 Cactus", "C1", "C-Elysee", "DS3", "DS4", "Xsara"],
      segment: "mainstream",
      avgMsrp: 6500000
    },
    "Fiat": {
      models: ["Punto", "500", "Panda", "Tipo", "Bravo", "Doblo", "Stilo", "Linea", "500X", "500L"],
      segment: "budget",
      avgMsrp: 5000000
    },
    "Hyundai": {
      models: ["i30", "i20", "Tucson", "Kona", "i10", "ix35", "Santa Fe", "i40", "Ioniq", "Bayon"],
      segment: "mainstream",
      avgMsrp: 8000000
    },
    "Kia": {
      models: ["Ceed", "Sportage", "Rio", "Picanto", "Niro", "Stonic", "Venga", "Soul", "Sorento", "XCeed"],
      segment: "mainstream",
      avgMsrp: 8000000
    },
    "Dacia": {
      models: ["Duster", "Sandero", "Logan", "Jogger", "Spring", "Dokker", "Lodgy", "Stepway"],
      segment: "budget",
      avgMsrp: 4500000
    },
    "Honda": {
      models: ["Civic", "CR-V", "Jazz", "HR-V", "Accord", "CR-Z", "Insight", "e"],
      segment: "mainstream",
      avgMsrp: 8500000
    },
    "Mazda": {
      models: ["3", "6", "CX-5", "CX-3", "CX-30", "2", "MX-5", "CX-60"],
      segment: "mainstream",
      avgMsrp: 9000000
    },
    "Nissan": {
      models: ["Qashqai", "Juke", "Micra", "X-Trail", "Note", "Leaf", "Navara", "Pulsar"],
      segment: "mainstream",
      avgMsrp: 7500000
    },
    "Seat": {
      models: ["Leon", "Ibiza", "Arona", "Ateca", "Alhambra", "Toledo", "Mii", "Tarraco"],
      segment: "mainstream",
      avgMsrp: 7500000
    },
    "Volvo": {
      models: ["XC60", "V40", "XC90", "V60", "S60", "XC40", "V70", "S80", "C30"],
      segment: "premium",
      avgMsrp: 14000000
    },
    "Mitsubishi": {
      models: ["Outlander", "ASX", "Lancer", "Colt", "Space Star", "L200", "Eclipse Cross", "Pajero"],
      segment: "mainstream",
      avgMsrp: 7500000
    },
    "Chevrolet": {
      models: ["Cruze", "Aveo", "Spark", "Orlando", "Captiva", "Lacetti", "Trax"],
      segment: "budget",
      avgMsrp: 5000000
    },
    "Alfa Romeo": {
      models: ["Giulietta", "MiTo", "159", "Stelvio", "Giulia", "147", "156", "Tonale"],
      segment: "premium",
      avgMsrp: 10000000
    },
    "Lancia": {
      models: ["Ypsilon", "Musa", "Delta"],
      segment: "budget",
      avgMsrp: 4000000
    }
  },

  fuelTypes: [
    { id: "benzin", label: "Benzin", expectedKmPerYear: 13500 },
    { id: "dizel", label: "Dizel", expectedKmPerYear: 20000 },
    { id: "lpg", label: "LPG", expectedKmPerYear: 18000 },
    { id: "hibrid", label: "Hibrid", expectedKmPerYear: 15500 },
    { id: "elektromos", label: "Elektromos", expectedKmPerYear: 12000 }
  ],

  conditions: [
    { id: "kituno", label: "Kituno", multiplier: 1.05 },
    { id: "jo", label: "Jo", multiplier: 1.00 },
    { id: "kozepes", label: "Kozepes", multiplier: 0.85 },
    { id: "rossz", label: "Rossz", multiplier: 0.65 }
  ],

  accidentSeverity: [
    { id: "nem", label: "Nem volt baleset", damageMultiplier: 0 },
    { id: "kozmetikai", label: "Kozmetikai (karcolas, kis horzs.)", damageMultiplier: 0.25 },
    { id: "kozepes", label: "Kozepes (elem csere, nem szerkezeti)", damageMultiplier: 0.50 },
    { id: "sulyos", label: "Sulyos (legzsak, nagy javitas)", damageMultiplier: 0.75 },
    { id: "szerkezeti", label: "Szerkezeti (vazserules)", damageMultiplier: 1.00 }
  ],

  /** Calculate base market value using depreciation model */
  getBaseValue: function(brand, year) {
    var brandData = this.brands[brand];
    if (!brandData) return 3000000;
    var msrp = brandData.avgMsrp;
    var age = Math.max(VDB_CURRENT_YEAR - year, 0);
    if (age === 0) return msrp;
    var d1 = 0.22;
    var d = 0.12;
    var value;
    if (age === 1) {
      value = msrp * (1 - d1);
    } else {
      value = msrp * (1 - d1) * Math.pow(1 - d, age - 1);
    }
    return Math.max(Math.round(value), Math.round(msrp * 0.03));
  },

  /** Get expected annual km for fuel type */
  getExpectedKm: function(fuelType) {
    var ft = this.fuelTypes.find(function(f) { return f.id === fuelType; });
    return ft ? ft.expectedKmPerYear : 15000;
  },

  // ─── Real market price data (loaded async) ───
  _marketPrices: null,

  loadMarketPrices: function() {
    if (this._marketPrices) return Promise.resolve(this._marketPrices);
    var self = this;
    return new Promise(function(resolve) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/shared/data/hungarian-market-prices.json', true);
      xhr.onload = function() {
        if (xhr.status === 200) {
          try {
            self._marketPrices = JSON.parse(xhr.responseText);
            resolve(self._marketPrices);
          } catch(e) { resolve(null); }
        } else { resolve(null); }
      };
      xhr.onerror = function() { resolve(null); };
      xhr.timeout = 5000;
      xhr.ontimeout = function() { resolve(null); };
      xhr.send();
    });
  },

  getMarketPrice: function(brand, model, year) {
    if (!this._marketPrices || !this._marketPrices.brands) return null;
    var brandData = this._marketPrices.brands[brand];
    if (!brandData) return null;
    var modelData = brandData[model];
    if (!modelData) return null;

    // Find exact year or interpolate between nearest years
    var yearStr = String(year);
    if (modelData[yearStr]) return modelData[yearStr];

    // Interpolate: find nearest available years
    var years = Object.keys(modelData).map(Number).sort(function(a, b) { return a - b; });
    if (year <= years[0]) return modelData[String(years[0])];
    if (year >= years[years.length - 1]) return modelData[String(years[years.length - 1])];

    // Find surrounding years and interpolate
    for (var i = 0; i < years.length - 1; i++) {
      if (year > years[i] && year < years[i + 1]) {
        var lower = modelData[String(years[i])];
        var upper = modelData[String(years[i + 1])];
        var ratio = (year - years[i]) / (years[i + 1] - years[i]);
        return {
          min: Math.round(lower.min + (upper.min - lower.min) * ratio),
          avg: Math.round(lower.avg + (upper.avg - lower.avg) * ratio),
          max: Math.round(lower.max + (upper.max - lower.max) * ratio)
        };
      }
    }
    return null;
  },

  /** Enhanced getBaseValue that tries market prices first, falls back to formula */
  getEnhancedValue: function(brand, model, year) {
    var marketPrice = this.getMarketPrice(brand, model, year);
    if (marketPrice) {
      return {
        source: 'market',
        min: marketPrice.min,
        avg: marketPrice.avg,
        max: marketPrice.max
      };
    }
    // Fallback to formula-based estimation
    var formulaValue = this.getBaseValue(brand, year);
    return {
      source: 'formula',
      min: Math.round(formulaValue * 0.85),
      avg: formulaValue,
      max: Math.round(formulaValue * 1.15)
    };
  }
};
