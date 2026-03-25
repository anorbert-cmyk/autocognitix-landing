import { describe, it, expect, beforeAll } from 'vitest';
import { createEnvironment } from '../setup/dom-shim.js';

let ToolCommon;
let window;
let document;

beforeAll(() => {
  const env = createEnvironment();
  ToolCommon = env.ToolCommon;
  window = env.window;
  document = window.document;
});

describe('ToolCommon', () => {
  describe('validateDTC(code)', () => {
    it('should accept valid DTC codes', () => {
      const validCodes = ['P0420', 'B0100', 'C0035', 'U0100'];
      validCodes.forEach((code) => {
        const result = ToolCommon.validateDTC(code);
        expect(result.valid, `${code} should be valid`).toBe(true);
        expect(result.code).toBe(code);
      });
    });

    it('should be case insensitive and normalize to uppercase', () => {
      const result = ToolCommon.validateDTC('p0420');
      expect(result.valid).toBe(true);
      expect(result.code).toBe('P0420');

      const result2 = ToolCommon.validateDTC('b0100');
      expect(result2.valid).toBe(true);
      expect(result2.code).toBe('B0100');
    });

    it('should reject invalid codes', () => {
      expect(ToolCommon.validateDTC('hello').valid).toBe(false);
      expect(ToolCommon.validateDTC('X1234').valid).toBe(false);
      expect(ToolCommon.validateDTC('P04').valid).toBe(false);
    });

    it('should reject empty and null input', () => {
      expect(ToolCommon.validateDTC('').valid).toBe(false);
      expect(ToolCommon.validateDTC(null).valid).toBe(false);
      expect(ToolCommon.validateDTC(undefined).valid).toBe(false);
    });

    it('should include a warning message on invalid input', () => {
      const result = ToolCommon.validateDTC('hello');
      expect(result.warning).toBeTruthy();
      expect(typeof result.warning).toBe('string');
    });
  });

  describe('detectOdometerAnomaly(km, year)', () => {
    // Note: the function uses new Date().getFullYear() internally.
    // In 2026, age of a 2020 car = 6 years, 500000/6 = 83333 km/year => high.
    it('should flag 500k km on a 2020 car as high anomaly', () => {
      const result = ToolCommon.detectOdometerAnomaly(500000, 2020);
      expect(result).not.toBeNull();
      expect(result.level).toBe('high');
    });

    it('should flag 0 km on a 2010 car as high anomaly', () => {
      const result = ToolCommon.detectOdometerAnomaly(0, 2010);
      expect(result).not.toBeNull();
      expect(result.level).toBe('high');
    });

    it('should return null for normal mileage (~15k km/year)', () => {
      const currentYear = new Date().getFullYear();
      const age = 5;
      const year = currentYear - age;
      const km = 15000 * age; // 75000 km in 5 years
      const result = ToolCommon.detectOdometerAnomaly(km, year);
      expect(result).toBeNull();
    });

    it('should return null when age is 0 (current year car)', () => {
      const currentYear = new Date().getFullYear();
      const result = ToolCommon.detectOdometerAnomaly(50000, currentYear);
      expect(result).toBeNull();
    });

    it('should flag medium anomaly for above-average mileage (>25k km/year)', () => {
      const currentYear = new Date().getFullYear();
      const year = currentYear - 5;
      const km = 30000 * 5; // 150000 km, 30k/year
      const result = ToolCommon.detectOdometerAnomaly(km, year);
      expect(result).not.toBeNull();
      expect(result.level).toBe('medium');
    });

    it('should flag medium for suspiciously low mileage on old cars', () => {
      const currentYear = new Date().getFullYear();
      const year = currentYear - 10;
      const km = 5000; // 500 km/year over 10 years
      const result = ToolCommon.detectOdometerAnomaly(km, year);
      expect(result).not.toBeNull();
      expect(result.level).toBe('medium');
    });
  });

  describe('validateNumericRange(value, min, max, fieldName)', () => {
    it('should accept value within range', () => {
      const result = ToolCommon.validateNumericRange(50, 0, 100, 'Kor');
      expect(result.valid).toBe(true);
      expect(result.value).toBe(50);
    });

    it('should reject value below min', () => {
      const result = ToolCommon.validateNumericRange(-5, 0, 100, 'Kor');
      expect(result.valid).toBe(false);
      expect(result.message).toContain('Kor');
    });

    it('should reject value above max', () => {
      const result = ToolCommon.validateNumericRange(150, 0, 100, 'Kor');
      expect(result.valid).toBe(false);
      expect(result.message).toContain('Kor');
    });

    it('should reject NaN input', () => {
      const result = ToolCommon.validateNumericRange('abc', 0, 100, 'Kor');
      expect(result.valid).toBe(false);
      expect(result.message).toContain('Kor');
    });

    it('should allow any value above min when max is null', () => {
      const result = ToolCommon.validateNumericRange(999999, 0, null, 'Km');
      expect(result.valid).toBe(true);
      expect(result.value).toBe(999999);
    });

    it('should accept boundary values (min and max)', () => {
      expect(ToolCommon.validateNumericRange(0, 0, 100, 'Test').valid).toBe(true);
      expect(ToolCommon.validateNumericRange(100, 0, 100, 'Test').valid).toBe(true);
    });
  });

  describe('formatHUF(num)', () => {
    it('should format 5000000 as "5 000 000 Ft"', () => {
      expect(ToolCommon.formatHUF(5000000)).toBe('5 000 000 Ft');
    });

    it('should format 0 as "0 Ft"', () => {
      expect(ToolCommon.formatHUF(0)).toBe('0 Ft');
    });

    it('should round decimals', () => {
      expect(ToolCommon.formatHUF(1234567.89)).toBe('1 234 568 Ft');
    });

    it('should return "-" for null or undefined', () => {
      expect(ToolCommon.formatHUF(null)).toBe('-');
      expect(ToolCommon.formatHUF(undefined)).toBe('-');
    });

    it('should format small numbers correctly', () => {
      expect(ToolCommon.formatHUF(500)).toBe('500 Ft');
      expect(ToolCommon.formatHUF(1000)).toBe('1 000 Ft');
    });
  });

  describe('escapeHTML(str)', () => {
    it('should escape < and >', () => {
      expect(ToolCommon.escapeHTML('<script>')).toBe('&lt;script&gt;');
    });

    it('should escape &', () => {
      expect(ToolCommon.escapeHTML('foo & bar')).toBe('foo &amp; bar');
    });

    it('should escape double quotes', () => {
      expect(ToolCommon.escapeHTML('"hello"')).toBe('&quot;hello&quot;');
    });

    it('should escape single quotes', () => {
      expect(ToolCommon.escapeHTML("it's")).toBe("it&#039;s");
    });

    it('should return empty string for empty input', () => {
      expect(ToolCommon.escapeHTML('')).toBe('');
    });

    it('should return empty string for null/undefined', () => {
      expect(ToolCommon.escapeHTML(null)).toBe('');
      expect(ToolCommon.escapeHTML(undefined)).toBe('');
    });

    it('should handle combined special characters', () => {
      expect(ToolCommon.escapeHTML('<a href="x">&')).toBe('&lt;a href=&quot;x&quot;&gt;&amp;');
    });
  });

  describe('populateSelect(selectEl, options, placeholder)', () => {
    it('should create option elements from string array', () => {
      const select = document.createElement('select');
      ToolCommon.populateSelect(select, ['Audi', 'BMW', 'Fiat']);
      expect(select.children.length).toBe(3);
      expect(select.children[0].value).toBe('Audi');
      expect(select.children[0].textContent).toBe('Audi');
    });

    it('should create option elements from object array', () => {
      const select = document.createElement('select');
      ToolCommon.populateSelect(select, [
        { id: 'a', label: 'Alpha' },
        { id: 'b', label: 'Beta' }
      ]);
      expect(select.children.length).toBe(2);
      expect(select.children[0].value).toBe('a');
      expect(select.children[0].textContent).toBe('Alpha');
    });

    it('should add a disabled placeholder option when specified', () => {
      const select = document.createElement('select');
      ToolCommon.populateSelect(select, ['A', 'B'], 'Choose...');
      expect(select.children.length).toBe(3);
      expect(select.children[0].textContent).toBe('Choose...');
      expect(select.children[0].disabled).toBe(true);
      expect(select.children[0].selected).toBe(true);
    });

    it('should clear existing options before populating', () => {
      const select = document.createElement('select');
      select.innerHTML = '<option>Old</option>';
      ToolCommon.populateSelect(select, ['New']);
      expect(select.children.length).toBe(1);
      expect(select.children[0].textContent).toBe('New');
    });
  });

  describe('selfTest', () => {
    it('should exist and be a function', () => {
      expect(ToolCommon.selfTest).toBeDefined();
      expect(typeof ToolCommon.selfTest).toBe('function');
    });
  });
});
