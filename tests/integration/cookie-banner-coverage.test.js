import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Wave-4 regression guard — site-wide cookie banner coverage.
 *
 * Background
 * ----------
 * Cookie consent (`shared/js/cookie-consent.js`) is the legal entry point for
 * any tracking on the site. If a single page ships WITHOUT this script we are
 * either (a) loading no analytics on that page (false negatives in metrics)
 * or, far worse, (b) loading analytics ungated -> direct GDPR Art. 7 + EDPB
 * 05/2020 violation. EU regulators have fined sites for exactly this drift,
 * which is why this test is the highest-priority Wave-4 guard.
 *
 * Failure mode this catches
 * -------------------------
 * Author copy-pastes a new HTML page from an old template that pre-dates the
 * cookie banner work, or omits the script tag during a refactor. Both happen.
 * One missing tag = compliance hole.
 *
 * Excludes
 * --------
 * - `*.bak`        backup copies
 * - `confirm.html` operational, no third-party scripts loaded, but we still
 *                  include it because consistency > exception list. If we ever
 *                  must exempt it, list it here AND the cookie policy.
 *
 * Implementation note
 * -------------------
 * We match the loose form `src=".../shared/js/cookie-consent.js..."` so the
 * cache-bust query string (`?v=20260421`) and `defer`/`async` attribute order
 * never break the assertion. A separate test (cache-bust-version.test.js)
 * verifies version consistency.
 */

async function getAllUserFacingHtml() {
  const huEn = await glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    ignore: ['**/*.bak', 'node_modules/**'],
  });
  const root = ['unsubscribe.html'].filter((f) =>
    fs.existsSync(path.join(ROOT, f))
  );
  return [...huEn, ...root];
}

const COOKIE_SCRIPT_RE =
  /<script[^>]+src=["'][^"']*\/shared\/js\/cookie-consent\.js[^"']*["']/i;

describe('Wave-4: cookie-consent.js loaded on every user-facing page', () => {
  test('every hu/, en/, and unsubscribe.html includes cookie-consent.js', async () => {
    const files = await getAllUserFacingHtml();
    expect(files.length).toBeGreaterThan(0);

    const missing = [];
    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      if (!COOKIE_SCRIPT_RE.test(html)) {
        missing.push(rel);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `Pages missing /shared/js/cookie-consent.js (GDPR/ePrivacy regression):\n` +
          missing.map((m) => `  ${m}`).join('\n') +
          `\nAdd: <script src="/shared/js/cookie-consent.js?v=YYYYMMDD" defer></script>` +
          ` to <head> BEFORE any analytics tags.`
      );
    }
    expect(missing).toEqual([]);
  });

  test('cookie-consent.js script is loaded with defer (non-blocking) attribute', async () => {
    const files = await getAllUserFacingHtml();
    const noDefer = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      // Find the cookie-consent script tag and verify defer/async present.
      const tagMatch = html.match(
        /<script[^>]+src=["'][^"']*\/shared\/js\/cookie-consent\.js[^"']*["'][^>]*>/i
      );
      if (!tagMatch) continue; // missing script caught by the previous test
      const tag = tagMatch[0];
      if (!/\b(defer|async)\b/i.test(tag)) {
        noDefer.push(`${rel}\n    ${tag}`);
      }
    }

    if (noDefer.length > 0) {
      throw new Error(
        `cookie-consent.js loaded without defer/async (will block first paint):\n` +
          noDefer.map((m) => `  ${m}`).join('\n')
      );
    }
    expect(noDefer).toEqual([]);
  });

  test('cookie-consent.js appears in <head>, not at end of <body>', async () => {
    // Loading the consent banner from <body> means it can fire AFTER an
    // analytics script that was placed in <head>. The banner must come first.
    const files = await getAllUserFacingHtml();
    const wrongPlacement = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const headEnd = html.search(/<\/head>/i);
      if (headEnd === -1) continue;
      const cookieIdx = html.search(
        /<script[^>]+src=["'][^"']*\/shared\/js\/cookie-consent\.js[^"']*["']/i
      );
      if (cookieIdx === -1) continue; // covered by previous test
      if (cookieIdx > headEnd) {
        wrongPlacement.push(rel);
      }
    }

    if (wrongPlacement.length > 0) {
      throw new Error(
        `cookie-consent.js found AFTER </head> (move it inside <head>):\n` +
          wrongPlacement.map((m) => `  ${m}`).join('\n')
      );
    }
    expect(wrongPlacement).toEqual([]);
  });
});
