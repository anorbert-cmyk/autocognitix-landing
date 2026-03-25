import { describe, it, expect, beforeAll } from 'vitest';
import { createEnvironment } from '../setup/dom-shim.js';

let VehicleDB;

beforeAll(() => {
  const env = createEnvironment();
  VehicleDB = env.VehicleDB;
});

describe('VehicleDB', () => {
  describe('brands database', () => {
    const expectedBrands = [
      'Suzuki', 'Opel', 'Volkswagen', 'Skoda', 'Ford', 'Toyota',
      'BMW', 'Audi', 'Mercedes-Benz', 'Renault', 'Peugeot', 'Citroen',
      'Fiat', 'Hyundai', 'Kia', 'Dacia', 'Honda', 'Mazda', 'Nissan',
      'Seat', 'Volvo', 'Mitsubishi', 'Chevrolet', 'Alfa Romeo', 'Lancia'
    ];

    it('should contain exactly 25 brands', () => {
      expect(Object.keys(VehicleDB.brands)).toHaveLength(25);
    });

    it.each(expectedBrands)('should contain brand: %s', (brand) => {
      expect(VehicleDB.brands[brand]).toBeDefined();
    });

    it('should have models, segment, and avgMsrp for every brand', () => {
      Object.entries(VehicleDB.brands).forEach(([name, data]) => {
        expect(Array.isArray(data.models) || data.models.length !== undefined, `${name} missing models`).toBe(true);
        expect(data.models.length, `${name} has no models`).toBeGreaterThan(0);
        expect(data.segment, `${name} missing segment`).toBeTruthy();
        expect(data.avgMsrp, `${name} missing avgMsrp`).toBeGreaterThan(0);
      });
    });
  });

  describe('getBaseValue(brand, year)', () => {
    it('should return a positive number for every brand at year 2020', () => {
      Object.keys(VehicleDB.brands).forEach((brand) => {
        const value = VehicleDB.getBaseValue(brand, 2020);
        expect(value, `${brand} returned non-positive value`).toBeGreaterThan(0);
      });
    });

    it('should return higher values for newer years (depreciation monotonicity)', () => {
      Object.keys(VehicleDB.brands).forEach((brand) => {
        const years = [2000, 2005, 2010, 2015, 2020, 2025];
        for (let i = 0; i < years.length - 1; i++) {
          const older = VehicleDB.getBaseValue(brand, years[i]);
          const newer = VehicleDB.getBaseValue(brand, years[i + 1]);
          expect(newer, `${brand}: year ${years[i + 1]} should be >= year ${years[i]}`).toBeGreaterThanOrEqual(older);
        }
      });
    });

    it('should never return below msrp * 0.03 (floor value)', () => {
      Object.keys(VehicleDB.brands).forEach((brand) => {
        const msrp = VehicleDB.brands[brand].avgMsrp;
        const floor = Math.round(msrp * 0.03);
        // Test with a very old year to hit the floor
        const value = VehicleDB.getBaseValue(brand, 1990);
        expect(value, `${brand} value below floor`).toBeGreaterThanOrEqual(floor);
      });
    });

    it('should return default 3000000 for unknown brand', () => {
      expect(VehicleDB.getBaseValue('UnknownBrand', 2020)).toBe(3000000);
      expect(VehicleDB.getBaseValue('', 2020)).toBe(3000000);
    });

    it('should return full MSRP for year 2026 (age = 0)', () => {
      Object.keys(VehicleDB.brands).forEach((brand) => {
        const msrp = VehicleDB.brands[brand].avgMsrp;
        expect(VehicleDB.getBaseValue(brand, 2026)).toBe(msrp);
      });
    });

    it('should return floor value for year 1995 (very old car)', () => {
      Object.keys(VehicleDB.brands).forEach((brand) => {
        const msrp = VehicleDB.brands[brand].avgMsrp;
        const floor = Math.round(msrp * 0.03);
        const value = VehicleDB.getBaseValue(brand, 1995);
        expect(value, `${brand} 1995 should be at floor`).toBe(floor);
      });
    });

    it('should return less than MSRP for age=1 (first year depreciation)', () => {
      const value = VehicleDB.getBaseValue('Volkswagen', 2025);
      const msrp = VehicleDB.brands['Volkswagen'].avgMsrp;
      expect(value).toBeLessThan(msrp);
      // 22% first year depreciation
      expect(value).toBe(Math.round(msrp * (1 - 0.22)));
    });
  });

  describe('fuelTypes', () => {
    it('should have exactly 5 fuel types', () => {
      expect(VehicleDB.fuelTypes).toHaveLength(5);
    });

    it('should define all expected fuel types', () => {
      const ids = VehicleDB.fuelTypes.map((f) => f.id);
      expect(ids).toEqual(['benzin', 'dizel', 'lpg', 'hibrid', 'elektromos']);
    });

    it('should have valid expectedKmPerYear for each fuel type', () => {
      VehicleDB.fuelTypes.forEach((ft) => {
        expect(ft.id, 'missing id').toBeTruthy();
        expect(ft.label, 'missing label').toBeTruthy();
        expect(ft.expectedKmPerYear, `${ft.id} has invalid km`).toBeGreaterThan(0);
      });
    });
  });

  describe('conditions', () => {
    it('should have condition multipliers between 0 and 2', () => {
      VehicleDB.conditions.forEach((c) => {
        expect(c.multiplier, `${c.id} multiplier out of range`).toBeGreaterThan(0);
        expect(c.multiplier, `${c.id} multiplier out of range`).toBeLessThan(2);
      });
    });

    it('should have id and label for every condition', () => {
      VehicleDB.conditions.forEach((c) => {
        expect(c.id).toBeTruthy();
        expect(c.label).toBeTruthy();
      });
    });
  });

  describe('accidentSeverity', () => {
    it('should have valid damageMultiplier values between 0 and 1', () => {
      VehicleDB.accidentSeverity.forEach((a) => {
        expect(a.damageMultiplier, `${a.id} damage out of range`).toBeGreaterThanOrEqual(0);
        expect(a.damageMultiplier, `${a.id} damage out of range`).toBeLessThanOrEqual(1);
      });
    });

    it('should have id and label for every severity level', () => {
      VehicleDB.accidentSeverity.forEach((a) => {
        expect(a.id).toBeTruthy();
        expect(a.label).toBeTruthy();
      });
    });

    it('should have "nem" with 0 damage and "szerkezeti" with 1.0 damage', () => {
      const nem = VehicleDB.accidentSeverity.find((a) => a.id === 'nem');
      const szerkezeti = VehicleDB.accidentSeverity.find((a) => a.id === 'szerkezeti');
      expect(nem.damageMultiplier).toBe(0);
      expect(szerkezeti.damageMultiplier).toBe(1.0);
    });
  });

  describe('getExpectedKm(fuelType)', () => {
    it('should return correct km for known fuel types', () => {
      expect(VehicleDB.getExpectedKm('benzin')).toBe(13500);
      expect(VehicleDB.getExpectedKm('dizel')).toBe(20000);
    });

    it('should return 15000 as default for unknown fuel type', () => {
      expect(VehicleDB.getExpectedKm('hydrogen')).toBe(15000);
    });
  });
});
