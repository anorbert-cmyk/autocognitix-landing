import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as cheerio from 'cheerio';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');

/**
 * Create a jsdom environment with shared JS loaded.
 *
 * NOTE: Objects created inside the jsdom realm (via eval) live in a different
 * JavaScript realm than the test code. This means `instanceof` checks across
 * the boundary will fail (e.g., `window.Array !== Array`). Use duck-typing or
 * structured clone when passing objects between realms.
 */
export function createEnvironment() {
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    url: 'http://localhost:8080',
    runScripts: 'dangerously',
    resources: 'usable',
  });

  const { window } = dom;

  // Load vehicle-data.js
  const vehicleDataSrc = fs.readFileSync(path.join(ROOT, 'shared/js/vehicle-data.js'), 'utf-8');
  try {
    window.eval(vehicleDataSrc);
  } catch (err) {
    throw new Error(`Failed to eval shared/js/vehicle-data.js in jsdom: ${err.message}`);
  }

  // Load tool-common.js
  const toolCommonSrc = fs.readFileSync(path.join(ROOT, 'shared/js/tool-common.js'), 'utf-8');
  try {
    window.eval(toolCommonSrc);
  } catch (err) {
    throw new Error(`Failed to eval shared/js/tool-common.js in jsdom: ${err.message}`);
  }

  return {
    dom,
    window,
    VehicleDB: window.VehicleDB,
    ToolCommon: window.ToolCommon,
    /** Clean up jsdom resources. Call when done with this environment. */
    cleanup() {
      dom.window.close();
    },
  };
}

/**
 * Extract the last inline <script> block from an HTML file
 */
export function extractInlineScript(htmlRelPath) {
  const html = fs.readFileSync(path.join(ROOT, htmlRelPath), 'utf-8');
  const $ = cheerio.load(html);
  const scripts = $('script:not([src])');
  if (scripts.length === 0) throw new Error(`No inline scripts found in ${htmlRelPath}`);
  return scripts.last().html();
}

/**
 * Load an HTML tool page into a jsdom environment with forms stubbed.
 *
 * NOTE: See realm-crossing caveat in createEnvironment() above.
 */
export function loadToolPage(htmlRelPath) {
  const html = fs.readFileSync(path.join(ROOT, htmlRelPath), 'utf-8');
  const dom = new JSDOM(html, {
    url: 'http://localhost:8080',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
  });

  // Load shared JS into the page context
  const vehicleDataSrc = fs.readFileSync(path.join(ROOT, 'shared/js/vehicle-data.js'), 'utf-8');
  try {
    dom.window.eval(vehicleDataSrc);
  } catch (err) {
    throw new Error(`Failed to eval shared/js/vehicle-data.js in loadToolPage: ${err.message}`);
  }

  const toolCommonSrc = fs.readFileSync(path.join(ROOT, 'shared/js/tool-common.js'), 'utf-8');
  try {
    dom.window.eval(toolCommonSrc);
  } catch (err) {
    throw new Error(`Failed to eval shared/js/tool-common.js in loadToolPage: ${err.message}`);
  }

  return {
    dom,
    window: dom.window,
    /** Clean up jsdom resources. Call when done with this environment. */
    cleanup() {
      dom.window.close();
    },
  };
}

/**
 * Get the root directory path
 */
export function getRootDir() {
  return ROOT;
}
