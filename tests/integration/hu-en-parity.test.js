import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import * as cheerio from 'cheerio';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * HU <-> EN page parity tests.
 *
 * Goal
 * ----
 * The site ships two language trees (`hu/`, `en/`) that are supposed to be
 * structural mirrors. A drift between them (e.g. a new HU input field without
 * an EN counterpart) is how half the real i18n bugs land in production.
 *
 * Strategy
 * --------
 * 1) Explicit HU->EN mapping table at the top of this file. No guessing by
 *    filename similarity — mistranslations and locale-specific slugs would
 *    trip heuristics. An explicit table is also easy to audit and update.
 * 2) Per pair we compare:
 *      - `<label for>` count
 *      - `name=` attribute count
 *      - `id=` count inside result containers (the `<section id>` nodes
 *        whose id starts with "result" or contains "result")
 *      - Total inline <script> size within 20 % (diacritic overhead is small,
 *        so a big delta means real logic drift.)
 * 3) Any HU file that is NOT in the mapping AND not in the excludes set
 *    fails the test. This forces us to update the table when adding pages.
 *
 * Excludes
 * --------
 * - `.bak`                           (backup copies)
 * - `confirm.html`, `unsubscribe.html`  (single-language operational pages)
 * - `*-internal.html`                 (ops/dev-only pages, not user-facing)
 *
 * Edit the MAPPING below when adding a new bilingual page.
 */

const EXCLUDES = new Set([
  'hu/confirm.html',
  'en/confirm.html',
  // unsubscribe.html lives at root, not under hu/ or en/
]);

/**
 * Explicit HU -> EN file mapping.
 * Key = HU path relative to ROOT. Value = EN path relative to ROOT.
 * Keep this alphabetically sorted for diff-friendliness.
 */
const MAPPING = Object.freeze({
  // Landing
  'hu/index.html': 'en/index.html',

  // Blog index
  'hu/blog/index.html': 'en/blog/index.html',

  // Blog articles
  'hu/blog/ai-diagnosztika-hogyan-mukodik.html':
    'en/blog/how-ai-car-diagnostics-works.html',
  'hu/blog/akkumulator-5-figyelmezteto-jel.html':
    'en/blog/5-signs-car-battery-dying.html',
  'hu/blog/autodiagnosztika-otthon-kezdoknek.html':
    'en/blog/car-diagnostics-at-home-beginners-guide.html',
  'hu/blog/dtc-hibakod-kereso-teljes-utmutato.html':
    'en/blog/dtc-trouble-code-lookup-guide.html',
  'hu/blog/p0171-hibakod-okok-tunetek-javitas.html':
    'en/blog/p0171-dtc-code-causes-symptoms-cost.html',
  'hu/blog/p0420-hibakod-utmutato.html':
    'en/blog/p0420-dtc-code-complete-guide.html',

  // Tools
  'hu/eszkozok/index.html': 'en/tools/index.html',
  'hu/eszkozok/megeri-megjavitani.html': 'en/tools/worth-repairing.html',
  'hu/eszkozok/muszaki-vizsga-prediktor.html': 'en/tools/mot-predictor.html',
  'hu/eszkozok/szerviz-kereso.html': 'en/tools/workshop-finder.html',

  // Legal
  'hu/legal/adatvedelmi-szabalyzat.html': 'en/legal/privacy-policy.html',
  'hu/legal/ai-felelossegi-nyilatkozat.html': 'en/legal/ai-disclaimer.html',
  'hu/legal/cookie-szabalyzat.html': 'en/legal/cookie-policy.html',
  'hu/legal/felhasznalasi-feltetelek.html': 'en/legal/terms-of-service.html',
});

/**
 * Tool-page pairs where deep structural parity (label/name/id counts)
 * matters — forms must match 1:1. Other pairs are checked for existence +
 * inline-script-size parity only (blog articles diverge in structure by design).
 */
const TOOL_PAIRS = [
  'hu/eszkozok/megeri-megjavitani.html',
  'hu/eszkozok/muszaki-vizsga-prediktor.html',
  'hu/eszkozok/szerviz-kereso.html',
];

// --- Helpers ---------------------------------------------------------------

function readHtml(relPath) {
  return fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
}

function countAttrs($) {
  return {
    labelsFor: $('label[for]').length,
    names: $('[name]').length,
    // id=... anywhere inside <section> or <div> whose id mentions "result"
    resultIds: $('[id*="result" i] [id]').length,
  };
}

function totalInlineScriptBytes($) {
  let total = 0;
  $('script:not([src])').each((_, el) => {
    total += $(el).html()?.length ?? 0;
  });
  return total;
}

function withinPct(a, b, pct) {
  if (a === 0 && b === 0) return true;
  const max = Math.max(a, b);
  const min = Math.min(a, b);
  return max === 0 ? true : (max - min) / max <= pct;
}

// --- Tests ------------------------------------------------------------------

describe('HU <-> EN parity — mapping completeness', () => {
  test('every HU html file is either mapped to an EN sibling or in the excludes set', async () => {
    const huFiles = await glob('hu/**/*.html', { cwd: ROOT, ignore: ['**/*.bak'] });
    const missing = [];

    for (const hu of huFiles) {
      if (EXCLUDES.has(hu)) continue;
      if (!(hu in MAPPING)) {
        missing.push(hu);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `HU files without EN mapping (update MAPPING or EXCLUDES in tests/integration/hu-en-parity.test.js):\n` +
          missing.map((m) => `  ${m}`).join('\n')
      );
    }
    expect(missing).toHaveLength(0);
  });

  test('every mapped EN file actually exists on disk', () => {
    const missing = [];
    for (const [hu, en] of Object.entries(MAPPING)) {
      if (!fs.existsSync(path.join(ROOT, en))) {
        missing.push(`${hu} -> ${en}`);
      }
    }
    if (missing.length > 0) {
      throw new Error(`EN targets missing on disk:\n${missing.map((m) => `  ${m}`).join('\n')}`);
    }
    expect(missing).toHaveLength(0);
  });

  test('every EN html file is the target of exactly one HU mapping (no orphans)', async () => {
    const enFiles = await glob('en/**/*.html', { cwd: ROOT, ignore: ['**/*.bak'] });
    const mapped = new Set(Object.values(MAPPING));
    const orphans = enFiles.filter((en) => !EXCLUDES.has(en) && !mapped.has(en));
    if (orphans.length > 0) {
      throw new Error(
        `EN files not referenced by any HU mapping:\n${orphans.map((o) => `  ${o}`).join('\n')}`
      );
    }
    expect(orphans).toHaveLength(0);
  });
});

describe('HU <-> EN parity — tool form structure', () => {
  test.each(TOOL_PAIRS)('tool pair has matching <label for>, name, and result-ids: %s', (huPath) => {
    const enPath = MAPPING[huPath];
    expect(enPath, `No EN mapping for ${huPath}`).toBeTruthy();

    const $hu = cheerio.load(readHtml(huPath));
    const $en = cheerio.load(readHtml(enPath));

    const hu = countAttrs($hu);
    const en = countAttrs($en);

    expect(hu.labelsFor, `<label for> count mismatch: HU=${hu.labelsFor} EN=${en.labelsFor}`).toBe(
      en.labelsFor
    );
    expect(hu.names, `name= count mismatch: HU=${hu.names} EN=${en.names}`).toBe(en.names);
    expect(
      hu.resultIds,
      `result-container inner id count mismatch: HU=${hu.resultIds} EN=${en.resultIds}`
    ).toBe(en.resultIds);
  });
});

describe('HU <-> EN parity — inline script size drift', () => {
  // 20 % tolerance: English is usually 10-15 % shorter than Hungarian in prose,
  // but inline scripts are mostly code. Anything beyond 20 % means real logic drift.
  const TOLERANCE = 0.20;

  test.each(Object.entries(MAPPING))(
    'inline script bytes within %s%% between HU/EN: %s',
    (huPath, enPath) => {
      const $hu = cheerio.load(readHtml(huPath));
      const $en = cheerio.load(readHtml(enPath));

      const huBytes = totalInlineScriptBytes($hu);
      const enBytes = totalInlineScriptBytes($en);

      // Pages without inline scripts (legal/blog) are trivially equal.
      if (huBytes === 0 && enBytes === 0) {
        expect(true).toBe(true);
        return;
      }

      const within = withinPct(huBytes, enBytes, TOLERANCE);
      if (!within) {
        const pct = Math.abs(huBytes - enBytes) / Math.max(huBytes, enBytes);
        throw new Error(
          `Inline-script drift > ${TOLERANCE * 100}% between ${huPath} (${huBytes} B) ` +
            `and ${enPath} (${enBytes} B). Actual drift: ${(pct * 100).toFixed(1)}%.`
        );
      }
      expect(within).toBe(true);
    }
  );
});
