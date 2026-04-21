import { describe, it, expect } from 'vitest';

/**
 * Backend smoke tests.
 *
 * Policy
 * ------
 * - If `BACKEND_URL` is NOT set, the whole suite is SKIPPED (describe.skipIf).
 *   Rationale: local devs shouldn't need backend credentials; CI can opt in
 *   by setting BACKEND_URL explicitly.
 * - If `BACKEND_URL` IS set, we FAIL LOUDLY on network errors. No silent
 *   try/catch — a mis-set URL should be visible, not hidden behind a warning.
 */

const BACKEND_URL = process.env.BACKEND_URL;
const TIMEOUT = 5000;

describe.skipIf(!BACKEND_URL)('API Smoke Tests [BACKEND_URL=%s]', () => {
  it('backend health endpoint responds with a non-5xx status', async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/health/status`, {
        signal: controller.signal,
      });
      expect(res.status).toBeLessThan(500);
    } finally {
      clearTimeout(timeoutId);
    }
  });

  it('DTC lookup endpoint returns valid JSON for a known code', async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/dtc/P0420`, {
        signal: controller.signal,
      });
      // Either the code is there (200) or the endpoint replies with a 4xx we
      // understand. A 5xx or unparseable body is a genuine smoke-test failure.
      expect(res.status).toBeLessThan(500);
      if (res.ok) {
        const data = await res.json();
        expect(data).toBeDefined();
        expect(typeof data).toBe('object');
      }
    } finally {
      clearTimeout(timeoutId);
    }
  });
});

// Informational: if BACKEND_URL isn't set, surface it once so CI logs
// don't look like "tests all passed, mystery" — they show a clear skip reason.
if (!BACKEND_URL) {
  // eslint-disable-next-line no-console
  console.warn(
    'api-smoke: BACKEND_URL not set -- skipping backend smoke tests. ' +
      'Set BACKEND_URL=https://... to enable.'
  );
}
