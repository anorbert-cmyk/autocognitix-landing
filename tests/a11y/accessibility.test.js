import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { glob } from 'glob';
import * as cheerio from 'cheerio';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);

describe('Accessibility Basics (Static Analysis)', () => {
  const toolPages = [
    'hu/eszkozok/megeri-megjavitani.html',
    'hu/eszkozok/muszaki-vizsga-prediktor.html',
    'hu/eszkozok/szerviz-kereso.html',
    'en/tools/worth-repairing.html',
    'en/tools/mot-predictor.html',
    'en/tools/workshop-finder.html',
  ];

  toolPages.forEach(page => {
    const filePath = path.join(ROOT, page);
    if (!fs.existsSync(filePath)) return;

    describe(page, () => {
      const html = fs.readFileSync(filePath, 'utf-8');
      const $ = cheerio.load(html);

      it('should have a lang attribute on html element', () => {
        expect($('html').attr('lang')).toBeTruthy();
      });

      it('should have a title element', () => {
        expect($('title').text().length).toBeGreaterThan(0);
      });

      it('should have meta viewport', () => {
        expect($('meta[name="viewport"]').length).toBeGreaterThan(0);
      });

      it('should have form labels for inputs', () => {
        const inputs = $('input[type="text"], input[type="number"], select').not('[type="hidden"]');
        inputs.each((_, el) => {
          const id = $(el).attr('id');
          if (id) {
            const hasLabel = $(`label[for="${id}"]`).length > 0;
            const isWrappedInLabel = $(el).closest('label').length > 0;
            const hasAriaLabel = $(el).attr('aria-label') || $(el).attr('aria-labelledby');
            expect(hasLabel || isWrappedInLabel || hasAriaLabel).toBe(true);
          }
        });
      });

      it('should have submit buttons with accessible text', () => {
        const buttons = $('button[type="submit"], input[type="submit"]');
        buttons.each((_, el) => {
          const text = $(el).text().trim() || $(el).attr('value') || $(el).attr('aria-label');
          expect(text).toBeTruthy();
        });
      });
    });
  });
});
