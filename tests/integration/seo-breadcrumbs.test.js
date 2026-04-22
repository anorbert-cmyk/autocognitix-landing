import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Wave-4 regression guard — non-root pages must declare BreadcrumbList
 * structured data so Google can render breadcrumbs in SERP rich results.
 *
 * Why
 * ---
 * BreadcrumbList JSON-LD increases SERP CTR ~5-10 % on multi-level pages
 * (blog posts, tool pages). Missing it doesn't break the site, but the SEO
 * lift is meaningful and easy to lose during template churn.
 *
 * Scope
 * -----
 * Pages under hu/blog/, en/blog/, hu/eszkozok/, en/tools/, hu/legal/, en/legal/
 * MUST contain a JSON-LD `<script type="application/ld+json">` whose payload
 * has `@type: "BreadcrumbList"` and at least 2 itemListElement entries.
 *
 * Pages we don't require breadcrumbs on
 * --------------------------------------
 * - hu/index.html, en/index.html  (top of tree, no parent)
 * - blog/index.html, eszkozok/index.html, tools/index.html  (these ARE the
 *   2nd level — Google handles them via category breadcrumb on the parent)
 * - confirm.html, unsubscribe.html  (operational, not indexed)
 */

function isExcluded(rel) {
  if (rel === 'hu/index.html' || rel === 'en/index.html') return true;
  if (rel === 'unsubscribe.html') return true;
  if (rel.endsWith('/index.html')) return true;
  if (rel.endsWith('/confirm.html')) return true;
  return false;
}

function findJsonLd(html) {
  const blocks = [];
  const re = /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  for (const m of html.matchAll(re)) {
    try {
      const parsed = JSON.parse(m[1].trim());
      blocks.push(parsed);
    } catch {
      // Malformed JSON — caught by a separate test below
      blocks.push({ __malformed: true, raw: m[1].slice(0, 200) });
    }
  }
  return blocks;
}

function flattenGraph(blocks) {
  // Handle @graph arrays: { "@context": "...", "@graph": [{...}, {...}] }
  const out = [];
  for (const b of blocks) {
    if (b && Array.isArray(b['@graph'])) {
      out.push(...b['@graph']);
    } else if (Array.isArray(b)) {
      out.push(...b);
    } else {
      out.push(b);
    }
  }
  return out;
}

async function getNonRootHtmlFiles() {
  const all = await glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    ignore: ['**/*.bak', 'node_modules/**', 'design/**'],
  });
  return all.filter((rel) => !isExcluded(rel));
}

describe.skip('Wave-4: BreadcrumbList JSON-LD on non-root pages', () => {
  test('every non-root page declares a BreadcrumbList in JSON-LD', async () => {
    const files = await getNonRootHtmlFiles();
    expect(files.length).toBeGreaterThan(0);

    const missing = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const items = flattenGraph(findJsonLd(html));
      const hasBreadcrumb = items.some(
        (b) => b && (b['@type'] === 'BreadcrumbList' || (Array.isArray(b['@type']) && b['@type'].includes('BreadcrumbList')))
      );
      if (!hasBreadcrumb) {
        missing.push(rel);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `Pages missing BreadcrumbList structured data ` +
          `(SEO regression — SERP rich-result loss):\n` +
          missing.map((m) => `  ${m}`).join('\n') +
          `\nAdd <script type="application/ld+json"> with @type BreadcrumbList ` +
          `and 2+ itemListElement entries.`
      );
    }
    expect(missing).toEqual([]);
  });

  test('BreadcrumbList has at least 2 itemListElement entries', async () => {
    const files = await getNonRootHtmlFiles();
    const tooShort = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const items = flattenGraph(findJsonLd(html));
      const crumbs = items.find(
        (b) => b && (b['@type'] === 'BreadcrumbList' || (Array.isArray(b['@type']) && b['@type'].includes('BreadcrumbList')))
      );
      if (!crumbs) continue; // covered by previous test
      const list = crumbs.itemListElement || [];
      if (!Array.isArray(list) || list.length < 2) {
        tooShort.push({ file: rel, count: Array.isArray(list) ? list.length : 0 });
      }
    }

    if (tooShort.length > 0) {
      const details = tooShort
        .map((t) => `  ${t.file}  (${t.count} items)`)
        .join('\n');
      throw new Error(
        `BreadcrumbList has fewer than 2 itemListElement entries ` +
          `(Google requires at least 2 to render rich result):\n${details}`
      );
    }
    expect(tooShort).toEqual([]);
  });

  test('all JSON-LD blocks are valid JSON (no malformed payloads)', async () => {
    // A malformed JSON-LD block silently disables ALL structured data on the
    // page in Google's parser — a regression that's invisible until SERP tests.
    const files = await getNonRootHtmlFiles();
    const broken = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const blocks = findJsonLd(html);
      for (const b of blocks) {
        if (b && b.__malformed) {
          broken.push({ file: rel, snippet: b.raw });
        }
      }
    }

    if (broken.length > 0) {
      throw new Error(
        `Malformed JSON-LD payloads:\n` +
          broken
            .map((b) => `  ${b.file}\n    ${b.snippet.slice(0, 120)}...`)
            .join('\n')
      );
    }
    expect(broken).toEqual([]);
  });
});
