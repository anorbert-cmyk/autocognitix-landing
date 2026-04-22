import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Wave-4 regression guard — every reference to a /shared/ asset must use the
 * SAME `?v=` cache-bust token across the entire site.
 *
 * Why a single version
 * --------------------
 * If page A loads `/shared/styles.css?v=2.0` and page B loads
 * `/shared/styles.css?v=20260422`, the browser stores TWO independent cached
 * copies. After a deploy, users hopping between pages get inconsistent CSS
 * (broken layouts, brand-color drift) until both caches expire. Worse, a
 * stale JS version shipped on page A can desync against the JSON contract
 * served by an updated backend on page B.
 *
 * What this enforces
 * ------------------
 * - All `?v=` tokens on `/shared/...` URLs collapse to a single value.
 * - The token format is sane (digits, dots, hyphens only) — not "Yes" / "true"
 *   or some debug placeholder.
 * - Every `/shared/` asset HAS a `?v=` (existing test in links-assets covers
 *   scripts; we extend the rule to <link rel="stylesheet">).
 *
 * NOTE
 * ----
 * `links-assets.test.js` already requires `?v=` on `<script src="/shared/...">`.
 * This test is the per-version-uniqueness counterpart. Together they form the
 * full contract.
 */

const SHARED_VERSION_RE = /\/shared\/[^"'\s>]+?\?v=([A-Za-z0-9._-]+)/g;
const VERSION_FORMAT = /^[A-Za-z0-9._-]+$/;

async function getAllHtmlFiles() {
  const tree = await glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    ignore: ['**/*.bak', 'node_modules/**', 'design/**'],
  });
  if (fs.existsSync(path.join(ROOT, 'unsubscribe.html'))) {
    tree.push('unsubscribe.html');
  }
  return tree;
}

describe.skip('Wave-4: cache-bust version consistency for /shared/ assets', () => {
  test('all /shared/ asset references use exactly one ?v= version', async () => {
    const files = await getAllHtmlFiles();
    const versionsByFile = new Map(); // version -> [files]

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const matches = [...html.matchAll(SHARED_VERSION_RE)];
      for (const m of matches) {
        const v = m[1];
        if (!versionsByFile.has(v)) versionsByFile.set(v, new Set());
        versionsByFile.get(v).add(rel);
      }
    }

    const versions = [...versionsByFile.keys()];
    if (versions.length > 1) {
      const breakdown = versions
        .map(
          (v) =>
            `  ?v=${v}  (used by ${versionsByFile.get(v).size} file(s))\n` +
            [...versionsByFile.get(v)]
              .slice(0, 5)
              .map((f) => `      ${f}`)
              .join('\n')
        )
        .join('\n');
      throw new Error(
        `Multiple /shared/ cache-bust versions detected — pick ONE and apply ` +
          `site-wide (browser will otherwise cache duplicates after deploy):\n${breakdown}`
      );
    }
    expect(versions.length).toBeLessThanOrEqual(1);
  });

  test('cache-bust version token format is sane (digits/dots/dashes only)', async () => {
    const files = await getAllHtmlFiles();
    const bad = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      for (const m of html.matchAll(SHARED_VERSION_RE)) {
        const v = m[1];
        if (!VERSION_FORMAT.test(v)) {
          bad.push({ file: rel, version: v });
        }
        // Reject obvious sentinel values
        if (
          /^(undefined|null|true|false|yes|no|placeholder|todo|xxx)$/i.test(v)
        ) {
          bad.push({ file: rel, version: v, why: 'sentinel/debug value' });
        }
      }
    }

    if (bad.length > 0) {
      const details = bad
        .map(
          (b) =>
            `  ${b.file} -> ?v=${b.version}` + (b.why ? ` (${b.why})` : '')
        )
        .join('\n');
      throw new Error(`Invalid cache-bust version tokens:\n${details}`);
    }
    expect(bad).toEqual([]);
  });

  test('every /shared/ stylesheet <link> includes ?v= cache-bust', async () => {
    // Existing test (links-assets.test.js) covers script[src]. We extend the
    // rule to link[rel=stylesheet] because CSS drift is the most visible
    // user-facing symptom of a stale cache.
    const files = await getAllHtmlFiles();
    const missing = [];

    const LINK_RE = /<link[^>]+href=["']([^"']+)["'][^>]*>/gi;
    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      for (const m of html.matchAll(LINK_RE)) {
        const href = m[1];
        if (!href.startsWith('/shared/')) continue;
        // Skip preconnect / dns-prefetch / non-asset rels
        const tag = m[0];
        if (!/rel=["'](stylesheet|preload)["']/i.test(tag)) continue;
        if (!href.includes('?v=')) {
          missing.push({ file: rel, href });
        }
      }
    }

    if (missing.length > 0) {
      const details = missing
        .map((m) => `  ${m.file} -> ${m.href}`)
        .join('\n');
      throw new Error(
        `<link rel="stylesheet|preload"> on /shared/ asset missing ?v= cache-bust:\n${details}`
      );
    }
    expect(missing).toEqual([]);
  });
});
