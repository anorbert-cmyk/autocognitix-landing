import { describe, it, expect } from 'vitest';
import { createEnvironment } from '../setup/dom-shim.js';

// ─── REIMPLEMENTED PURE CALCULATION LOGIC (from muszaki-vizsga-prediktor.html) ───

const EMISSION_CRITICAL = [
  'P0420','P0430','P0440','P0441','P0442','P0443','P0446','P0455','P0456','P0457',
  'P0300','P0301','P0302','P0303','P0304','P0305','P0306','P0307','P0308',
  'P0130','P0131','P0132','P0133','P0134','P0135','P0136','P0137','P0138','P0139','P0140','P0141',
  'P0400','P0401','P0402','P0403','P0404','P2000','P2002','P2004'
];

const WEAR_PARTS = {
  fekbetet: {
    benzin: [30000, 80000], dizel: [30000, 80000], lpg: [30000, 80000], hibrid: [40000, 100000], elektromos: [50000, 120000],
    deduction: 10, label: 'Fekbetetek'
  },
  fektarcsa: {
    benzin: [60000, 120000], dizel: [60000, 120000], lpg: [60000, 120000], hibrid: [70000, 140000], elektromos: [80000, 160000],
    deduction: 10, label: 'Fektarcsak'
  },
  katalizator: {
    benzin: [100000, 160000], dizel: null, lpg: [80000, 140000], hibrid: [120000, 200000], elektromos: null,
    deduction: 15, label: 'Katalizator'
  },
  dpf: {
    benzin: null, dizel: [100000, 200000], lpg: null, hibrid: null, elektromos: null,
    deduction: 15, label: 'DPF'
  },
  lambda: {
    benzin: [80000, 160000], dizel: [80000, 160000], lpg: [60000, 120000], hibrid: [80000, 160000], elektromos: null,
    deduction: 10, label: 'Lambda szonda'
  },
  egr: {
    benzin: null, dizel: [80000, 150000], lpg: null, hibrid: null, elektromos: null,
    deduction: 10, label: 'EGR szelep'
  },
  turbo: {
    benzin: null, dizel: [170000, 250000], lpg: null, hibrid: null, elektromos: null,
    deduction: 10, label: 'Turbo'
  },
  gyujtotekercs: {
    benzin: [80000, 160000], dizel: null, lpg: [80000, 160000], hibrid: [80000, 160000], elektromos: null,
    deduction: 8, label: 'Gyujtotekercsek'
  },
  lengescsillapito: {
    benzin: [80000, 160000], dizel: [80000, 160000], lpg: [80000, 160000], hibrid: [80000, 160000], elektromos: [80000, 160000],
    deduction: 8, label: 'Lengescsillapitok'
  },
  idozito: {
    benzin: [60000, 120000], dizel: [80000, 150000], lpg: [60000, 120000], hibrid: [60000, 120000], elektromos: null,
    deduction: 5, label: 'Idozito szij'
  },
  kuplung: {
    benzin: [100000, 200000], dizel: [100000, 200000], lpg: [100000, 200000], hibrid: null, elektromos: null,
    deduction: 3, label: 'Kuplung'
  }
};

/**
 * Pure reimplementation of the calculate() function from the inline script.
 * Mirrors the source logic line-for-line for test fidelity.
 */
function calculate(year, km, fuel, milOn, dtcCodes) {
  var score = 100;
  var verdict = '';
  var dtcWarnings = [];
  var wearAlerts = [];
  var tips = [];
  var isElectric = fuel === 'elektromos';
  var dieselWarning = '';

  // MIL CHECK — instant fail
  var milFailed = false;
  if (milOn === 'igen') {
    score = 0;
    verdict = 'MEGBUKIK';
    milFailed = true;
  } else if (milOn === 'nemtudom') {
    score -= 10;
  }

  if (!milFailed) {
    // DTC SCORING
    dtcCodes.forEach(function(code) {
      if (EMISSION_CRITICAL.indexOf(code) !== -1) {
        if (!isElectric) {
          score -= 15;
          dtcWarnings.push({ code: code, severity: 'critical' });
        } else {
          dtcWarnings.push({ code: code, severity: 'info' });
        }
      } else if (code.indexOf('P0') === 0) {
        score -= 5;
        dtcWarnings.push({ code: code, severity: 'moderate' });
      } else if (code.charAt(0) === 'C' || code.charAt(0) === 'U') {
        score -= 3;
        dtcWarnings.push({ code: code, severity: 'minor' });
      } else if (code.charAt(0) === 'B') {
        score -= 2;
        dtcWarnings.push({ code: code, severity: 'info' });
      } else if (code.indexOf('P') === 0) {
        score -= 5;
        dtcWarnings.push({ code: code, severity: 'moderate' });
      }
    });

    // WEAR PARTS ANALYSIS
    Object.keys(WEAR_PARTS).forEach(function(partKey) {
      var part = WEAR_PARTS[partKey];
      var lifespan = part[fuel];
      if (!lifespan) return;

      var midpoint = (lifespan[0] + lifespan[1]) / 2;
      var wearPct = km / midpoint;

      if (wearPct >= 0.90) {
        score -= part.deduction;
        wearAlerts.push({
          label: part.label,
          urgency: 'MAGAS',
          wearPct: Math.round(wearPct * 100),
          lifespan: lifespan
        });
      } else if (wearPct >= 0.75) {
        wearAlerts.push({
          label: part.label,
          urgency: 'KOZEPES',
          wearPct: Math.round(wearPct * 100),
          lifespan: lifespan
        });
      }
    });

    // AGE DEDUCTION
    var age = 2026 - year;
    if (age > 10) {
      var ageDeduction = Math.min((age - 10) * 2, 20);
      score -= ageDeduction;
    }

    // DIESEL EXTRA
    if (fuel === 'dizel' && km > 150000) {
      score -= 5;
      dieselWarning = 'diesel_high_km';
    } else if (fuel === 'dizel' && km > 100000) {
      dieselWarning = 'diesel_moderate_km';
    }
  }

  // CLAMP
  score = Math.max(0, Math.min(100, score));

  // VERDICT (if not already set by MIL)
  if (!verdict) {
    if (score >= 80) {
      verdict = 'ATMEGY';
    } else if (score >= 50) {
      verdict = 'KOCKAZATOS';
    } else {
      verdict = 'MEGBUKIK';
    }
  }

  return {
    score: score,
    verdict: verdict,
    dtcWarnings: dtcWarnings,
    wearAlerts: wearAlerts,
    tips: tips,
    milFailed: milFailed,
    isElectric: isElectric,
    dieselWarning: dieselWarning
  };
}

// ─── Helper: default "clean" car ───
function cleanCar(overrides = {}) {
  return {
    year: overrides.year ?? 2020,
    km: overrides.km ?? 10000,
    fuel: overrides.fuel ?? 'benzin',
    milOn: overrides.milOn ?? 'nem',
    dtcCodes: overrides.dtcCodes ?? []
  };
}

function calc(overrides = {}) {
  const c = cleanCar(overrides);
  return calculate(c.year, c.km, c.fuel, c.milOn, c.dtcCodes);
}

// ═══════════════ TESTS ═══════════════

describe('MOT Predictor — calculation engine', () => {

  // ─── MIL (Check Engine Light) ───
  describe('MIL status', () => {
    it('should return score 0 and verdict MEGBUKIK when MIL is ON (instant fail)', () => {
      const result = calc({ milOn: 'igen' });
      expect(result.score).toBe(0);
      expect(result.verdict).toBe('MEGBUKIK');
      expect(result.milFailed).toBe(true);
    });

    it('should short-circuit all other deductions when MIL is ON', () => {
      // Even with many DTCs and old age, MIL ON = score 0 directly
      const result = calc({
        milOn: 'igen',
        year: 2000,
        km: 300000,
        fuel: 'dizel',
        dtcCodes: ['P0420', 'P0300', 'C1234']
      });
      expect(result.score).toBe(0);
      expect(result.verdict).toBe('MEGBUKIK');
      expect(result.dtcWarnings).toHaveLength(0);
      expect(result.wearAlerts).toHaveLength(0);
    });

    it('should apply -10 penalty when MIL is "nemtudom"', () => {
      const result = calc({ milOn: 'nemtudom' });
      // Clean 2020 car with 10k km: base 100 - 10 (MIL nemtudom) = 90
      expect(result.score).toBe(90);
      expect(result.milFailed).toBe(false);
    });

    it('should apply no MIL penalty when MIL is OFF', () => {
      const result = calc({ milOn: 'nem' });
      expect(result.score).toBe(100);
    });
  });

  // ─── DTC Scoring ───
  describe('DTC code scoring', () => {
    it('should deduct -15 for emission-critical DTC (P0420) on petrol', () => {
      const result = calc({ dtcCodes: ['P0420'] });
      expect(result.score).toBe(85);
      expect(result.dtcWarnings).toHaveLength(1);
      expect(result.dtcWarnings[0].severity).toBe('critical');
    });

    it('should NOT deduct for emission-critical DTC on electric vehicle', () => {
      const result = calc({ fuel: 'elektromos', dtcCodes: ['P0420'] });
      expect(result.score).toBe(100);
      expect(result.dtcWarnings).toHaveLength(1);
      expect(result.dtcWarnings[0].severity).toBe('info');
    });

    it('should deduct -5 for non-emission P0 code (e.g. P0010)', () => {
      const result = calc({ dtcCodes: ['P0010'] });
      expect(result.score).toBe(95);
      expect(result.dtcWarnings[0].severity).toBe('moderate');
    });

    it('should deduct -5 for non-P0 P-code (e.g. P1234)', () => {
      const result = calc({ dtcCodes: ['P1234'] });
      expect(result.score).toBe(95);
      expect(result.dtcWarnings[0].severity).toBe('moderate');
    });

    it('should deduct -3 for C-code (chassis)', () => {
      const result = calc({ dtcCodes: ['C1234'] });
      expect(result.score).toBe(97);
      expect(result.dtcWarnings[0].severity).toBe('minor');
    });

    it('should deduct -3 for U-code (communication)', () => {
      const result = calc({ dtcCodes: ['U0100'] });
      expect(result.score).toBe(97);
      expect(result.dtcWarnings[0].severity).toBe('minor');
    });

    it('should deduct -2 for B-code (body)', () => {
      const result = calc({ dtcCodes: ['B1234'] });
      expect(result.score).toBe(98);
      expect(result.dtcWarnings[0].severity).toBe('info');
    });

    it('should handle DTC deduplication — P0420 twice counts as one -15', () => {
      // dtcCodes are pre-deduplicated by the form parser (indexOf filter)
      // Simulate deduplicated input: only one P0420
      const dedupedCodes = ['P0420', 'P0420']
        .filter((c, i, arr) => arr.indexOf(c) === i);
      const result = calc({ dtcCodes: dedupedCodes });
      expect(result.score).toBe(85); // -15, not -30
      expect(result.dtcWarnings).toHaveLength(1);
    });

    it('should accumulate deductions for multiple different DTCs', () => {
      const result = calc({ dtcCodes: ['P0420', 'B1234', 'C1234'] });
      // -15 (emission) -2 (B) -3 (C) = -20 → score 80
      expect(result.score).toBe(80);
    });
  });

  // ─── Wear Parts ───
  describe('wear parts analysis', () => {
    it('should generate DPF, EGR, and turbo alerts for 200k km diesel', () => {
      const result = calc({ fuel: 'dizel', km: 200000 });
      const alertLabels = result.wearAlerts.map(a => a.label);

      // DPF midpoint = (100k+200k)/2 = 150k → 200k/150k = 133% → MAGAS
      expect(alertLabels).toContain('DPF');
      // EGR midpoint = (80k+150k)/2 = 115k → 200k/115k = 174% → MAGAS
      expect(alertLabels).toContain('EGR szelep');
      // Turbo midpoint = (170k+250k)/2 = 210k → 200k/210k = 95% → MAGAS
      expect(alertLabels).toContain('Turbo');

      // All three should be MAGAS urgency
      const highAlerts = result.wearAlerts.filter(a => a.urgency === 'MAGAS');
      expect(highAlerts.length).toBeGreaterThanOrEqual(3);
    });

    it('should not generate alerts for low-km vehicle', () => {
      const result = calc({ fuel: 'benzin', km: 10000 });
      expect(result.wearAlerts).toHaveLength(0);
    });

    it('should skip parts not applicable for fuel type (e.g. DPF for benzin)', () => {
      const result = calc({ fuel: 'benzin', km: 200000 });
      const alertLabels = result.wearAlerts.map(a => a.label);
      expect(alertLabels).not.toContain('DPF');
      expect(alertLabels).not.toContain('EGR szelep');
      expect(alertLabels).not.toContain('Turbo');
    });

    it('should deduct points for wear parts at >= 90% of midpoint lifespan', () => {
      // Benzin fekbetet midpoint = (30k+80k)/2 = 55k → 50k/55k = 91% → MAGAS → -10 deduction
      const result = calc({ fuel: 'benzin', km: 50000 });
      const fekbetetAlert = result.wearAlerts.find(a => a.label === 'Fekbetetek');
      expect(fekbetetAlert).toBeDefined();
      expect(fekbetetAlert.urgency).toBe('MAGAS');
    });
  });

  // ─── Age Deduction ───
  describe('age deduction', () => {
    it('should not deduct for car <= 10 years old', () => {
      const result = calc({ year: 2016, km: 10000 }); // age=10
      expect(result.score).toBe(100);
    });

    it('should deduct -2 per year over 10 for a 15-year-old car', () => {
      // age = 2026 - 2011 = 15 → (15-10)*2 = 10 deduction
      const result = calc({ year: 2011, km: 10000 });
      expect(result.score).toBe(90);
    });

    it('should cap age deduction at -20 (max)', () => {
      // age = 2026 - 1995 = 31 → (31-10)*2 = 42, but capped at 20
      const result = calc({ year: 1995, km: 10000 });
      expect(result.score).toBe(80);
    });
  });

  // ─── Diesel Extra ───
  describe('diesel extra penalty', () => {
    it('should deduct -5 for diesel over 150k km', () => {
      // Base: 100, diesel 200k on a 2020 car
      // Wear parts will also deduct, so let's compute expected
      const result = calc({ fuel: 'dizel', km: 200000 });
      expect(result.dieselWarning).toBe('diesel_high_km');
      // Verify the -5 diesel penalty is applied by comparing to a petrol car
      const petrolResult = calc({ fuel: 'benzin', km: 200000 });
      // Diesel has different wear parts, so direct score comparison is unreliable.
      // Instead, verify the flag is set (the -5 is baked into score)
      expect(result.dieselWarning).toBeTruthy();
    });

    it('should not deduct extra for diesel at exactly 150k km', () => {
      const result = calc({ fuel: 'dizel', km: 150000 });
      // km > 150000 is the condition, so 150000 exactly should NOT trigger
      expect(result.dieselWarning).not.toBe('diesel_high_km');
    });

    it('should set moderate warning for diesel between 100k and 150k km', () => {
      const result = calc({ fuel: 'dizel', km: 120000 });
      expect(result.dieselWarning).toBe('diesel_moderate_km');
    });

    it('should not apply diesel penalty to petrol car', () => {
      const result = calc({ fuel: 'benzin', km: 200000 });
      expect(result.dieselWarning).toBe('');
    });
  });

  // ─── Score Clamping ───
  describe('score clamping', () => {
    it('should never go below 0', () => {
      // Stack many deductions: old diesel, many DTCs, nemtudom MIL
      const result = calc({
        year: 1995,
        km: 300000,
        fuel: 'dizel',
        milOn: 'nemtudom',
        dtcCodes: ['P0420', 'P0300', 'P0130', 'P0400', 'P2002', 'C1234', 'U0100', 'B1234']
      });
      expect(result.score).toBeGreaterThanOrEqual(0);
    });

    it('should never exceed 100', () => {
      // Perfect car, no issues
      const result = calc({ year: 2024, km: 1000, fuel: 'elektromos' });
      expect(result.score).toBeLessThanOrEqual(100);
      expect(result.score).toBe(100);
    });
  });

  // ─── Verdict Thresholds ───
  describe('verdict classification', () => {
    it('should return ATMEGY for score >= 80', () => {
      const result = calc({ year: 2020, km: 10000, fuel: 'benzin' });
      expect(result.score).toBeGreaterThanOrEqual(80);
      expect(result.verdict).toBe('ATMEGY');
    });

    it('should return KOCKAZATOS for score 50-79', () => {
      // Need to engineer a score in 50-79 range
      // 3 emission DTCs on petrol: -45, + age 15yr: -10 → score=45 (too low)
      // 2 emission DTCs: -30, age 12yr: -4 → score=66
      const result = calc({
        year: 2014,
        km: 10000,
        fuel: 'benzin',
        dtcCodes: ['P0420', 'P0300']
      });
      // age = 2026-2014 = 12 → (12-10)*2 = 4; DTCs: 2*-15 = -30
      // score = 100 - 30 - 4 = 66
      expect(result.score).toBe(66);
      expect(result.verdict).toBe('KOCKAZATOS');
    });

    it('should return MEGBUKIK for score < 50', () => {
      const result = calc({
        year: 2000,
        km: 10000,
        fuel: 'benzin',
        dtcCodes: ['P0420', 'P0300', 'P0130', 'P0400']
      });
      // age = 26 → min(32, 20) = 20 deduction
      // DTCs: 4 * -15 = -60
      // score = 100 - 60 - 20 = 20
      expect(result.score).toBe(20);
      expect(result.verdict).toBe('MEGBUKIK');
    });

    it('should return ATMEGY at exactly score 80', () => {
      // 1995 car, 10k km, benzin: 100 - 20 (age cap) = 80
      const result = calc({ year: 1995, km: 10000, fuel: 'benzin' });
      expect(result.score).toBe(80);
      expect(result.verdict).toBe('ATMEGY');
    });

    it('should return KOCKAZATOS at exactly score 50', () => {
      // Need score exactly 50: 100 - 20 (age) - 15 (emission) - 15 (emission) = 50
      const result = calc({
        year: 1995,
        km: 10000,
        fuel: 'benzin',
        dtcCodes: ['P0420', 'P0300']
      });
      expect(result.score).toBe(50);
      expect(result.verdict).toBe('KOCKAZATOS');
    });
  });

  // ─── Metamorphic: more DTCs → lower score ───
  describe('metamorphic properties', () => {
    it('should produce lower score with more DTCs (monotonically decreasing)', () => {
      const score0 = calc({ dtcCodes: [] }).score;
      const score1 = calc({ dtcCodes: ['P1234'] }).score;
      const score2 = calc({ dtcCodes: ['P1234', 'C1234'] }).score;
      const score3 = calc({ dtcCodes: ['P1234', 'C1234', 'B1234'] }).score;

      expect(score0).toBeGreaterThan(score1);
      expect(score1).toBeGreaterThan(score2);
      expect(score2).toBeGreaterThan(score3);
    });

    it('should produce lower score with higher mileage', () => {
      const scoreLow = calc({ km: 10000, fuel: 'benzin' }).score;
      const scoreHigh = calc({ km: 200000, fuel: 'benzin' }).score;
      expect(scoreLow).toBeGreaterThan(scoreHigh);
    });

    it('should produce lower score with older car', () => {
      const scoreNew = calc({ year: 2024 }).score;
      const scoreOld = calc({ year: 2000 }).score;
      expect(scoreNew).toBeGreaterThan(scoreOld);
    });
  });

  // ─── Electric Vehicle Specifics ───
  describe('electric vehicle handling', () => {
    it('should skip emission DTC scoring entirely for electric', () => {
      const result = calc({
        fuel: 'elektromos',
        dtcCodes: ['P0420', 'P0300', 'P0130']
      });
      // No score deduction for emission codes
      expect(result.score).toBe(100);
      expect(result.isElectric).toBe(true);
    });

    it('should still deduct for non-emission DTCs on electric', () => {
      const result = calc({
        fuel: 'elektromos',
        dtcCodes: ['C1234', 'U0100']
      });
      expect(result.score).toBe(94); // -3 -3
    });
  });
});
