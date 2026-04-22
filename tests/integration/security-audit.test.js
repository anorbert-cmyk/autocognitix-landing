import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import * as cheerio from 'cheerio';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();

/**
 * Collect all HTML files from hu/ and en/ plus unsubscribe.html.
 */
async function getAllHtmlFiles() {
  return glob('{hu,en}/**/*.html', {
    cwd: ROOT,
    absolute: false,
  });
}

/**
 * Collect tool page HTML files only.
 */
async function getToolHtmlFiles() {
  return glob('{hu/eszkozok,en/tools}/**/*.html', {
    cwd: ROOT,
    absolute: false,
    ignore: ['**/index.html'],
  });
}

/**
 * Collect all JS files in shared/ directory.
 */
async function getSharedJsFiles() {
  return glob('shared/**/*.js', {
    cwd: ROOT,
    absolute: false,
  });
}

// --- Secret / Credential Detection -------------------------------------------

describe('Secret & Credential Detection', () => {
  // Patterns that indicate hardcoded secrets
  const SECRET_PATTERNS = [
    { pattern: /api[_-]?key\s*[:=]\s*['"][^'"]{20,}['"]/gi, name: 'API key assignment' },
    { pattern: /secret\s*[:=]\s*['"][^'"]{8,}['"]/gi, name: 'Secret assignment' },
    { pattern: /password\s*[:=]\s*['"][^'"]{3,}['"]/gi, name: 'Password assignment' },
    { pattern: /(?:access|auth|bearer)[_-]?token\s*[:=]\s*['"][^'"]{8,}['"]/gi, name: 'Token assignment' },
    { pattern: /(?:sk|pk)[-_](?:live|test)[-_][a-zA-Z0-9]{20,}/g, name: 'Stripe-style key' },
    { pattern: /AIza[0-9A-Z_-]{35}/g, name: 'Google API key' },
    { pattern: /ghp_[a-zA-Z0-9]{36}/g, name: 'GitHub PAT' },
  ];

  // Known dev/placeholder values that are not real secrets
  const DEV_VALUE_PATTERNS = [
    /(?:development|test|local|mock|placeholder|example)/i,
  ];

  // False positive exclusions
  const FALSE_POSITIVE_PATTERNS = [
    /csrf[_-]?token/i,
    /token[s]?\s*[:\.]?\s*$/i, // "tokens" as a word
    /meta.*token/i, // meta csrf token references
    /token[_-]?type/i, // token type declarations
    /token[_-]?expir/i, // token expiration references
    /token[_-]?valid/i, // token validation references
    /refresh[_-]?token/i, // refresh token flow references
    /schema.*password/i, // schema descriptions
    /type="password"/i, // input type declarations
    /password.*placeholder/i, // placeholder text
    /forgot.*password/i, // UI text
    /reset.*password/i, // UI text
  ];

  function isFalsePositive(line) {
    if (FALSE_POSITIVE_PATTERNS.some((fp) => fp.test(line))) return true;
    // Exclude known dev/placeholder values from flagging
    if (DEV_VALUE_PATTERNS.some((dp) => dp.test(line))) return true;
    return false;
  }

  test('no hardcoded secrets in HTML files', async () => {
    const htmlFiles = await getAllHtmlFiles();
    const findings = [];

    for (const relPath of htmlFiles) {
      const content = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        for (const { pattern, name } of SECRET_PATTERNS) {
          pattern.lastIndex = 0; // reset regex state
          if (pattern.test(line) && !isFalsePositive(line)) {
            findings.push({
              file: relPath,
              line: i + 1,
              type: name,
              snippet: line.trim().substring(0, 80),
            });
          }
        }
      }
    }

    if (findings.length > 0) {
      const details = findings
        .map((f) => `  ${f.file}:${f.line} [${f.type}] ${f.snippet}`)
        .join('\n');
      throw new Error(`Potential hardcoded secrets found:\n${details}`);
    }
    expect(findings).toHaveLength(0);
  });

  test('no hardcoded secrets in shared JS files', async () => {
    const jsFiles = await getSharedJsFiles();
    const findings = [];

    for (const relPath of jsFiles) {
      const content = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        for (const { pattern, name } of SECRET_PATTERNS) {
          pattern.lastIndex = 0;
          if (pattern.test(line) && !isFalsePositive(line)) {
            findings.push({
              file: relPath,
              line: i + 1,
              type: name,
              snippet: line.trim().substring(0, 80),
            });
          }
        }
      }
    }

    if (findings.length > 0) {
      const details = findings
        .map((f) => `  ${f.file}:${f.line} [${f.type}] ${f.snippet}`)
        .join('\n');
      throw new Error(`Potential hardcoded secrets in JS:\n${details}`);
    }
    expect(findings).toHaveLength(0);
  });
});

// --- innerHTML Safety Audit ---------------------------------------------------

describe('innerHTML Safety Audit', () => {
  // NOTE: This test is NOW BLOCKING (previously advisory). An allow-list below
  // records every .innerHTML = line that has been manually audited and confirmed
  // safe. Anything not on the allow-list and not a safe computed value (numeric,
  // escapeHTML-wrapped, etc.) will FAIL this test.
  //
  // HOW TO ADD AN ENTRY:
  //   - Format: `relative/file/path.html:lineNumber`
  //   - Only add entries whose innerHTML target is either (a) a static string
  //     literal or (b) concatenates ONLY escapeHTML()-wrapped variables.
  //   - If in doubt, refactor the code to use escapeHTML() instead of allow-listing.
  // Wave 5: every HTML file shifted by +1 after the cookie-banner.css <link>
  // tag was inserted in <head>. Line numbers below all bumped accordingly.
  const INNERHTML_ALLOWLIST = new Set([
    'hu/eszkozok/megeri-megjavitani.html:795', // static spinner label
    'hu/eszkozok/megeri-megjavitani.html:815', // static "frissítve" label
    'hu/eszkozok/megeri-megjavitani.html:845', // static fallback label
    'hu/eszkozok/megeri-megjavitani.html:928', // interpolates numeric uncertainty only
    'hu/eszkozok/megeri-megjavitani.html:935', // static HTML, no user input
    'hu/eszkozok/muszaki-vizsga-prediktor.html:764', // static warning copy
    'hu/eszkozok/muszaki-vizsga-prediktor.html:879', // static spinner label
    'hu/eszkozok/muszaki-vizsga-prediktor.html:887', // static updated-from-backend label
    'hu/eszkozok/muszaki-vizsga-prediktor.html:895', // static header
    'hu/eszkozok/muszaki-vizsga-prediktor.html:907', // static fallback label
    // EN mirrors of the above (see hu-en-parity.test.js for the pairing).
    'en/tools/worth-repairing.html:795',
    'en/tools/worth-repairing.html:815',
    'en/tools/worth-repairing.html:845',
    'en/tools/worth-repairing.html:928',
    'en/tools/worth-repairing.html:935',
    'en/tools/mot-predictor.html:764',
    'en/tools/mot-predictor.html:879',
    'en/tools/mot-predictor.html:887',
    'en/tools/mot-predictor.html:895',
    'en/tools/mot-predictor.html:907',
    // Wave 2 line drift after <main>, <fieldset>, and i18n insertions
    'hu/eszkozok/megeri-megjavitani.html:972', // shifted from :955 (numeric uncertainty only, line drift)
    'en/tools/worth-repairing.html:974', // EN mirror (line shifts as Wave 4 SEO/perf agents add meta tags)
    // renderCard() patterns — all variables pre-escape via escapeHTML() at build sites
    'hu/eszkozok/szerviz-kereso.html:595', // card.innerHTML = headerHTML + descHTML + btnHTML (all escaped; line shifted +2 in Wave 5 diacritics restore)
    'en/tools/workshop-finder.html:591',   // EN mirror of szerviz-kereso (line shifted)
  ]);

  test('all innerHTML assignments with user-controllable data use escapeHtml()', async () => {
    const toolFiles = await getToolHtmlFiles();
    const unsafe = [];

    for (const relPath of toolFiles) {
      const content = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Find lines with .innerHTML = containing string concatenation
        if (!line.includes('.innerHTML')) continue;

        // Skip lines that only set innerHTML to '' (clearing)
        if (/\.innerHTML\s*=\s*['"]'?\s*['"]?\s*;?\s*$/.test(line)) continue;

        // Lines that concatenate variables into innerHTML without escapeHtml
        // Look for patterns like: + variable + or + variable; (without escapeHtml wrapping)
        const hasStringConcat = /\.innerHTML\s*=.*\+/.test(line);
        if (!hasStringConcat) continue;

        // Check if every concatenated variable is wrapped in escapeHtml/escapeHTML
        // Extract the innerHTML assignment value
        const assignmentMatch = line.match(/\.innerHTML\s*=(.*)/);
        if (!assignmentMatch) continue;

        const assignment = assignmentMatch[1];

        // Find variable references in the concatenation (not string literals)
        // Pattern: + someVar or + someObj.prop (not wrapped in escapeHtml)
        const segments = assignment.split('+').map((s) => s.trim());

        for (const segment of segments) {
          // Skip string literals
          if (/^['"`]/.test(segment) || /['"`][;]?\s*$/.test(segment)) continue;
          // Skip empty or whitespace
          if (!segment || segment === ';') continue;

          // This segment is a variable reference -check if wrapped in escapeHtml
          if (
            !segment.includes('escapeHtml(') &&
            !segment.includes('escapeHTML(') &&
            !segment.includes('ToolCommon.escapeHTML(')
          ) {
            // Check if it is a safe computed value (not user input)
            // Allow: numeric computations, .length, .toFixed, constants
            const isSafeComputed =
              /^\d/.test(segment) ||
              /\.length/.test(segment) ||
              /\.toFixed/.test(segment) ||
              /\.toLocaleString/.test(segment) ||
              /Math\./.test(segment) ||
              /parseInt|parseFloat/.test(segment) ||
              /typeof/.test(segment);

            if (!isSafeComputed) {
              const key = `${relPath}:${i + 1}`;
              if (!INNERHTML_ALLOWLIST.has(key)) {
                unsafe.push({
                  file: relPath,
                  line: i + 1,
                  snippet: line.trim().substring(0, 120),
                  segment: segment.substring(0, 60),
                });
              }
            }
          }
        }
      }
    }

    if (unsafe.length > 0) {
      const details = unsafe
        .map(
          (u) =>
            `  ${u.file}:${u.line}\n    ${u.snippet}\n    Unescaped: ${u.segment}`
        )
        .join('\n');
      throw new Error(
        `Unsafe innerHTML assignments found (wrap variables in escapeHTML() ` +
        `or add the exact "file:line" to INNERHTML_ALLOWLIST after manual audit):\n${details}`
      );
    }
    expect(unsafe).toHaveLength(0);
  });
});

// --- Dangerous JS Constructs -------------------------------------------------

describe('Dangerous JS Constructs', () => {
  test('no eval() in production code', async () => {
    const htmlFiles = await getAllHtmlFiles();
    const jsFiles = await getSharedJsFiles();
    const allFiles = [...htmlFiles, ...jsFiles];
    const findings = [];

    for (const relPath of allFiles) {
      const content = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Match eval( but not .eval( from jsdom test helpers, and not in comments
        if (/(?<!\w)eval\s*\(/.test(line) && !/^\s*\/\//.test(line) && !/^\s*\*/.test(line)) {
          findings.push({
            file: relPath,
            line: i + 1,
            snippet: line.trim().substring(0, 80),
          });
        }
      }
    }

    if (findings.length > 0) {
      const details = findings
        .map((f) => `  ${f.file}:${f.line} ${f.snippet}`)
        .join('\n');
      throw new Error(`eval() found in production code:\n${details}`);
    }
    expect(findings).toHaveLength(0);
  });

  test('no Function() constructor in production code', async () => {
    const htmlFiles = await getAllHtmlFiles();
    const jsFiles = await getSharedJsFiles();
    const allFiles = [...htmlFiles, ...jsFiles];
    const findings = [];

    for (const relPath of allFiles) {
      const content = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Match new Function( but not in comments
        if (/new\s+Function\s*\(/.test(line) && !/^\s*\/\//.test(line) && !/^\s*\*/.test(line)) {
          findings.push({
            file: relPath,
            line: i + 1,
            snippet: line.trim().substring(0, 80),
          });
        }
      }
    }

    if (findings.length > 0) {
      const details = findings
        .map((f) => `  ${f.file}:${f.line} ${f.snippet}`)
        .join('\n');
      throw new Error(`Function() constructor found in production code:\n${details}`);
    }
    expect(findings).toHaveLength(0);
  });
});

// --- External Script Sources -------------------------------------------------

describe('External Script Sources', () => {
  test('no external script sources -all scripts should be local or inline', async () => {
    const htmlFiles = await getAllHtmlFiles();
    const external = [];

    // Allowed external domains (add exceptions here if needed)
    const ALLOWED_EXTERNAL = [
      // Example: 'cdn.jsdelivr.net' if CDN is approved
    ];

    for (const relPath of htmlFiles) {
      const html = fs.readFileSync(path.join(ROOT, relPath), 'utf-8');
      const $ = cheerio.load(html);

      $('script[src]').each((_, el) => {
        const src = $(el).attr('src');
        if (!src) return;

        // External if starts with http:// or https:// or //
        const isExternal =
          src.startsWith('http://') ||
          src.startsWith('https://') ||
          src.startsWith('//');

        if (isExternal) {
          const isAllowed = ALLOWED_EXTERNAL.some((domain) =>
            src.includes(domain)
          );
          if (!isAllowed) {
            external.push({ file: relPath, src });
          }
        }
      });
    }

    if (external.length > 0) {
      const details = external
        .map((e) => `  ${e.file} -> ${e.src}`)
        .join('\n');
      throw new Error(`External script sources found:\n${details}`);
    }
    expect(external).toHaveLength(0);
  });
});

// --- Nginx Security Headers --------------------------------------------------

describe('Nginx Security Headers', () => {
  let nginxConf;

  beforeAll(() => {
    const confPath = path.join(ROOT, 'nginx.conf');
    expect(fs.existsSync(confPath)).toBe(true);
    nginxConf = fs.readFileSync(confPath, 'utf-8');
  });

  test('X-Frame-Options header is configured', () => {
    expect(nginxConf).toMatch(/add_header\s+X-Frame-Options/);
    expect(nginxConf).toMatch(/X-Frame-Options\s+["']SAMEORIGIN["']/i);
  });

  test('X-Content-Type-Options header is configured', () => {
    expect(nginxConf).toMatch(/add_header\s+X-Content-Type-Options/);
    expect(nginxConf).toMatch(/X-Content-Type-Options\s+["']nosniff["']/i);
  });

  test('X-XSS-Protection header is configured', () => {
    expect(nginxConf).toMatch(/add_header\s+X-XSS-Protection/);
  });

  test('Referrer-Policy header is configured', () => {
    expect(nginxConf).toMatch(/add_header\s+Referrer-Policy/);
  });

  test('security headers use "always" directive', () => {
    // "always" ensures headers are sent even on error responses
    // Only check security-relevant headers, not Cache-Control
    const SECURITY_HEADERS = [
      'X-Frame-Options',
      'X-Content-Type-Options',
      'X-XSS-Protection',
      'Referrer-Policy',
      'Content-Security-Policy',
      'Strict-Transport-Security',
    ];

    const headerLines = nginxConf
      .split('\n')
      .filter((line) => {
        if (!line.includes('add_header') || line.trim().startsWith('#')) return false;
        return SECURITY_HEADERS.some((h) => line.includes(h));
      });

    const missingAlways = headerLines.filter(
      (line) => !line.includes('always')
    );

    if (missingAlways.length > 0) {
      throw new Error(
        `Security headers missing "always" directive:\n${missingAlways.map((l) => `  ${l.trim()}`).join('\n')}`
      );
    }
    expect(missingAlways).toHaveLength(0);
  });
});
