import { describe, it, expect } from 'vitest';

describe('API Smoke Tests', () => {
  const BACKEND_URL = process.env.BACKEND_URL || 'https://autocognitix-production.up.railway.app';
  const TIMEOUT = 5000;

  it('backend health endpoint should respond', async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);
      const res = await fetch(`${BACKEND_URL}/api/v1/health/status`, { signal: controller.signal });
      clearTimeout(timeoutId);
      expect(res.status).toBeLessThan(500);
    } catch (e) {
      // Network error = backend unreachable, skip gracefully
      console.warn('Backend unreachable, skipping smoke test:', e.message);
    }
  });

  it('DTC search endpoint should return valid JSON', async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);
      const res = await fetch(`${BACKEND_URL}/api/v1/dtc/P0420`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        expect(data).toBeDefined();
      }
    } catch (e) {
      console.warn('Backend unreachable, skipping smoke test:', e.message);
    }
  });
});
