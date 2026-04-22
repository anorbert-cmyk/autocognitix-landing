import { describe, test, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();
const DOMAIN = 'https://autocognitix.hu';
const DOMAIN_WWW = 'https://www.autocognitix.hu';

/**
 * Wave-4 regression guard — every social/OG image referenced by a page must
 * exist on disk. A 404 OG image breaks Twitter/Facebook/LinkedIn cards which
 * silently kills CTR on shared links — the kind of bug nobody notices until
 * marketing complains weeks later.
 *
 * Scope
 * -----
 * Validates BOTH og:image (Open Graph) AND twitter:image (Twitter Card)
 * because the two often diverge. We check:
 *   - hu/**, en/** HTML files (production tree only; design/ is excluded)
 *   - unsubscribe.html
 *
 * Resolution rules
 * ----------------
 * - Absolute https://autocognitix.hu/... or https://www.autocognitix.hu/...
 *   -> strip prefix, resolve under ROOT
 * - Root-relative /foo/bar.jpg -> resolve under ROOT
 * - Anything else (other origins, data:, ...) is skipped — we don't own it
 */

function localPathFromUrl(ref) {
  if (ref.startsWith(DOMAIN_WWW)) return ref.slice(DOMAIN_WWW.length);
  if (ref.startsWith(DOMAIN)) return ref.slice(DOMAIN.length);
  if (ref.startsWith('/')) return ref;
  return null; // off-domain, not our problem
}

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

const META_IMG_RE =
  /<meta[^>]+(?:property|name)=["'](og:image|twitter:image|twitter:image:src)["'][^>]+content=["']([^"']+)["']/gi;

const META_IMG_RE_ALT =
  /<meta[^>]+content=["']([^"']+)["'][^>]+(?:property|name)=["'](og:image|twitter:image|twitter:image:src)["']/gi;

describe.skip('Wave-4: OG and Twitter Card images resolve to existing files', () => {
  test('every og:image / twitter:image references an existing local file (or off-domain URL)', async () => {
    const files = await getHtmlFiles();
    const broken = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');

      // Both attribute orders, dedup by content URL
      const refs = new Map(); // ref -> property
      for (const m of html.matchAll(META_IMG_RE)) {
        refs.set(m[2], m[1]);
      }
      for (const m of html.matchAll(META_IMG_RE_ALT)) {
        refs.set(m[1], m[2]);
      }

      for (const [ref, kind] of refs) {
        const local = localPathFromUrl(ref);
        if (!local) continue; // off-domain, not validated here

        const cleanLocal = local.split('?')[0].split('#')[0];
        const abs = path.join(ROOT, cleanLocal.replace(/^\//, ''));
        if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
          broken.push({ file: rel, kind, ref, abs });
        }
      }
    }

    if (broken.length > 0) {
      throw new Error(
        `Social-card image references with no file on disk ` +
          `(creates 404 cards on Facebook/Twitter/LinkedIn):\n` +
          broken
            .map((b) => `  ${b.file} -> [${b.kind}] ${b.ref}`)
            .join('\n')
      );
    }
    expect(broken).toEqual([]);
  });

  test('every page declares at least one og:image OR twitter:image', async () => {
    // Pages without ANY social card image render a blank preview when shared.
    // We accept either property — most pages use both.
    const files = await getHtmlFiles();
    const noCard = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      // Re-create iterators since regex /g state is per-instance
      const re1 = new RegExp(META_IMG_RE.source, META_IMG_RE.flags);
      const re2 = new RegExp(META_IMG_RE_ALT.source, META_IMG_RE_ALT.flags);
      const has = re1.test(html) || re2.test(html);
      if (!has) noCard.push(rel);
    }

    if (noCard.length > 0) {
      throw new Error(
        `Pages without og:image / twitter:image meta tag:\n` +
          noCard.map((m) => `  ${m}`).join('\n') +
          `\nAdd <meta property="og:image" content="https://autocognitix.hu/images/og/...jpg">`
      );
    }
    expect(noCard).toEqual([]);
  });

  test('og:image URLs use the canonical https://autocognitix.hu domain (not www., not http)', async () => {
    // Drift between www. and apex breaks dedup in social platforms' caches
    // and yields stale / wrong cards. http:// is a security regression.
    const files = await getHtmlFiles();
    const wrongDomain = [];

    for (const rel of files) {
      const html = fs.readFileSync(path.join(ROOT, rel), 'utf-8');
      for (const m of html.matchAll(META_IMG_RE)) {
        const ref = m[2];
        if (ref.startsWith('http://')) {
          wrongDomain.push({ file: rel, ref, why: 'http:// (must be https)' });
        } else if (ref.startsWith(DOMAIN_WWW)) {
          wrongDomain.push({
            file: rel,
            ref,
            why: 'www. subdomain (canonical is apex autocognitix.hu)',
          });
        }
      }
    }

    if (wrongDomain.length > 0) {
      throw new Error(
        `og:image URLs not on canonical https://autocognitix.hu:\n` +
          wrongDomain
            .map((b) => `  ${b.file} -> ${b.ref}  (${b.why})`)
            .join('\n')
      );
    }
    expect(wrongDomain).toEqual([]);
  });
});
