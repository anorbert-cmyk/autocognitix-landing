import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import * as cheerio from 'cheerio';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Wave-4 regression guard — every page with a <main> landmark must expose a
 * "skip to main content" link as the FIRST focusable element inside <body>.
 *
 * Why this matters
 * ----------------
 * WCAG 2.2 SC 2.4.1 (Bypass Blocks) requires a mechanism to skip repeated
 * navigation. For keyboard and screen-reader users, tabbing past 30+ nav links
 * on every page is a productivity tax. A `.skip-link` solves it in one tag.
 *
 * What this test enforces
 * -----------------------
 * 1) Pages with <main> must contain a `<a class="skip-link" href="#main-content">`.
 * 2) The skip link must be the FIRST focusable element after <body> opens —
 *    if a logo or nav <a> precedes it, the skip is useless.
 * 3) <main> must carry id="main-content" (the skip target). A dangling href
 *    that points nowhere is a regression.
 *
 * Loose matching
 * --------------
 * The href value is normalised (#main-content / #main / #content all OK)
 * because team conventions occasionally drift. We pin on the CSS class because
 * styling depends on it.
 */

const SKIP_HREFS = new Set(['#main-content', '#main', '#content']);

async function getHtmlFiles() {
  const tree = await glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    ignore: ['**/*.bak', 'node_modules/**', 'design/**'],
  });
  if (fs.existsSync(path.join(ROOT, 'unsubscribe.html'))) {
    tree.push('unsubscribe.html');
  }
  return tree;
}

function pagesWithMain(files) {
  return files.filter((rel) => {
    const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
    return /<main[\s>]/i.test(html);
  });
}

describe('Wave-4: skip-link present on every page with <main>', () => {
  test('every page with <main> includes class="skip-link"', async () => {
    const files = await getHtmlFiles();
    const pages = pagesWithMain(files);
    expect(pages.length).toBeGreaterThan(0);

    const missing = [];
    for (const rel of pages) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      if (!/class=["'][^"']*\bskip-link\b[^"']*["']/.test(html)) {
        missing.push(rel);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `Pages with <main> but no .skip-link (WCAG 2.4.1 violation):\n` +
          missing.map((m) => `  ${m}`).join('\n') +
          `\nAdd: <a href="#main-content" class="skip-link">Skip to main content</a>` +
          ` immediately after <body>.`
      );
    }
    expect(missing).toEqual([]);
  });

  test('skip-link href targets an existing id on the page', async () => {
    const files = await getHtmlFiles();
    const pages = pagesWithMain(files);
    const broken = [];

    for (const rel of pages) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const $ = cheerio.load(html);
      const skip = $('a.skip-link').first();
      if (!skip.length) continue; // covered above
      const href = skip.attr('href') || '';
      if (!href.startsWith('#')) {
        broken.push({ file: rel, href, why: 'href is not an in-page anchor' });
        continue;
      }
      const id = href.slice(1);
      if (!id) {
        broken.push({ file: rel, href, why: 'empty fragment' });
        continue;
      }
      if (!SKIP_HREFS.has(href)) {
        // Allow non-canonical names but verify the ID resolves on the page.
        if ($('#' + CSS.escape(id)).length === 0) {
          broken.push({ file: rel, href, why: `no element with id="${id}"` });
        }
        continue;
      }
      // Canonical href: target id must exist
      if ($('#' + CSS.escape(id)).length === 0) {
        broken.push({ file: rel, href, why: `no element with id="${id}"` });
      }
    }

    if (broken.length > 0) {
      throw new Error(
        `skip-link href has no matching id on the page:\n` +
          broken
            .map((b) => `  ${b.file}  href=${b.href}  (${b.why})`)
            .join('\n')
      );
    }
    expect(broken).toEqual([]);
  });

  test('skip-link is the first focusable element inside <body>', async () => {
    // SC 2.4.1 wants the skip link to be the FIRST tab stop. A logo, search,
    // or nav <a> before it defeats the purpose entirely.
    const files = await getHtmlFiles();
    const pages = pagesWithMain(files);
    const wrongOrder = [];

    for (const rel of pages) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      const $ = cheerio.load(html);
      const skip = $('a.skip-link').first();
      if (!skip.length) continue;

      // Walk all focusable elements inside <body> in DOM order
      const focusable = $(
        'body a[href], body button, body input, body select, body textarea, body [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) continue;
      const first = focusable.first()[0];
      const skipNode = skip[0];
      if (first !== skipNode) {
        const tag = first.tagName?.toLowerCase() || '?';
        const cls = ($(first).attr('class') || '').slice(0, 60);
        wrongOrder.push(
          `${rel}  (first focusable is <${tag} class="${cls}">, not .skip-link)`
        );
      }
    }

    if (wrongOrder.length > 0) {
      throw new Error(
        `.skip-link is not the first focusable element inside <body>:\n` +
          wrongOrder.map((m) => `  ${m}`).join('\n') +
          `\nMove the skip-link to be the first child of <body>.`
      );
    }
    expect(wrongOrder).toEqual([]);
  });
});
