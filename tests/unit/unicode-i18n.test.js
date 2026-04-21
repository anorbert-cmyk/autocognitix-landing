import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { createEnvironment, getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Unicode / i18n integrity tests.
 *
 * These guard against three real, previously-observed failure modes:
 *   1. escapeHTML() mangling Hungarian diacritics (á, é, ő, ű, ...)
 *   2. populateSelect() losing diacritics when written to DOM
 *   3. UTF-8 BOM bytes accidentally prepended to HU pages by Windows tooling —
 *      these corrupt the first character and break <!DOCTYPE> detection.
 */

let window;
let ToolCommon;
let VehicleDB;

beforeAll(() => {
  const env = createEnvironment();
  window = env.window;
  ToolCommon = env.ToolCommon;
  VehicleDB = env.VehicleDB;
});

describe('escapeHTML preserves non-ASCII characters', () => {
  it.each([
    ['<á>', '&lt;á&gt;'],
    ['árvíztűrő tükörfúrógép', 'árvíztűrő tükörfúrógép'],
    ['<script>alert("ő")</script>', '&lt;script&gt;alert(&quot;ő&quot;)&lt;/script&gt;'],
    ['& ő & ű & ', '&amp; ő &amp; ű &amp; '],
  ])('escapeHTML(%o) === %o', (input, expected) => {
    expect(ToolCommon.escapeHTML(input)).toBe(expected);
  });

  it('does not strip diacritics from pure prose', () => {
    const input = 'Vissza az előző oldalra — összehasonlítás';
    expect(ToolCommon.escapeHTML(input)).toBe(input);
  });

  it('handles null/undefined/non-string inputs without throwing', () => {
    // Contract check: if escapeHTML crashes on non-strings, it will break
    // every render that passes through a nullable field.
    expect(() => ToolCommon.escapeHTML(null)).not.toThrow();
    expect(() => ToolCommon.escapeHTML(undefined)).not.toThrow();
    expect(() => ToolCommon.escapeHTML(42)).not.toThrow();
  });
});

describe('populateSelect preserves Hungarian diacritics', () => {
  it('writes option.value and option.textContent with exact diacritics', () => {
    const sel = window.document.createElement('select');
    const opts = [
      { id: 'erkölcs', label: 'Érték' },
      { id: 'új', label: 'Új' },
      { id: 'régi', label: 'Régi' },
    ];
    ToolCommon.populateSelect(sel, opts, 'Válassz...');

    // First option is the placeholder.
    const options = Array.from(sel.querySelectorAll('option'));
    const placeholder = options[0];
    expect(placeholder.textContent).toBe('Válassz...');
    expect(placeholder.disabled).toBe(true);

    const rest = options.slice(1);
    expect(rest.map((o) => o.value)).toEqual(['erkölcs', 'új', 'régi']);
    expect(rest.map((o) => o.textContent)).toEqual(['Érték', 'Új', 'Régi']);
  });

  it('preserves diacritics when options are plain strings', () => {
    const sel = window.document.createElement('select');
    ToolCommon.populateSelect(sel, ['Opel', 'Škoda', 'Citroën']);
    const values = Array.from(sel.querySelectorAll('option')).map((o) => o.value);
    expect(values).toEqual(['Opel', 'Škoda', 'Citroën']);
  });
});

describe('HU pages do not start with UTF-8 BOM', () => {
  // BOM = EF BB BF (3 bytes). When present at the start of an HTML file it
  // prevents browsers from recognizing <!DOCTYPE html> as the first token
  // and flips them into quirks mode. This breaks CSS layout subtly.
  const BOM = Buffer.from([0xef, 0xbb, 0xbf]);

  it('no HTML file under hu/ begins with the UTF-8 BOM', async () => {
    const files = await glob('hu/**/*.html', { cwd: ROOT });
    const withBom = [];
    for (const rel of files) {
      const buf = fs.readFileSync(path.join(ROOT, rel));
      if (buf.length >= 3 && buf.subarray(0, 3).equals(BOM)) {
        withBom.push(rel);
      }
    }
    if (withBom.length > 0) {
      throw new Error(`Files starting with UTF-8 BOM:\n${withBom.map((f) => `  ${f}`).join('\n')}`);
    }
    expect(withBom).toHaveLength(0);
  });

  it('no HTML file under en/ begins with the UTF-8 BOM', async () => {
    const files = await glob('en/**/*.html', { cwd: ROOT });
    const withBom = [];
    for (const rel of files) {
      const buf = fs.readFileSync(path.join(ROOT, rel));
      if (buf.length >= 3 && buf.subarray(0, 3).equals(BOM)) {
        withBom.push(rel);
      }
    }
    if (withBom.length > 0) {
      throw new Error(`Files starting with UTF-8 BOM:\n${withBom.map((f) => `  ${f}`).join('\n')}`);
    }
    expect(withBom).toHaveLength(0);
  });
});

describe('VehicleDB contains Hungarian-market brands without mojibake', () => {
  it('every brand label is a valid UTF-8 string with no replacement chars', () => {
    const REPLACEMENT = '\uFFFD';
    const offenders = [];
    for (const name of Object.keys(VehicleDB.brands)) {
      if (name.includes(REPLACEMENT)) offenders.push(name);
    }
    expect(offenders).toHaveLength(0);
  });
});
