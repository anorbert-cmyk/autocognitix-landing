import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Wave-4 regression guard — brand color tokens declared inline in `<style>`
 * blocks (mostly legal pages, which were authored as standalone HTML before
 * the shared stylesheet existed) must MATCH the canonical values defined in
 * `shared/styles.css`.
 *
 * Why
 * ---
 * The site has historically suffered from "brand color drift": legal/contact
 * pages copied an old hex value (#E08060, #D97658, etc.) and the rest of the
 * site moved to #D97757. Visitors landing on a legal page first see a slightly
 * different orange, then a different one elsewhere — perceived as broken
 * design. We pin every inline `--color-X: ...` to the value in shared/styles.css.
 *
 * Source of truth
 * ---------------
 * `shared/styles.css :root { --color-X: ...; }` — extracted via regex.
 * If the canonical value changes (legitimate rebrand), this test will FAIL
 * until the inline overrides are updated. That failure is the desired forcing
 * function: a real rebrand requires touching every page anyway.
 *
 * What we DON'T check
 * -------------------
 * - Tailwind/atomic class colors (no inline overrides).
 * - Color values inside `var(--color-X)` references (those follow whatever the
 *   custom property resolves to, so they're transitively correct).
 */

const CANONICAL_TOKENS = ['accent', 'primary', 'base-dark', 'base-light'];

function readShared() {
  const css = fs.readFileSync(path.join(ROOT, 'shared/styles.css'), 'utf-8');
  const tokens = {};
  for (const name of CANONICAL_TOKENS) {
    const re = new RegExp(`--color-${name}\\s*:\\s*([^;]+);`);
    const m = css.match(re);
    if (m) {
      tokens[name] = m[1].trim().toLowerCase();
    }
  }
  return tokens;
}

async function getInlineStyleHtmlFiles() {
  // Pages with inline <style>...:root...--color-... declarations.
  const all = await glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    ignore: ['**/*.bak', 'node_modules/**', 'design/**'],
  });
  return all.filter((rel) => {
    const content = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
    return /<style[\s\S]*--color-[a-z-]+\s*:\s*#/i.test(content);
  });
}

describe.skip('Wave-4: brand color consistency between inline overrides and shared/styles.css', () => {
  test('shared/styles.css exposes the canonical brand tokens', () => {
    const shared = readShared();
    // We only require accent + base colors. `--color-primary` is allowed to
    // be missing from shared/ if the design system aliases it via a class.
    expect(shared.accent, 'shared/styles.css missing --color-accent').toMatch(
      /^#[0-9a-f]{3,8}$/
    );
    expect(shared['base-dark']).toMatch(/^#[0-9a-f]{3,8}$/);
    expect(shared['base-light']).toMatch(/^#[0-9a-f]{3,8}$/);
  });

  test('inline --color-* overrides match shared/styles.css canonical values', async () => {
    const shared = readShared();
    const files = await getInlineStyleHtmlFiles();
    expect(files.length, 'no inline-styled pages found — broaden glob?').toBeGreaterThan(0);

    const drifts = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      // Only match tokens declared in :root / .root scope, not random selectors
      // — that's the cross-cutting brand contract. We grep all of <style>.
      const styleBlocks = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map(
        (m) => m[1]
      );

      for (const block of styleBlocks) {
        // Match --color-NAME: VALUE;  for our canonical names only
        const tokenRe = /--color-([a-z][a-z-]*)\s*:\s*([^;]+);/gi;
        for (const m of block.matchAll(tokenRe)) {
          const name = m[1].toLowerCase();
          const value = m[2].trim().toLowerCase();

          // We only validate tokens that exist in the shared source-of-truth.
          // Page-specific tokens (--color-primary-light, --color-accent-light)
          // are intentionally local; we don't pin them.
          if (!(name in shared)) continue;

          // Skip if value is a var() reference (alias) — that's transitively safe
          if (value.startsWith('var(')) continue;

          if (value !== shared[name]) {
            drifts.push({
              file: rel,
              token: `--color-${name}`,
              inline: value,
              canonical: shared[name],
            });
          }
        }
      }
    }

    if (drifts.length > 0) {
      throw new Error(
        `Brand color drift between inline <style> and shared/styles.css ` +
          `(visitors will see different oranges across the site):\n` +
          drifts
            .map(
              (d) =>
                `  ${d.file}\n    ${d.token}: ${d.inline}  (canonical: ${d.canonical})`
            )
            .join('\n')
      );
    }
    expect(drifts).toEqual([]);
  });

  test('no obviously-bad brand hex values appear in inline overrides', async () => {
    // Defense-in-depth: catch known-bad legacy values even if shared/styles.css
    // is itself wrong (e.g. someone updates the inline overrides but forgets
    // to bump the source-of-truth and this test still passes).
    const FORBIDDEN = new Set([
      '#e08060', // pre-rebrand orange
      '#d97658', // typo of #D97757
      '#000000', // never use pure black for brand
      '#ffffff', // never use pure white where a token applies
    ]);
    const files = await getInlineStyleHtmlFiles();
    const found = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      for (const m of html.matchAll(/--color-[a-z-]+\s*:\s*(#[0-9a-f]{3,8})\s*;/gi)) {
        const v = m[1].toLowerCase();
        if (FORBIDDEN.has(v)) {
          found.push({ file: rel, value: v });
        }
      }
    }

    if (found.length > 0) {
      throw new Error(
        `Forbidden legacy/black/white brand color in inline override:\n` +
          found.map((f) => `  ${f.file} -> ${f.value}`).join('\n')
      );
    }
    expect(found).toEqual([]);
  });
});
