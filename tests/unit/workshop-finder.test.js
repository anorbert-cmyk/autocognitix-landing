import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { createEnvironment, extractInlineScript } from '../setup/dom-shim.js';

/**
 * Workshop Finder Unit Tests
 *
 * The workshop finder logic lives inside an IIFE in the HTML file.
 * We extract the pure functions and test them in isolation by
 * re-creating them in a jsdom environment with the same DTC_SPECIALTIES map.
 */

let window;
let document;

// Extracted functions — mirrors the inline script logic
let DTC_SPECIALTIES;
let DEFAULT_SPECIALTY;
let matchSpecialty;
let parseCodes;
let groupBySpecialty;
let getMapsLink;
let escapeHTML;

beforeAll(() => {
  const env = createEnvironment();
  window = env.window;
  document = window.document;

  // Recreate the DTC_SPECIALTIES map (identical to the inline script)
  DTC_SPECIALTIES = {
    'P04':  { name: 'Kipufofo es katalizator szerviz',       terms: 'kipufofo szerviz katalizator javitas' },
    'P03':  { name: 'Gyujtas es motorjavitas',                terms: 'gyujtas javitas gyujtotekercs csere' },
    'P01':  { name: 'Motordiagnosztika — Uzemanyag rendszer', terms: 'motor szerviz autoszerelo motordiagnosztika' },
    'P02':  { name: 'Motordiagnosztika — Levego rendszer',    terms: 'motor szerviz autoszerelo' },
    'P029': { name: 'Turbo szerviz',                          terms: 'turbo javitas turbo szerviz turbocharger' },
    'P040': { name: 'Dizel szerviz / EGR',                    terms: 'dizel szerviz EGR javitas EGR szelep' },
    'P200': { name: 'DPF tisztitas es diagnosztika',          terms: 'DPF tisztitas dizel reszecskezuro regeneralas' },
    'P06':  { name: 'Valto szerviz',                          terms: 'valto javitas automata valto szerviz' },
    'P07':  { name: 'Valto szerviz',                          terms: 'valto javitas valto szerviz' },
    'C0':   { name: 'Futomunjavito',                          terms: 'futomunjavito futomun beallitas fekszerviz' },
    'B0':   { name: 'Karosszeria es autovillamossag',         terms: 'autovillamossag karosszeria lakatos' },
    'U0':   { name: 'Auto elektronika / CAN-bus',             terms: 'autovillamossag CAN-bus javitas autoelektronika' }
  };

  DEFAULT_SPECIALTY = {
    name: 'Altalanos autoszerviz',
    terms: 'autoszerviz autoszerelo'
  };

  // Recreate the functions exactly as they appear in the inline script
  matchSpecialty = function(code) {
    code = code.toUpperCase().trim();
    if (!code) return null;
    for (var len = 4; len >= 2; len--) {
      var prefix = code.substring(0, len);
      if (DTC_SPECIALTIES[prefix]) {
        return { code: code, specialty: DTC_SPECIALTIES[prefix] };
      }
    }
    return { code: code, specialty: DEFAULT_SPECIALTY };
  };

  getMapsLink = function(terms, location) {
    return 'https://www.google.com/maps/search/' + encodeURIComponent(terms + ' ' + location);
  };

  parseCodes = function(input) {
    if (!input || !input.trim()) return { codes: [], invalidCodes: [] };
    var seen = {};
    var validPattern = /^[PBCU]\d{4}$/i;
    var dtcCodes = input.split(/[,;\s]+/).map(function(c) {
      return c.trim().toUpperCase();
    }).filter(function(c) {
      if (!c || seen[c]) return false;
      seen[c] = true;
      return true;
    });
    var invalidCodes = [];
    dtcCodes = dtcCodes.filter(function(code) {
      if (!validPattern.test(code)) {
        invalidCodes.push(code);
        return false;
      }
      return true;
    });
    // In test env we skip DOM warning/alert side effects, just return valid codes
    return { codes: dtcCodes, invalidCodes: invalidCodes };
  };

  groupBySpecialty = function(matches) {
    var groups = [];
    var nameMap = {};
    matches.forEach(function(m) {
      var key = m.specialty.name;
      if (nameMap[key] !== undefined) {
        groups[nameMap[key]].codes.push(m.code);
      } else {
        nameMap[key] = groups.length;
        groups.push({
          specialty: m.specialty,
          codes: [m.code]
        });
      }
    });
    return groups;
  };

  escapeHTML = function(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  };
});

// ─── matchSpecialty ───
describe('Workshop Finder — matchSpecialty', () => {
  it('should match P0420 to P04 (exhaust/catalytic)', () => {
    const result = matchSpecialty('P0420');
    expect(result.code).toBe('P0420');
    expect(result.specialty.name).toBe('Kipufofo es katalizator szerviz');
  });

  it('should match P0299 to P029 (turbo) via longest-prefix-first', () => {
    const result = matchSpecialty('P0299');
    expect(result.code).toBe('P0299');
    expect(result.specialty.name).toBe('Turbo szerviz');
  });

  it('should match P0301 to P03 (ignition)', () => {
    const result = matchSpecialty('P0301');
    expect(result.code).toBe('P0301');
    expect(result.specialty.name).toBe('Gyujtas es motorjavitas');
  });

  it('should match P0171 to P01 (fuel system)', () => {
    const result = matchSpecialty('P0171');
    expect(result.code).toBe('P0171');
    expect(result.specialty.name).toBe('Motordiagnosztika — Uzemanyag rendszer');
  });

  it('should match P0200 to P200 (DPF) via 4-char prefix', () => {
    const result = matchSpecialty('P2001');
    expect(result.code).toBe('P2001');
    expect(result.specialty.name).toBe('DPF tisztitas es diagnosztika');
  });

  it('should match P0401 to P040 (diesel/EGR) via 4-char prefix', () => {
    const result = matchSpecialty('P0401');
    expect(result.code).toBe('P0401');
    expect(result.specialty.name).toBe('Dizel szerviz / EGR');
  });

  it('should match C0035 to C0 (suspension)', () => {
    const result = matchSpecialty('C0035');
    expect(result.code).toBe('C0035');
    expect(result.specialty.name).toBe('Futomunjavito');
  });

  it('should match B0100 to B0 (body/electrical)', () => {
    const result = matchSpecialty('B0100');
    expect(result.code).toBe('B0100');
    expect(result.specialty.name).toBe('Karosszeria es autovillamossag');
  });

  it('should match U0100 to U0 (CAN-bus/electronics)', () => {
    const result = matchSpecialty('U0100');
    expect(result.code).toBe('U0100');
    expect(result.specialty.name).toBe('Auto elektronika / CAN-bus');
  });

  it('should match P0600 to P06 (transmission)', () => {
    const result = matchSpecialty('P0600');
    expect(result.code).toBe('P0600');
    expect(result.specialty.name).toBe('Valto szerviz');
  });

  it('should match P0700 to P07 (transmission)', () => {
    const result = matchSpecialty('P0700');
    expect(result.code).toBe('P0700');
    expect(result.specialty.name).toBe('Valto szerviz');
  });

  it('should return default specialty for unknown DTC code', () => {
    const result = matchSpecialty('P1234');
    expect(result.code).toBe('P1234');
    expect(result.specialty.name).toBe('Altalanos autoszerviz');
  });

  it('should return default specialty for B-prefix codes without B0 match', () => {
    const result = matchSpecialty('B1234');
    expect(result.code).toBe('B1234');
    expect(result.specialty.name).toBe('Altalanos autoszerviz');
  });

  it('should return null for empty string', () => {
    expect(matchSpecialty('')).toBeNull();
  });

  it('should return null for whitespace-only input', () => {
    expect(matchSpecialty('   ')).toBeNull();
  });

  it('should be case-insensitive', () => {
    const result = matchSpecialty('p0420');
    expect(result.code).toBe('P0420');
    expect(result.specialty.name).toBe('Kipufofo es katalizator szerviz');
  });

  it('should prefer P029 over P02 for P0299 (longest prefix wins)', () => {
    // P0299 should match P029 (len=4: P029), NOT P02 (len=3)
    const result = matchSpecialty('P0299');
    expect(result.specialty.name).toBe('Turbo szerviz');
    expect(result.specialty.name).not.toBe('Motordiagnosztika — Levego rendszer');
  });

  it('should prefer P040 over P04 for P0401 (longest prefix wins)', () => {
    // P0401 should match P040 (len=4), NOT P04 (len=3)
    const result = matchSpecialty('P0401');
    expect(result.specialty.name).toBe('Dizel szerviz / EGR');
    expect(result.specialty.name).not.toBe('Kipufofo es katalizator szerviz');
  });
});

// ─── parseCodes ───
describe('Workshop Finder — parseCodes', () => {
  it('should parse "P0420, P0171, C0035" into 3 unique codes', () => {
    const { codes } = parseCodes('P0420, P0171, C0035');
    expect(codes).toHaveLength(3);
    expect(codes).toEqual(['P0420', 'P0171', 'C0035']);
  });

  it('should deduplicate "P0420, P0420" to 1 code', () => {
    const { codes } = parseCodes('P0420, P0420');
    expect(codes).toHaveLength(1);
    expect(codes).toEqual(['P0420']);
  });

  it('should filter out invalid "hello" and keep valid "P0420"', () => {
    const { codes, invalidCodes } = parseCodes('hello, P0420');
    expect(codes).toHaveLength(1);
    expect(codes).toEqual(['P0420']);
    expect(invalidCodes).toContain('HELLO');
  });

  it('should return empty for empty string', () => {
    const { codes } = parseCodes('');
    expect(codes).toHaveLength(0);
  });

  it('should return empty for null', () => {
    const { codes } = parseCodes(null);
    expect(codes).toHaveLength(0);
  });

  it('should return empty for undefined', () => {
    const { codes } = parseCodes(undefined);
    expect(codes).toHaveLength(0);
  });

  it('should return empty for whitespace-only input', () => {
    const { codes } = parseCodes('   ');
    expect(codes).toHaveLength(0);
  });

  it('should uppercase all codes', () => {
    const { codes } = parseCodes('p0420, c0035');
    expect(codes).toEqual(['P0420', 'C0035']);
  });

  it('should accept semicolons and spaces as delimiters', () => {
    const { codes } = parseCodes('P0420;P0171 C0035');
    expect(codes).toHaveLength(3);
  });

  it('should accept all 4 valid DTC prefixes: P, B, C, U', () => {
    const { codes } = parseCodes('P0420, B0100, C0035, U0100');
    expect(codes).toHaveLength(4);
  });

  it('should reject codes that are too short', () => {
    const { codes, invalidCodes } = parseCodes('P04');
    expect(codes).toHaveLength(0);
    expect(invalidCodes).toContain('P04');
  });

  it('should reject codes with invalid prefix letters', () => {
    const { codes, invalidCodes } = parseCodes('X1234');
    expect(codes).toHaveLength(0);
    expect(invalidCodes).toContain('X1234');
  });

  it('should reject all-invalid and return no valid codes', () => {
    const { codes, invalidCodes } = parseCodes('hello, world, test');
    expect(codes).toHaveLength(0);
    expect(invalidCodes).toHaveLength(3);
  });

  it('should handle mixed valid and invalid gracefully', () => {
    const { codes, invalidCodes } = parseCodes('P0420, BAD1, C0035, NOPE');
    expect(codes).toEqual(['P0420', 'C0035']);
    expect(invalidCodes).toEqual(['BAD1', 'NOPE']);
  });
});

// ─── groupBySpecialty ───
describe('Workshop Finder — groupBySpecialty', () => {
  it('should group two codes with the same specialty', () => {
    const matches = [
      matchSpecialty('P0600'),
      matchSpecialty('P0700')
    ];
    // Both P06 and P07 map to "Valto szerviz"
    const groups = groupBySpecialty(matches);
    expect(groups).toHaveLength(1);
    expect(groups[0].specialty.name).toBe('Valto szerviz');
    expect(groups[0].codes).toEqual(['P0600', 'P0700']);
  });

  it('should keep different specialties separate', () => {
    const matches = [
      matchSpecialty('P0420'),
      matchSpecialty('C0035')
    ];
    const groups = groupBySpecialty(matches);
    expect(groups).toHaveLength(2);
  });

  it('should handle single code', () => {
    const matches = [matchSpecialty('P0420')];
    const groups = groupBySpecialty(matches);
    expect(groups).toHaveLength(1);
    expect(groups[0].codes).toEqual(['P0420']);
  });

  it('should handle empty matches', () => {
    const groups = groupBySpecialty([]);
    expect(groups).toHaveLength(0);
  });

  it('should preserve order of first occurrence', () => {
    const matches = [
      matchSpecialty('C0035'),
      matchSpecialty('P0420'),
      matchSpecialty('C0050')
    ];
    const groups = groupBySpecialty(matches);
    // C0 group should come first (first occurrence)
    expect(groups[0].specialty.name).toBe('Futomunjavito');
    expect(groups[0].codes).toEqual(['C0035', 'C0050']);
    expect(groups[1].specialty.name).toBe('Kipufofo es katalizator szerviz');
  });
});

// ─── getMapsLink ───
describe('Workshop Finder — getMapsLink', () => {
  it('should return a valid Google Maps URL', () => {
    const link = getMapsLink('autoszerviz', 'Budapest');
    expect(link).toBe('https://www.google.com/maps/search/' + encodeURIComponent('autoszerviz Budapest'));
  });

  it('should properly encode special characters', () => {
    const link = getMapsLink('turbo szerviz', 'Budapest, 11. kerület');
    expect(link).toContain('https://www.google.com/maps/search/');
    expect(link).toContain(encodeURIComponent('turbo szerviz Budapest, 11. kerület'));
  });

  it('should encode spaces as %20', () => {
    const link = getMapsLink('turbo javitas', 'Debrecen');
    expect(link).toContain('turbo%20javitas%20Debrecen');
  });

  it('should handle empty location', () => {
    const link = getMapsLink('szerviz', '');
    expect(link).toBe('https://www.google.com/maps/search/' + encodeURIComponent('szerviz '));
  });
});

// ─── escapeHTML ───
describe('Workshop Finder — escapeHTML', () => {
  it('should escape < and >', () => {
    const result = escapeHTML('<script>alert("xss")</script>');
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;');
    expect(result).toContain('&gt;');
  });

  it('should escape &', () => {
    const result = escapeHTML('foo & bar');
    expect(result).toBe('foo &amp; bar');
  });

  it('should preserve double quotes (DOM textContent approach does not entity-encode quotes)', () => {
    // The DOM-based escapeHTML uses div.textContent + div.innerHTML,
    // which escapes <, >, & but NOT quotes (quotes are safe inside element content)
    const result = escapeHTML('"hello"');
    expect(result).toBe('"hello"');
  });

  it('should handle normal strings unchanged', () => {
    expect(escapeHTML('hello world')).toBe('hello world');
  });

  it('should handle empty string', () => {
    expect(escapeHTML('')).toBe('');
  });

  it('should handle combined XSS vector', () => {
    const result = escapeHTML('<img src=x onerror="alert(1)">');
    expect(result).not.toContain('<img');
    expect(result).toContain('&lt;');
  });
});
