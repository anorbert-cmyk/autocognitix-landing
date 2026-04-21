import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import * as cheerio from 'cheerio';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Normalize a URL path: strip query/hash, normalize trailing slashes.
 */
function normalizePath(href) {
  let clean = href.split('?')[0].split('#')[0];
  // Normalize double slashes but preserve leading slash
  clean = clean.replace(/\/+/g, '/');
  return clean;
}

/**
 * Resolve an internal path to an actual file on disk.
 * Strips query params (?v=1.0) and hash fragments (#section).
 * Handles trailing-slash to index.html and extensionless paths.
 */
function resolveInternalPath(href) {
  const clean = normalizePath(href);

  const abs = path.join(ROOT, clean);

  // Exact file exists
  if (fs.existsSync(abs) && fs.statSync(abs).isFile()) return abs;

  // Trailing slash -> look for index.html
  if (clean.endsWith('/')) {
    const indexPath = path.join(abs, 'index.html');
    if (fs.existsSync(indexPath)) return indexPath;
  }

  // No trailing slash on directory -> try with trailing slash
  if (!path.extname(clean) && !clean.endsWith('/')) {
    const indexPath = path.join(abs, 'index.html');
    if (fs.existsSync(indexPath)) return indexPath;
  }

  // Extensionless -> try .html (nginx try_files $uri.html)
  if (!path.extname(clean)) {
    const withHtml = abs + '.html';
    if (fs.existsSync(withHtml)) return withHtml;
  }

  return null;
}

/**
 * Collect all HTML files from hu/ and en/ directories.
 */
async function getHtmlFiles() {
  return glob('**/*.html', {
    cwd: ROOT,
    absolute: false,
    ignore: ['node_modules/**', 'design/**'],
  });
}

/**
 * Get tool page HTML files (hu/eszkozok/ and en/tools/).
 */
async function getToolHtmlFiles() {
  return glob('{hu/eszkozok,en/tools}/**/*.html', {
    cwd: ROOT,
    absolute: false,
  });
}

// --- Link & Asset Verification -----------------------------------------------

describe('Link & Asset Verification', () => {
  /**
   * Scan all HTML files and collect broken links/assets.
   * Each test calls this independently to avoid shared mutable state.
   */
  async function scanHtmlFiles() {
    const htmlFiles = await getHtmlFiles();
    const brokenLinks = [];
    const brokenAssets = [];

    for (const relPath of htmlFiles) {
      const html = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const $ = cheerio.load(html);

      // Check <a href="..."> internal links
      $('a[href]').each((_, el) => {
        const href = $(el).attr('href');
        if (!href || href.startsWith('http') || href.startsWith('mailto:') || href.startsWith('tel:') || href === '#') return;
        if (href.startsWith('#')) {
          // Anchor-only link - checked separately
          return;
        }
        if (href.startsWith('/')) {
          // Skip root "/" - handled by nginx redirect to /hu/
          const cleanHref = normalizePath(href);
          if (cleanHref === '/') return;

          const resolved = resolveInternalPath(href);
          if (!resolved) {
            brokenLinks.push({ file: relPath, href, type: 'a[href]' });
          }
        }
      });

      // Check <link href="..."> for CSS
      $('link[href]').each((_, el) => {
        const href = $(el).attr('href');
        if (!href || href.startsWith('http') || href.startsWith('//')) return;
        if (href.startsWith('/')) {
          const resolved = resolveInternalPath(href);
          if (!resolved) {
            brokenAssets.push({ file: relPath, href, type: 'link[href]' });
          }
        }
      });

      // Check <script src="...">
      $('script[src]').each((_, el) => {
        const src = $(el).attr('src');
        if (!src || src.startsWith('http') || src.startsWith('//')) return;
        if (src.startsWith('/')) {
          const resolved = resolveInternalPath(src);
          if (!resolved) {
            brokenAssets.push({ file: relPath, src, type: 'script[src]' });
          }
        }
      });

      // Check <img src="...">
      $('img[src]').each((_, el) => {
        const src = $(el).attr('src');
        if (!src || src.startsWith('http') || src.startsWith('//') || src.startsWith('data:')) return;
        if (src.startsWith('/')) {
          const resolved = resolveInternalPath(src);
          if (!resolved) {
            brokenAssets.push({ file: relPath, src, type: 'img[src]' });
          }
        }
      });
    }

    return { brokenLinks, brokenAssets };
  }

  test('all internal href links resolve to existing files', async () => {
    const { brokenLinks } = await scanHtmlFiles();
    if (brokenLinks.length > 0) {
      const details = brokenLinks
        .map((b) => `  ${b.file} -> ${b.href}`)
        .join('\n');
      throw new Error(`Broken internal links (${brokenLinks.length}):\n${details}`);
    }
    expect(brokenLinks).toHaveLength(0);
  });

  test('all CSS, JS, and image src paths resolve to existing files', async () => {
    const { brokenAssets } = await scanHtmlFiles();
    if (brokenAssets.length > 0) {
      const details = brokenAssets
        .map((b) => `  ${b.file} -> ${b.href || b.src} (${b.type})`)
        .join('\n');
      throw new Error(`Broken asset references:\n${details}`);
    }
    expect(brokenAssets).toHaveLength(0);
  });
});

// --- Sitemap.xml Verification ------------------------------------------------

describe('Sitemap.xml Verification', () => {
  const DOMAIN = 'https://autocognitix.hu';

  test('every sitemap URL maps to an existing file', () => {
    const sitemapPath = path.join(ROOT, 'sitemap.xml');
    expect(fs.existsSync(sitemapPath)).toBe(true);

    const xml = fs.readFileSync(sitemapPath, 'utf-8');
    const $ = cheerio.load(xml, { xmlMode: true });

    const brokenUrls = [];

    $('url > loc').each((_, el) => {
      const loc = $(el).text().trim();
      if (!loc.startsWith(DOMAIN)) return;

      const urlPath = loc.replace(DOMAIN, '');
      const resolved = resolveInternalPath(urlPath);
      if (!resolved) {
        brokenUrls.push(loc);
      }
    });

    if (brokenUrls.length > 0) {
      throw new Error(
        `Sitemap URLs with no matching file:\n${brokenUrls.map((u) => `  ${u}`).join('\n')}`
      );
    }
    expect(brokenUrls).toHaveLength(0);
  });

  test('sitemap URL count matches expected page count', () => {
    const xml = fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf-8');
    const $ = cheerio.load(xml, { xmlMode: true });
    const urlCount = $('url > loc').length;

    // Sanity check: should have a reasonable number of URLs
    expect(urlCount).toBeGreaterThan(0);
    expect(urlCount).toBeLessThan(500);
  });

  /**
   * Inverse sitemap check: every user-facing HTML page on disk must be
   * reachable via sitemap.xml. This catches the common failure of forgetting
   * to add a new page to the sitemap (SEO regression).
   *
   * Excludes:
   *   - *.bak                (backup copies)
   *   - confirm.html         (email-flow landing, not indexed)
   *   - unsubscribe.html     (unsubscribe landing, not indexed)
   *   - pages starting with 'internal-' (ops/dev-only)
   */
  test('every user-facing HTML page is listed in sitemap.xml', async () => {
    const DOMAIN = 'https://autocognitix.hu';
    const EXCLUDE_NAMES = new Set(['confirm.html', 'unsubscribe.html']);
    const EXCLUDE_PREFIXES = ['internal-'];

    const htmlFiles = await glob('{hu,en}/**/*.html', {
      cwd: ROOT,
      ignore: ['**/*.bak', 'node_modules/**'],
    });

    const filtered = htmlFiles.filter((f) => {
      const base = path.basename(f);
      if (EXCLUDE_NAMES.has(base)) return false;
      if (EXCLUDE_PREFIXES.some((p) => base.startsWith(p))) return false;
      return true;
    });

    // Sitemap <loc> values can be directory-style ("/hu/blog/") which nginx
    // serves via try_files. Normalize both sides before comparing.
    const xml = fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf-8');
    const $ = cheerio.load(xml, { xmlMode: true });
    const locs = new Set();
    $('url > loc').each((_, el) => {
      const loc = $(el).text().trim();
      if (!loc.startsWith(DOMAIN)) return;
      let p = loc.slice(DOMAIN.length);
      // Directory-style "/hu/" is equivalent to "/hu/index.html"
      if (p.endsWith('/')) p = p + 'index.html';
      locs.add(p);
    });

    const missing = [];
    for (const rel of filtered) {
      const urlPath = '/' + rel.split(path.sep).join('/');
      if (!locs.has(urlPath)) {
        missing.push(urlPath);
      }
    }

    if (missing.length > 0) {
      throw new Error(
        `Pages on disk that are NOT in sitemap.xml:\n` +
          missing.map((m) => `  ${m}`).join('\n') +
          `\nAdd them to sitemap.xml or extend the EXCLUDE_NAMES/EXCLUDE_PREFIXES set.`
      );
    }
    expect(missing).toHaveLength(0);
  });
});

// --- Cache-Busting Params ----------------------------------------------------

describe('Cache-Busting Parameters', () => {
  test('all shared script references include ?v= cache-busting param', async () => {
    const htmlFiles = await getHtmlFiles();
    const missing = [];

    for (const relPath of htmlFiles) {
      const html = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const $ = cheerio.load(html);

      $('script[src]').each((_, el) => {
        const src = $(el).attr('src');
        if (!src || !src.startsWith('/shared/')) return;

        if (!src.includes('?v=')) {
          missing.push({ file: relPath, src });
        }
      });
    }

    if (missing.length > 0) {
      const details = missing
        .map((m) => `  ${m.file} -> ${m.src}`)
        .join('\n');
      throw new Error(
        `Shared scripts missing ?v= cache-busting param:\n${details}`
      );
    }
    expect(missing).toHaveLength(0);
  });
});

// --- Anchor Links (in-page #id references) -----------------------------------

describe('Anchor Link Verification', () => {
  test('no broken anchor links to non-existent IDs', async () => {
    const htmlFiles = await getHtmlFiles();
    const broken = [];

    // Cache: resolved file path -> Set of IDs (avoids O(n^2) re-parsing)
    const idCache = new Map();

    function getIdsForFile(filePath) {
      if (idCache.has(filePath)) return idCache.get(filePath);
      const html = fs.readFileSync(filePath, 'utf-8');
      const $ = cheerio.load(html);
      const ids = new Set();
      $('[id]').each((_, el) => {
        ids.add($(el).attr('id'));
      });
      idCache.set(filePath, ids);
      return ids;
    }

    for (const relPath of htmlFiles) {
      const absPath = path.join(ROOT, relPath);
      const html = fs.readFileSync(absPath, 'utf-8');
      const $ = cheerio.load(html);

      // Collect all IDs in this page (use cache)
      const ids = getIdsForFile(absPath);

      // Check anchor-only href="#something"
      $('a[href^="#"]').each((_, el) => {
        const href = $(el).attr('href');
        if (href === '#' || href === '#!' || href === '#0') return; // common no-ops
        const targetId = href.slice(1);
        if (targetId && !ids.has(targetId)) {
          broken.push({ file: relPath, href, targetId });
        }
      });

      // Check internal links with fragment: /page#section
      $('a[href]').each((_, el) => {
        const href = $(el).attr('href');
        if (!href || !href.startsWith('/') || !href.includes('#')) return;

        const [pagePath, fragment] = href.split('#');
        if (!fragment) return;

        const resolved = resolveInternalPath(pagePath);
        if (!resolved) return; // broken link - caught by other test

        const targetIds = getIdsForFile(resolved);

        if (!targetIds.has(fragment)) {
          broken.push({ file: relPath, href, targetId: fragment });
        }
      });
    }

    if (broken.length > 0) {
      const details = broken
        .map((b) => `  ${b.file} -> ${b.href} (missing id="${b.targetId}")`)
        .join('\n');
      throw new Error(`Broken anchor links:\n${details}`);
    }
    expect(broken).toHaveLength(0);
  });
});
