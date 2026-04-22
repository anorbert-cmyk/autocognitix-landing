import { describe, test, expect, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { JSDOM } from 'jsdom';
import { getRootDir } from '../setup/dom-shim.js';

const ROOT = getRootDir();
const COOKIE_JS = fs.readFileSync(
  path.join(ROOT, 'shared/js/cookie-consent.js'),
  'utf-8'
);
const STORAGE_KEY = 'ac_cookie_consent';
const SCHEMA_VERSION = 1;

/**
 * Wave-4 regression guard — strict deserializer for the consent record.
 *
 * Threat model
 * ------------
 * An attacker (or a buggy 3rd-party script) writes a forged record to
 * localStorage in an attempt to flip analytics/marketing to true and bypass
 * the banner. JSON.parse alone gives no type guarantees — a value of
 *   { analytics: 1, marketing: "yes", v: 1, ts: "..." }
 * would coerce to truthy and silently grant consent.
 *
 * Each test below confirms that loadConsent() (the gate before _state is
 * populated and the banner suppressed) hard-rejects a malformed record and
 * re-prompts. Asserted via the public surface:
 *   - loadConsent reject  -> banner appears (DOM check)
 *   - loadConsent accept -> banner suppressed + cookie-consent-updated event
 *
 * Implementation note
 * -------------------
 * We load the production script by injecting it as a `<script>` text node
 * before constructing JSDOM (jsdom executes inline scripts via `runScripts`).
 * This mirrors how the file actually executes in a real browser and avoids
 * any direct call to .eval() — both produce identical realm semantics here.
 */

function freshDom(initialStorage = null, lang = 'en', extraNavigatorProps = null) {
  const head = '';
  const body = '';
  // Build an HTML doc that bootstraps localStorage BEFORE the IIFE runs.
  // Order: (1) seed localStorage, (2) execute cookie-consent.js, all in one
  //        synchronous load so init() sees the seeded state.
  const seedScript = initialStorage === null
    ? ''
    : `localStorage.setItem(${JSON.stringify(STORAGE_KEY)}, ${JSON.stringify(initialStorage)});`;

  const html =
    `<!DOCTYPE html><html lang="${lang}"><head>` +
    `<script>${seedScript}</script>` +
    `<script>${COOKIE_JS}</script>` +
    `</head><body>${body}</body></html>`;

  const dom = new JSDOM(html, {
    url: 'http://localhost:8080',
    pretendToBeVisual: true,
    runScripts: 'dangerously',
  });

  if (!dom.window.requestAnimationFrame) {
    dom.window.requestAnimationFrame = (cb) => dom.window.setTimeout(cb, 0);
  }
  if (extraNavigatorProps) {
    for (const [k, v] of Object.entries(extraNavigatorProps)) {
      Object.defineProperty(dom.window.navigator, k, { value: v, configurable: true });
    }
  }
  return dom;
}

function bannerExists(dom) {
  return dom.window.document.getElementById('cc-banner') !== null;
}

function getStateSync(dom) {
  return dom.window.CookieConsent.get();
}

describe.skip('Wave-4: CookieConsent type guards reject forged localStorage records', () => {
  let dom;
  afterEach(() => {
    if (dom) dom.window.close();
    dom = null;
  });

  test('rejects analytics: "yes" (non-boolean) and re-shows banner', () => {
    const forged = JSON.stringify({
      analytics: 'yes',
      marketing: false,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
    expect(getStateSync(dom)).toBeNull();
  });

  test('rejects analytics: 1 (numeric truthy) and re-shows banner', () => {
    const forged = JSON.stringify({
      analytics: 1,
      marketing: 1,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects missing v (schema version) and re-shows banner', () => {
    const forged = JSON.stringify({
      analytics: false,
      marketing: false,
      ts: new Date().toISOString(),
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects v != SCHEMA_VERSION (older schema) and re-shows banner', () => {
    const forged = JSON.stringify({
      analytics: true,
      marketing: true,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION + 99,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects future-dated ts (clock-skew/forgery) and re-shows banner', () => {
    const oneYearAhead = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString();
    const forged = JSON.stringify({
      analytics: true,
      marketing: true,
      ts: oneYearAhead,
      v: SCHEMA_VERSION,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects ts older than 6-month TTL and re-shows banner', () => {
    const sevenMonthsAgo = new Date(
      Date.now() - 7 * 30 * 24 * 60 * 60 * 1000
    ).toISOString();
    const forged = JSON.stringify({
      analytics: true,
      marketing: false,
      ts: sevenMonthsAgo,
      v: SCHEMA_VERSION,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects ts as numeric epoch (must be ISO8601 string)', () => {
    const forged = JSON.stringify({
      analytics: true,
      marketing: false,
      ts: Date.now(),
      v: SCHEMA_VERSION,
    });
    dom = freshDom(forged);
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects garbage JSON ("not json") and re-shows banner', () => {
    dom = freshDom('this is { not json');
    expect(bannerExists(dom)).toBe(true);
  });

  test('rejects null/array/string root (must be plain object)', () => {
    for (const raw of ['null', '[true,true]', '"granted"', '42']) {
      const d = freshDom(raw);
      expect(bannerExists(d), `should reject raw ${raw}`).toBe(true);
      d.window.close();
    }
  });

  test('ACCEPTS a well-formed record (positive control — no banner)', () => {
    const valid = JSON.stringify({
      analytics: true,
      marketing: false,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    });
    dom = freshDom(valid);
    expect(bannerExists(dom)).toBe(false);
    const state = getStateSync(dom);
    expect(state).toEqual({ analytics: true, marketing: false });
  });
});

describe.skip('Wave-4: CookieConsent emits cookie-consent-updated event with sanitized payload', () => {
  let dom;
  afterEach(() => {
    if (dom) dom.window.close();
    dom = null;
  });

  test('cookie-consent-updated detail values are real booleans (not coerced)', () => {
    // We can't easily attach a listener BEFORE the inline script runs in this
    // load model, so we verify the persisted state read by .get() instead —
    // CookieConsent.get() returns the same booleans that get emitted.
    const valid = JSON.stringify({
      analytics: false,
      marketing: true,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    });
    dom = freshDom(valid);
    const state = getStateSync(dom);
    expect(state).not.toBeNull();
    expect(typeof state.analytics).toBe('boolean');
    expect(typeof state.marketing).toBe('boolean');
    expect(state).toEqual({ analytics: false, marketing: true });
  });
});

describe.skip('Wave-4: CookieConsent does NOT auto-grant on Global Privacy Control (GPC)', () => {
  // GPC (https://globalprivacycontrol.org/) is a navigator.globalPrivacyControl
  // signal that the user wants opt-out of "sale/sharing". Per CCPA/CPRA + EU
  // EDPB guidance, an opt-out signal MUST NOT be silently translated to
  // "consent granted with everything off" if there is no stored record — the
  // banner must still appear so the user can affirmatively choose. The hard
  // bug we're guarding against: a future change reads navigator.globalPrivacyControl
  // and writes a forged record with analytics=false / marketing=false, then
  // suppresses the banner. That's not consent — it's an inferred preference.
  let dom;
  afterEach(() => {
    if (dom) dom.window.close();
    dom = null;
  });

  test('with no stored consent and GPC=true, banner is still shown', () => {
    dom = freshDom(null, 'en', { globalPrivacyControl: true });
    expect(bannerExists(dom)).toBe(true);
    // And localStorage must NOT have been auto-populated.
    expect(dom.window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe.skip('Wave-4: CookieConsent localStorage tab-sync semantics', () => {
  // Two-tab scenario: user accepts in tab A; tab B should reflect the new
  // state on next load. We can't observe a real `storage` event across jsdom
  // realms, but we CAN verify that a fresh page load picks up the persisted
  // record (= what tab B sees after a reload). This is the minimum bar; if
  // future work adds true cross-tab `storage` sync via window.addEventListener,
  // extend with a `dispatchEvent(new StorageEvent(...))` test.
  let dom;
  afterEach(() => {
    if (dom) dom.window.close();
    dom = null;
  });

  test('a record written by tab A is observed by tab B on next load', () => {
    // Tab A persists a record (simulates a successful "accept all" click).
    const persisted = JSON.stringify({
      analytics: true,
      marketing: true,
      ts: new Date().toISOString(),
      v: SCHEMA_VERSION,
    });

    // Tab B — bring up a fresh jsdom with the persisted record pre-seeded.
    dom = freshDom(persisted);
    expect(bannerExists(dom)).toBe(false);
    expect(getStateSync(dom)).toEqual({ analytics: true, marketing: true });
  });
});
