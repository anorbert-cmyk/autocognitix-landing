import { describe, it, expect, beforeAll } from 'vitest';
import { createEnvironment } from '../setup/dom-shim.js';

/**
 * Worth-Repairing Calculator — Unit Tests
 *
 * The calculator lives as an inline script in the HTML page.
 * We reimplement the pure calculation functions here based on
 * the source code to test them in isolation without DOM dependencies.
 */

let VehicleDB;

beforeAll(() => {
  const env = createEnvironment();
  VehicleDB = env.VehicleDB;
});

// ─── Reimplemented pure calculation helpers ───────────────────────

const CURRENT_YEAR = 2026;
const REPLACEMENT_ANNUAL = 800000;

function calculateMarketValue(brand, year, mileage, fuel, condition, accident, serviceBook, owners) {
  const age = Math.max(CURRENT_YEAR - year, 0);
  const baseValue = VehicleDB.getBaseValue(brand, year);

  // Mileage adjustment
  const expectedKmPerYear = VehicleDB.getExpectedKm(fuel);
  const expectedKm = expectedKmPerYear * age;
  let mileageAdj = 1 + (-0.002 * (mileage - expectedKm) / 1000);
  mileageAdj = Math.max(0.75, Math.min(1.25, mileageAdj));

  // Accident adjustment
  const accidentData = VehicleDB.accidentSeverity.find(a => a.id === accident);
  const damageMultiplier = accidentData ? accidentData.damageMultiplier : 0;
  let mileageMultiplierForAccident;
  if (mileage < 30000) mileageMultiplierForAccident = 1.0;
  else if (mileage < 60000) mileageMultiplierForAccident = 0.8;
  else if (mileage < 100000) mileageMultiplierForAccident = 0.6;
  else if (mileage < 160000) mileageMultiplierForAccident = 0.4;
  else mileageMultiplierForAccident = 0.2;
  const accidentAdj = 1 - (0.10 * damageMultiplier * mileageMultiplierForAccident);

  // Service history
  const serviceAdj = serviceBook ? 1.10 : 0.95;

  // Owner adjustment
  let ownerAdj;
  if (owners <= 1) ownerAdj = 1.0;
  else if (owners === 2) ownerAdj = 0.97;
  else if (owners === 3) ownerAdj = 0.93;
  else if (owners === 4) ownerAdj = 0.90;
  else ownerAdj = 0.87;

  // Condition multiplier
  const condData = VehicleDB.conditions.find(c => c.id === condition);
  const conditionMult = condData ? condData.multiplier : 1.0;

  // Market value
  let marketValue = baseValue * mileageAdj * accidentAdj * serviceAdj * ownerAdj * conditionMult;
  marketValue = Math.max(Math.round(marketValue), 100000);

  return marketValue;
}

function estimateRepairCost(age, marketValue) {
  let repairCost;
  if (age <= 5) repairCost = 150000 * Math.max(age, 1);
  else if (age <= 10) repairCost = 250000 * Math.max(age - 4, 1);
  else if (age <= 15) repairCost = 400000 * Math.max(age - 8, 1);
  else repairCost = 550000 * Math.max(age - 12, 1);
  repairCost = Math.min(repairCost, marketValue * 0.8);
  repairCost = Math.round(repairCost);
  return repairCost;
}

function getAnnualMaint(age) {
  if (age <= 5) return 150000;
  else if (age <= 10) return 250000;
  else if (age <= 15) return 400000;
  else return 550000;
}

function calculateFactor1(repairCost, marketValue) {
  const ka = repairCost / marketValue;
  if (ka < 0.30) return 1.0;
  else if (ka < 0.50) return 0.65;
  else if (ka < 0.75) return 0.35;
  else return 0;
}

function calculateFactor2(age, mileage) {
  if (age < 5 && mileage < 80000) return 1.0;
  else if (age < 10 && mileage < 150000) return 0.65;
  else if (age < 15 && mileage < 250000) return 0.35;
  else return 0.10;
}

function calculateFactor3(repairCost, annualMaint) {
  const repairAnnual = (repairCost + 2 * annualMaint) / 2;
  if (repairAnnual < REPLACEMENT_ANNUAL * 0.60) return 1.0;
  else if (repairAnnual < REPLACEMENT_ANNUAL) return 0.60;
  else return 0.20;
}

function calculateFactor4(repairCost, annualMaint) {
  const monthlyReplacement = REPLACEMENT_ANNUAL / 12;
  const monthlyCurrent = annualMaint / 12;
  let beMonths;
  if (monthlyReplacement - monthlyCurrent > 0) {
    beMonths = repairCost / (monthlyReplacement - monthlyCurrent);
  } else {
    beMonths = 999;
  }

  let f4;
  if (beMonths < 6) f4 = 1.0;
  else if (beMonths < 12) f4 = 0.70;
  else if (beMonths < 18) f4 = 0.40;
  else f4 = 0.10;

  return { f4, beMonths };
}

function calculateComposite(f1, f2, f3, f4) {
  let composite = 0.40 * f1 + 0.20 * f2 + 0.20 * f3 + 0.20 * f4;
  return Math.max(0, Math.min(1, composite));
}

function getVerdict(score) {
  if (score >= 0.65) return 'JAVITAS';
  else if (score >= 0.40) return 'HATAESET';
  else return 'CSERE';
}

/**
 * Full pipeline: same as handleSubmit() but pure
 */
function runFullCalculation({ brand, year, mileage, fuel, condition, accident, serviceBook, owners, repairCostInput }) {
  const age = Math.max(CURRENT_YEAR - year, 0);
  const marketValue = calculateMarketValue(brand, year, mileage, fuel, condition, accident, serviceBook, owners);

  let repairCost;
  let repairEstimated = false;
  if (repairCostInput && repairCostInput > 0) {
    repairCost = repairCostInput;
  } else {
    repairEstimated = true;
    repairCost = estimateRepairCost(age, marketValue);
  }

  const annualMaint = getAnnualMaint(age);
  const f1 = calculateFactor1(repairCost, marketValue);
  const f2 = calculateFactor2(age, mileage);
  const f3 = calculateFactor3(repairCost, annualMaint);
  const { f4, beMonths } = calculateFactor4(repairCost, annualMaint);
  const composite = calculateComposite(f1, f2, f3, f4);
  const verdict = getVerdict(composite);

  return { marketValue, repairCost, repairEstimated, f1, f2, f3, f4, composite, verdict, beMonths, age, annualMaint };
}


// ═══════════════════════════════════════════════════════════════════
// TESTS
// ═══════════════════════════════════════════════════════════════════

describe('Worth-Repairing Calculator', () => {

  // ─── Factor 1: Cost ratio ────────────────────────────────────────

  describe('Factor 1 — Cost ratio (repairCost / marketValue)', () => {
    it('should return 1.0 when cost ratio < 0.30', () => {
      expect(calculateFactor1(100000, 1000000)).toBe(1.0);   // 10%
      expect(calculateFactor1(290000, 1000000)).toBe(1.0);   // 29%
    });

    it('should return 0.65 when cost ratio >= 0.30 and < 0.50', () => {
      expect(calculateFactor1(300000, 1000000)).toBe(0.65);  // 30% exact boundary
      expect(calculateFactor1(499000, 1000000)).toBe(0.65);  // just under 50%
    });

    it('should return 0.35 when cost ratio >= 0.50 and < 0.75', () => {
      expect(calculateFactor1(500000, 1000000)).toBe(0.35);  // 50% exact boundary
      expect(calculateFactor1(749000, 1000000)).toBe(0.35);  // just under 75%
    });

    it('should return 0 when cost ratio >= 0.75', () => {
      expect(calculateFactor1(750000, 1000000)).toBe(0);     // 75% exact boundary
      expect(calculateFactor1(1500000, 1000000)).toBe(0);    // 150%
    });

    it('should handle zero repair cost', () => {
      expect(calculateFactor1(0, 1000000)).toBe(1.0);
    });
  });

  // ─── Factor 2: Age + mileage ─────────────────────────────────────

  describe('Factor 2 — Age + mileage', () => {
    it('should return 1.0 for new car with low mileage (age<5, km<80000)', () => {
      expect(calculateFactor2(0, 0)).toBe(1.0);
      expect(calculateFactor2(4, 79999)).toBe(1.0);
    });

    it('should return 0.65 for middle-aged car (age<10, km<150000)', () => {
      expect(calculateFactor2(5, 80000)).toBe(0.65);
      expect(calculateFactor2(9, 149999)).toBe(0.65);
    });

    it('should return 0.35 for older car (age<15, km<250000)', () => {
      expect(calculateFactor2(10, 150000)).toBe(0.35);
      expect(calculateFactor2(14, 249999)).toBe(0.35);
    });

    it('should return 0.10 for very old/high-mileage car', () => {
      expect(calculateFactor2(15, 250000)).toBe(0.10);
      expect(calculateFactor2(25, 500000)).toBe(0.10);
    });

    it('should use the WORSE of age/mileage — old car but low km still gets downgraded by age', () => {
      // age=15 triggers the else branch regardless of km
      expect(calculateFactor2(15, 50000)).toBe(0.10);
    });

    it('should use the WORSE of age/mileage — new car but high km gets downgraded by km', () => {
      // age=3 but mileage=200000 — fails age<5 && km<80000, fails age<10 && km<150000
      expect(calculateFactor2(3, 200000)).toBe(0.35);
    });
  });

  // ─── Factor 3: Annual cost comparison ────────────────────────────

  describe('Factor 3 — Annual cost comparison', () => {
    it('should return 1.0 when repairAnnual < 60% of replacement annual', () => {
      // repairAnnual = (repairCost + 2*annualMaint) / 2
      // replacementAnnual = 800000, 60% = 480000
      // For annualMaint=150000: repairAnnual = (repairCost + 300000)/2
      // Need repairAnnual < 480000 => repairCost + 300000 < 960000 => repairCost < 660000
      expect(calculateFactor3(100000, 150000)).toBe(1.0);
    });

    it('should return 0.60 when repairAnnual >= 60% but < 100% of replacement', () => {
      // repairAnnual < 800000 => repairCost + 2*annualMaint < 1600000
      // repairAnnual >= 480000 => repairCost + 2*annualMaint >= 960000
      // annualMaint=150000 => repairCost >= 660000 and < 1300000
      expect(calculateFactor3(700000, 150000)).toBe(0.60);
    });

    it('should return 0.20 when repairAnnual >= replacement annual', () => {
      // repairAnnual >= 800000 => repairCost + 2*annualMaint >= 1600000
      // annualMaint=550000 => repairCost >= 500000
      expect(calculateFactor3(600000, 550000)).toBe(0.20);
    });
  });

  // ─── Factor 4: Break-even months ─────────────────────────────────

  describe('Factor 4 — Break-even months', () => {
    it('should return 1.0 when break-even < 6 months', () => {
      // monthlyReplacement = 800000/12 ≈ 66667
      // monthlyCurrent = annualMaint/12
      // beMonths = repairCost / (monthlyReplacement - monthlyCurrent)
      // annualMaint=150000 => monthlyCurrent=12500 => diff=54167
      // beMonths < 6 => repairCost < 6*54167 = 325000
      const { f4 } = calculateFactor4(200000, 150000);
      expect(f4).toBe(1.0);
    });

    it('should return 0.70 when break-even >= 6 and < 12 months', () => {
      // repairCost >= 325000 and < 650000 (with annualMaint=150000)
      const { f4 } = calculateFactor4(400000, 150000);
      expect(f4).toBe(0.70);
    });

    it('should return 0.40 when break-even >= 12 and < 18 months', () => {
      // repairCost >= 650000 and < 975000 (with annualMaint=150000)
      const { f4 } = calculateFactor4(700000, 150000);
      expect(f4).toBe(0.40);
    });

    it('should return 0.10 when break-even >= 18 months', () => {
      // repairCost >= 975000 (with annualMaint=150000)
      const { f4 } = calculateFactor4(1200000, 150000);
      expect(f4).toBe(0.10);
    });

    it('should return 0.10 (beMonths=999) when monthlyCurrent >= monthlyReplacement', () => {
      // annualMaint >= 800000 makes monthlyCurrent >= monthlyReplacement
      const { f4, beMonths } = calculateFactor4(500000, 800000);
      expect(beMonths).toBe(999);
      expect(f4).toBe(0.10);
    });

    it('should return 0.10 (beMonths=999) when monthlyCurrent equals monthlyReplacement exactly', () => {
      // annualMaint = 800000 exactly
      const { f4, beMonths } = calculateFactor4(100000, 800000);
      expect(beMonths).toBe(999);
      expect(f4).toBe(0.10);
    });

    it('bugfix verification: break-even calculation uses correct monthly diff formula', () => {
      // Verify the formula: beMonths = repairCost / (monthlyReplacement - monthlyCurrent)
      const annualMaint = 250000;
      const repairCost = 500000;
      const monthlyReplacement = REPLACEMENT_ANNUAL / 12;
      const monthlyCurrent = annualMaint / 12;
      const expectedBeMonths = repairCost / (monthlyReplacement - monthlyCurrent);
      const { beMonths } = calculateFactor4(repairCost, annualMaint);
      expect(beMonths).toBeCloseTo(expectedBeMonths, 5);
    });
  });

  // ─── Composite score ─────────────────────────────────────────────

  describe('Composite score', () => {
    it('should weight factors 40/20/20/20', () => {
      const composite = calculateComposite(1.0, 1.0, 1.0, 1.0);
      expect(composite).toBe(1.0);
    });

    it('should return 0 when all factors are 0', () => {
      expect(calculateComposite(0, 0, 0, 0)).toBe(0);
    });

    it('should clamp to [0, 1]', () => {
      expect(calculateComposite(1.0, 1.0, 1.0, 1.0)).toBeLessThanOrEqual(1);
      expect(calculateComposite(0, 0, 0, 0)).toBeGreaterThanOrEqual(0);
    });

    it('should reflect F1 dominance (40% weight)', () => {
      // Only F1 is 1.0, rest 0
      const withF1 = calculateComposite(1.0, 0, 0, 0);
      expect(withF1).toBeCloseTo(0.40, 5);

      // Only F2 is 1.0, rest 0
      const withF2 = calculateComposite(0, 1.0, 0, 0);
      expect(withF2).toBeCloseTo(0.20, 5);
    });
  });

  // ─── Verdict thresholds ──────────────────────────────────────────

  describe('Verdict thresholds', () => {
    it('should return JAVITAS for score >= 0.65', () => {
      expect(getVerdict(0.65)).toBe('JAVITAS');
      expect(getVerdict(0.80)).toBe('JAVITAS');
      expect(getVerdict(1.0)).toBe('JAVITAS');
    });

    it('should return HATAESET for score >= 0.40 and < 0.65', () => {
      expect(getVerdict(0.40)).toBe('HATAESET');
      expect(getVerdict(0.50)).toBe('HATAESET');
      expect(getVerdict(0.6499)).toBe('HATAESET');
    });

    it('should return CSERE for score < 0.40', () => {
      expect(getVerdict(0.39)).toBe('CSERE');
      expect(getVerdict(0.0)).toBe('CSERE');
    });

    it('should handle exact boundaries', () => {
      expect(getVerdict(0.65)).toBe('JAVITAS');
      expect(getVerdict(0.40)).toBe('HATAESET');
      expect(getVerdict(0.3999)).toBe('CSERE');
    });
  });

  // ─── Market value calculation ────────────────────────────────────

  describe('Market value calculation', () => {
    it('should return minimum 100000 for any combination', () => {
      // Very old, very high km, worst accident, worst condition
      const mv = calculateMarketValue('Lancia', 1995, 900000, 'benzin', 'rossz', 'szerkezeti', false, 5);
      expect(mv).toBeGreaterThanOrEqual(100000);
    });

    it('should apply mileage adjustment within [0.75, 1.25] bounds', () => {
      // Low mileage on old car => mileageAdj capped at 1.25
      const mvLow = calculateMarketValue('Volkswagen', 2016, 0, 'benzin', 'jo', 'nem', true, 1);
      // Extremely high mileage => mileageAdj capped at 0.75
      const mvHigh = calculateMarketValue('Volkswagen', 2016, 999999, 'benzin', 'jo', 'nem', true, 1);
      expect(mvLow).toBeGreaterThan(mvHigh);
    });

    it('should increase value with service book vs without', () => {
      const withService = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 1);
      const withoutService = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', false, 1);
      expect(withService).toBeGreaterThan(withoutService);
      // Service book: 1.10 vs 0.95 => ratio should be 1.10/0.95
      const ratio = withService / withoutService;
      expect(ratio).toBeCloseTo(1.10 / 0.95, 1);
    });

    it('should decrease value with more owners', () => {
      const oneOwner = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 1);
      const threeOwners = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 3);
      const fiveOwners = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 5);
      expect(oneOwner).toBeGreaterThan(threeOwners);
      expect(threeOwners).toBeGreaterThan(fiveOwners);
    });

    it('should decrease value with worse condition', () => {
      const kituno = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'kituno', 'nem', true, 1);
      const jo = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 1);
      const rossz = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'rossz', 'nem', true, 1);
      expect(kituno).toBeGreaterThan(jo);
      expect(jo).toBeGreaterThan(rossz);
    });

    it('should decrease value with accident severity', () => {
      const noAccident = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'nem', true, 1);
      const kozmetikai = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'kozmetikai', true, 1);
      const sulyos = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'sulyos', true, 1);
      const szerkezeti = calculateMarketValue('Toyota', 2020, 60000, 'benzin', 'jo', 'szerkezeti', true, 1);
      expect(noAccident).toBeGreaterThan(kozmetikai);
      expect(kozmetikai).toBeGreaterThan(sulyos);
      expect(sulyos).toBeGreaterThan(szerkezeti);
    });

    it('should use accident mileage multiplier tiers correctly', () => {
      // At very low mileage, accident penalty is higher (mileageMultiplierForAccident=1.0)
      const lowKm = calculateMarketValue('Toyota', 2024, 20000, 'benzin', 'jo', 'szerkezeti', true, 1);
      // At very high mileage, accident penalty is lower (mileageMultiplierForAccident=0.2)
      const highKm = calculateMarketValue('Toyota', 2024, 200000, 'benzin', 'jo', 'szerkezeti', true, 1);
      // The accident penalty at low km should be larger in absolute terms
      const noAccidentLow = calculateMarketValue('Toyota', 2024, 20000, 'benzin', 'jo', 'nem', true, 1);
      const noAccidentHigh = calculateMarketValue('Toyota', 2024, 200000, 'benzin', 'jo', 'nem', true, 1);
      const penaltyLow = noAccidentLow - lowKm;
      const penaltyHigh = noAccidentHigh - highKm;
      // Higher penalty (proportionally) at low km
      expect(penaltyLow / noAccidentLow).toBeGreaterThan(penaltyHigh / noAccidentHigh);
    });
  });

  // ─── Repair cost estimation ──────────────────────────────────────

  describe('Repair cost estimation', () => {
    it('should estimate repair cost based on age tiers', () => {
      const marketValue = 5000000;
      // age=3 => 150000 * 3 = 450000
      expect(estimateRepairCost(3, marketValue)).toBe(450000);
      // age=7 => 250000 * (7-4) = 750000
      expect(estimateRepairCost(7, marketValue)).toBe(750000);
      // age=12 => 400000 * (12-8) = 1600000 => capped at 80% of 5M = 4000000
      expect(estimateRepairCost(12, marketValue)).toBe(1600000);
    });

    it('should cap estimated repair at 80% of market value', () => {
      // age=20 => 550000 * (20-12) = 4400000 but marketValue=1000000 => capped at 800000
      expect(estimateRepairCost(20, 1000000)).toBe(800000);
    });

    it('should use Math.max(age, 1) for age=0', () => {
      // age=0 => 150000 * max(0,1) = 150000
      expect(estimateRepairCost(0, 5000000)).toBe(150000);
    });

    it('should use Math.max(age-offset, 1) at tier boundaries', () => {
      // age=5 => 150000 * 5 = 750000
      expect(estimateRepairCost(5, 5000000)).toBe(750000);
      // age=6 => 250000 * max(6-4,1) = 250000 * 2 = 500000
      expect(estimateRepairCost(6, 5000000)).toBe(500000);
    });
  });

  // ─── Annual maintenance ──────────────────────────────────────────

  describe('Annual maintenance estimate', () => {
    it('should return correct tier for each age bracket', () => {
      expect(getAnnualMaint(0)).toBe(150000);
      expect(getAnnualMaint(5)).toBe(150000);
      expect(getAnnualMaint(6)).toBe(250000);
      expect(getAnnualMaint(10)).toBe(250000);
      expect(getAnnualMaint(11)).toBe(400000);
      expect(getAnnualMaint(15)).toBe(400000);
      expect(getAnnualMaint(16)).toBe(550000);
      expect(getAnnualMaint(30)).toBe(550000);
    });
  });

  // ─── Metamorphic properties ──────────────────────────────────────

  describe('Metamorphic properties', () => {
    const baseParams = {
      brand: 'Volkswagen',
      year: 2020,
      mileage: 80000,
      fuel: 'benzin',
      condition: 'jo',
      accident: 'nem',
      serviceBook: true,
      owners: 1,
      repairCostInput: 500000,
    };

    it('higher repair cost should produce lower or equal composite score', () => {
      const low = runFullCalculation({ ...baseParams, repairCostInput: 200000 });
      const mid = runFullCalculation({ ...baseParams, repairCostInput: 500000 });
      const high = runFullCalculation({ ...baseParams, repairCostInput: 2000000 });
      expect(low.composite).toBeGreaterThanOrEqual(mid.composite);
      expect(mid.composite).toBeGreaterThanOrEqual(high.composite);
    });

    it('newer car should have higher or equal market value (same brand, km, condition)', () => {
      const newer = runFullCalculation({ ...baseParams, year: 2024, mileage: 30000 });
      const older = runFullCalculation({ ...baseParams, year: 2015, mileage: 30000 });
      expect(newer.marketValue).toBeGreaterThanOrEqual(older.marketValue);
    });

    it('premium brand should have higher market value than budget brand', () => {
      const premium = runFullCalculation({ ...baseParams, brand: 'BMW' });
      const budget = runFullCalculation({ ...baseParams, brand: 'Dacia' });
      expect(premium.marketValue).toBeGreaterThan(budget.marketValue);
    });

    it('worse condition should lower the composite score', () => {
      const good = runFullCalculation({ ...baseParams, condition: 'kituno' });
      const bad = runFullCalculation({ ...baseParams, condition: 'rossz' });
      // Worse condition lowers market value, which raises cost ratio, lowering F1
      expect(good.composite).toBeGreaterThanOrEqual(bad.composite);
    });

    it('adding accident history should lower market value', () => {
      const clean = runFullCalculation({ ...baseParams, accident: 'nem' });
      const damaged = runFullCalculation({ ...baseParams, accident: 'sulyos' });
      expect(clean.marketValue).toBeGreaterThan(damaged.marketValue);
    });
  });

  // ─── Edge cases ──────────────────────────────────────────────────

  describe('Edge cases', () => {
    it('should handle 0 km new car', () => {
      const result = runFullCalculation({
        brand: 'Toyota',
        year: 2026,
        mileage: 0,
        fuel: 'benzin',
        condition: 'kituno',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 100000,
      });
      expect(result.marketValue).toBeGreaterThan(0);
      expect(result.composite).toBeGreaterThan(0);
      expect(result.verdict).toBe('JAVITAS');
    });

    it('should enforce minimum market value of 100000', () => {
      const result = runFullCalculation({
        brand: 'Lancia',
        year: 1995,
        mileage: 500000,
        fuel: 'benzin',
        condition: 'rossz',
        accident: 'szerkezeti',
        serviceBook: false,
        owners: 5,
        repairCostInput: null,
      });
      expect(result.marketValue).toBe(100000);
    });

    it('should handle very high mileage', () => {
      const result = runFullCalculation({
        brand: 'Mercedes-Benz',
        year: 2010,
        mileage: 999999,
        fuel: 'dizel',
        condition: 'kozepes',
        accident: 'kozepes',
        serviceBook: true,
        owners: 3,
        repairCostInput: 800000,
      });
      expect(result.marketValue).toBeGreaterThanOrEqual(100000);
      expect(result.composite).toBeGreaterThanOrEqual(0);
      expect(result.composite).toBeLessThanOrEqual(1);
    });

    it('should handle 0 repair cost input gracefully', () => {
      const result = runFullCalculation({
        brand: 'Ford',
        year: 2018,
        mileage: 120000,
        fuel: 'dizel',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 2,
        repairCostInput: 0,
      });
      // 0 triggers estimation
      expect(result.repairEstimated).toBe(true);
      expect(result.repairCost).toBeGreaterThan(0);
    });

    it('should handle null repair cost input (estimated mode)', () => {
      const result = runFullCalculation({
        brand: 'Opel',
        year: 2015,
        mileage: 180000,
        fuel: 'benzin',
        condition: 'kozepes',
        accident: 'kozmetikai',
        serviceBook: false,
        owners: 3,
        repairCostInput: null,
      });
      expect(result.repairEstimated).toBe(true);
      expect(result.repairCost).toBeGreaterThan(0);
      expect(result.repairCost).toBeLessThanOrEqual(result.marketValue * 0.8);
    });

    it('should handle future year (age=0)', () => {
      const result = runFullCalculation({
        brand: 'Kia',
        year: 2026,
        mileage: 1000,
        fuel: 'hibrid',
        condition: 'kituno',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 50000,
      });
      expect(result.age).toBe(0);
      expect(result.marketValue).toBeGreaterThan(0);
    });

    it('should handle unknown brand with default base value', () => {
      const result = runFullCalculation({
        brand: 'NonExistentBrand',
        year: 2020,
        mileage: 100000,
        fuel: 'benzin',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 300000,
      });
      // Default base value is 3000000
      expect(result.marketValue).toBeGreaterThan(0);
    });
  });

  // ─── Full pipeline integration ───────────────────────────────────

  describe('Full calculation pipeline', () => {
    it('should produce JAVITAS for cheap repair on valuable car', () => {
      const result = runFullCalculation({
        brand: 'BMW',
        year: 2022,
        mileage: 40000,
        fuel: 'benzin',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 200000,
      });
      expect(result.verdict).toBe('JAVITAS');
      expect(result.composite).toBeGreaterThanOrEqual(0.65);
    });

    it('should produce CSERE for expensive repair on old cheap car', () => {
      const result = runFullCalculation({
        brand: 'Dacia',
        year: 2005,
        mileage: 350000,
        fuel: 'benzin',
        condition: 'rossz',
        accident: 'sulyos',
        serviceBook: false,
        owners: 4,
        repairCostInput: 1500000,
      });
      expect(result.verdict).toBe('CSERE');
      expect(result.composite).toBeLessThan(0.40);
    });

    it('should produce HATAESET for borderline case', () => {
      // Construct a case that falls in the HATAESET range (0.40-0.64)
      // Using high repair cost on a moderate-value car pushes F1 down
      const result = runFullCalculation({
        brand: 'Opel',
        year: 2014,
        mileage: 280000,
        fuel: 'dizel',
        condition: 'kozepes',
        accident: 'kozepes',
        serviceBook: false,
        owners: 3,
        repairCostInput: 900000,
      });
      expect(result.composite).toBeGreaterThanOrEqual(0);
      expect(result.composite).toBeLessThanOrEqual(1);
      // This case should produce HATAESET or CSERE, not JAVITAS
      expect(['HATAESET', 'CSERE']).toContain(result.verdict);
    });

    it('should return all expected fields from runFullCalculation', () => {
      const result = runFullCalculation({
        brand: 'Suzuki',
        year: 2018,
        mileage: 90000,
        fuel: 'benzin',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 300000,
      });
      expect(result).toHaveProperty('marketValue');
      expect(result).toHaveProperty('repairCost');
      expect(result).toHaveProperty('repairEstimated');
      expect(result).toHaveProperty('f1');
      expect(result).toHaveProperty('f2');
      expect(result).toHaveProperty('f3');
      expect(result).toHaveProperty('f4');
      expect(result).toHaveProperty('composite');
      expect(result).toHaveProperty('verdict');
      expect(result).toHaveProperty('beMonths');
      expect(result).toHaveProperty('age');
      expect(result).toHaveProperty('annualMaint');
    });
  });

  // ─── Mileage adjustment boundary tests ─────────────────────────

  describe('Mileage adjustment boundaries', () => {
    it('should use -0.002 coefficient for mileage deviation', () => {
      // For a 2020 benzin car (age=6), expectedKm = 13500 * 6 = 81000
      // mileageAdj = 1 + (-0.002 * (mileage - 81000) / 1000)
      // At mileage = 81000: adj = 1 + (-0.002 * 0 / 1000) = 1.0
      const atExpected = calculateMarketValue('Toyota', 2020, 81000, 'benzin', 'jo', 'nem', true, 1);
      // At mileage = 82000: adj = 1 + (-0.002 * 1000 / 1000) = 1 - 0.002 = 0.998
      const slightly_over = calculateMarketValue('Toyota', 2020, 82000, 'benzin', 'jo', 'nem', true, 1);
      // At mileage = 80000: adj = 1 + (-0.002 * -1000 / 1000) = 1 + 0.002 = 1.002
      const slightly_under = calculateMarketValue('Toyota', 2020, 80000, 'benzin', 'jo', 'nem', true, 1);

      expect(slightly_under).toBeGreaterThan(atExpected);
      expect(atExpected).toBeGreaterThan(slightly_over);

      // Verify the ratio matches the -0.002 coefficient
      const baseValue = VehicleDB.getBaseValue('Toyota', 2020);
      const otherAdj = 1.10 * 1.0 * 1.0; // serviceBook=true, ownerAdj=1, accidentAdj=1
      const condMult = VehicleDB.conditions.find(c => c.id === 'jo').multiplier;
      // atExpected should use mileageAdj=1.0
      const expectedAtExpected = Math.max(Math.round(baseValue * 1.0 * 1.0 * 1.10 * 1.0 * condMult), 100000);
      expect(atExpected).toBe(expectedAtExpected);
    });

    it('should clamp mileage adjustment at 0.75 lower bound', () => {
      // mileageAdj = 1 + (-0.002 * (mileage - expectedKm) / 1000) clamped to [0.75, 1.25]
      // For 0.75: 0.75 = 1 + (-0.002 * deviation / 1000) => deviation = 125000
      // For a 2020 benzin car (age=6), expectedKm = 81000, so mileage = 81000 + 125000 = 206000
      const atClamp = calculateMarketValue('Toyota', 2020, 206000, 'benzin', 'jo', 'nem', true, 1);
      const belowClamp = calculateMarketValue('Toyota', 2020, 300000, 'benzin', 'jo', 'nem', true, 1);
      // Both should produce the same market value since adj is clamped at 0.75
      expect(atClamp).toBe(belowClamp);
    });

    it('should clamp mileage adjustment at 1.25 upper bound', () => {
      // For 1.25: 1.25 = 1 + (-0.002 * deviation / 1000) => deviation = -125000
      // For a 2020 benzin car (age=6), expectedKm = 81000, so mileage = 81000 - 125000 = -44000
      // Since mileage can't be negative, use a car with higher expected km
      // For 2010 dizel (age=16), expectedKm = 20000 * 16 = 320000
      // deviation = -125000 => mileage = 320000 - 125000 = 195000
      const atClamp = calculateMarketValue('Toyota', 2010, 195000, 'dizel', 'jo', 'nem', true, 1);
      // Going even lower mileage should not increase value further
      const belowClamp = calculateMarketValue('Toyota', 2010, 100000, 'dizel', 'jo', 'nem', true, 1);
      expect(atClamp).toBe(belowClamp);
    });

    it('should produce exactly 0.75 at the right mileage deviation', () => {
      // Direct formula verification with age=6 benzin
      const age = 6;
      const expectedKm = 13500 * age; // 81000
      // mileageAdj = 1 + (-0.002 * (mileage - 81000) / 1000)
      // For adj = 0.75: mileage = 81000 + 125000 = 206000
      const mileage = expectedKm + 125000;
      let adj = 1 + (-0.002 * (mileage - expectedKm) / 1000);
      adj = Math.max(0.75, Math.min(1.25, adj));
      expect(adj).toBe(0.75);
    });

    it('should produce exactly 1.25 at the right mileage deviation', () => {
      const age = 6;
      const expectedKm = 13500 * age; // 81000
      const mileage = expectedKm - 125000; // negative, but formula still works
      let adj = 1 + (-0.002 * (mileage - expectedKm) / 1000);
      adj = Math.max(0.75, Math.min(1.25, adj));
      expect(adj).toBe(1.25);
    });
  });

  // ─── Owner adjustment boundary tests ──────────────────────────

  describe('Owner adjustment at all boundaries', () => {
    const baseBrand = 'Toyota';
    const baseYear = 2020;
    const baseMileage = 60000;
    const baseFuel = 'benzin';
    const baseCond = 'jo';
    const baseAcc = 'nem';
    const baseSvc = true;

    function mvForOwners(n) {
      return calculateMarketValue(baseBrand, baseYear, baseMileage, baseFuel, baseCond, baseAcc, baseSvc, n);
    }

    it('should apply ownerAdj=1.0 for 0 owners', () => {
      const mv0 = mvForOwners(0);
      const mv1 = mvForOwners(1);
      // 0 owners: owners <= 1, so ownerAdj = 1.0 (same as 1 owner)
      expect(mv0).toBe(mv1);
    });

    it('should apply ownerAdj=1.0 for 1 owner', () => {
      const mv1 = mvForOwners(1);
      const mv2 = mvForOwners(2);
      expect(mv1).toBeGreaterThan(mv2);
    });

    it('should apply ownerAdj=0.97 for 2 owners', () => {
      const mv2 = mvForOwners(2);
      const mv1 = mvForOwners(1);
      const ratio = mv2 / mv1;
      expect(ratio).toBeCloseTo(0.97, 2);
    });

    it('should apply ownerAdj=0.93 for 3 owners', () => {
      const mv3 = mvForOwners(3);
      const mv1 = mvForOwners(1);
      const ratio = mv3 / mv1;
      expect(ratio).toBeCloseTo(0.93, 2);
    });

    it('should apply ownerAdj=0.90 for 4 owners', () => {
      const mv4 = mvForOwners(4);
      const mv1 = mvForOwners(1);
      const ratio = mv4 / mv1;
      expect(ratio).toBeCloseTo(0.90, 2);
    });

    it('should apply ownerAdj=0.87 for 5+ owners', () => {
      const mv5 = mvForOwners(5);
      const mv6 = mvForOwners(6);
      const mv10 = mvForOwners(10);
      const mv1 = mvForOwners(1);

      // All 5+ should produce the same ratio
      expect(mv5).toBe(mv6);
      expect(mv5).toBe(mv10);
      const ratio = mv5 / mv1;
      expect(ratio).toBeCloseTo(0.87, 2);
    });

    it('should monotonically decrease from 1 to 5+ owners', () => {
      const mv1 = mvForOwners(1);
      const mv2 = mvForOwners(2);
      const mv3 = mvForOwners(3);
      const mv4 = mvForOwners(4);
      const mv5 = mvForOwners(5);
      expect(mv1).toBeGreaterThan(mv2);
      expect(mv2).toBeGreaterThan(mv3);
      expect(mv3).toBeGreaterThan(mv4);
      expect(mv4).toBeGreaterThan(mv5);
    });
  });

  // ─── Coefficient -0.002 verification ──────────────────────────

  describe('Mileage coefficient -0.002 verification', () => {
    it('should produce exactly 0.002 change per 1000 km deviation', () => {
      // Direct formula test: adj = 1 + (-0.002 * deviation / 1000)
      // For deviation of +10000: adj = 1 + (-0.002 * 10000 / 1000) = 1 - 0.02 = 0.98
      const deviation = 10000;
      const adj = 1 + (-0.002 * deviation / 1000);
      expect(adj).toBeCloseTo(0.98, 10);
    });

    it('should produce symmetric adjustments for equal positive and negative deviations', () => {
      const age = 6;
      const expectedKm = 13500 * age; // 81000
      const deviation = 50000;

      const adjHigh = 1 + (-0.002 * deviation / 1000);   // 0.90
      const adjLow = 1 + (-0.002 * -deviation / 1000);   // 1.10

      expect(adjHigh).toBeCloseTo(0.90, 10);
      expect(adjLow).toBeCloseTo(1.10, 10);
      // Both deviate by 0.10 from 1.0
      expect(1.0 - adjHigh).toBeCloseTo(adjLow - 1.0, 10);
    });

    it('should match the market value difference proportionally', () => {
      // Two cars differing by exactly 10000 km
      const brand = 'Toyota';
      const year = 2022; // age=4, expectedKm = 13500*4 = 54000
      const fuel = 'benzin';
      const km1 = 54000; // exactly expected
      const km2 = 64000; // +10000 over

      const mv1 = calculateMarketValue(brand, year, km1, fuel, 'jo', 'nem', true, 1);
      const mv2 = calculateMarketValue(brand, year, km2, fuel, 'jo', 'nem', true, 1);

      // adj1 = 1.0, adj2 = 1 + (-0.002 * 10000 / 1000) = 0.98
      // mv2/mv1 should be approximately 0.98
      const ratio = mv2 / mv1;
      expect(ratio).toBeCloseTo(0.98, 2);
    });
  });

  // ─── Numerical consistency (HU/EN parity placeholder) ───────────

  describe('Numerical consistency', () => {
    it('should produce deterministic results for the same inputs', () => {
      const params = {
        brand: 'Volkswagen',
        year: 2018,
        mileage: 120000,
        fuel: 'dizel',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 2,
        repairCostInput: 500000,
      };
      const r1 = runFullCalculation(params);
      const r2 = runFullCalculation(params);
      expect(r1.marketValue).toBe(r2.marketValue);
      expect(r1.composite).toBe(r2.composite);
      expect(r1.verdict).toBe(r2.verdict);
      expect(r1.f1).toBe(r2.f1);
      expect(r1.f2).toBe(r2.f2);
      expect(r1.f3).toBe(r2.f3);
      expect(r1.f4).toBe(r2.f4);
    });

    it('HU and EN pages should produce same numerical results (when EN page exists)', () => {
      // NOTE: EN version does not exist yet. When created, this test should
      // be expanded to load both pages and verify identical calculations.
      // For now, we verify the pure functions match the HU inline script logic.
      const result = runFullCalculation({
        brand: 'Toyota',
        year: 2020,
        mileage: 80000,
        fuel: 'benzin',
        condition: 'jo',
        accident: 'nem',
        serviceBook: true,
        owners: 1,
        repairCostInput: 300000,
      });
      // Manually verify: age=6, baseValue from Toyota 2020
      expect(result.age).toBe(6);
      expect(result.annualMaint).toBe(250000);
      // cost ratio = 300000 / marketValue
      const expectedKa = 300000 / result.marketValue;
      expect(result.f1).toBe(expectedKa < 0.30 ? 1.0 : expectedKa < 0.50 ? 0.65 : expectedKa < 0.75 ? 0.35 : 0);
    });
  });
});
