# AutoCognitix SEO — Files to Fix (with Paths)

## 🚨 CRITICAL FIXES REQUIRED

### 1. Missing Meta Descriptions (3 files)

#### File: `landing-page/en/legal/terms-of-service.html`
**Issue:** No meta description
**Current:** Empty
**Target:** "Terms of Service - AutoCognitix. Learn your rights, our responsibilities, and how to use our AI car diagnostics platform."
**Action:** Add `<meta name="description" content="...">`

#### File: `landing-page/en/legal/cookie-policy.html`
**Issue:** No meta description
**Current:** Empty
**Target:** "AutoCognitix Cookie Policy. Understand how we use cookies and tracking on our AI car diagnostics platform."
**Action:** Add `<meta name="description" content="...">`

#### File: `landing-page/en/legal/ai-disclaimer.html`
**Issue:** No meta description
**Current:** Empty
**Target:** "AI Disclaimer - AutoCognitix. Learn about limitations, reliability, and responsible use of our AI car diagnostics system."
**Action:** Add `<meta name="description" content="...">`

---

## 🔴 HIGH PRIORITY FIXES

### 2. Content Too Short (Expand to 2000+ words)

**These blog articles need expansion:**

1. `landing-page/hu/blog/index.html` — Current: 323 words | Target: 1000+ words
   - Add article previews with summaries
   - Add categories/topics section
   - Add author bios

2. `landing-page/en/blog/index.html` — Current: 103 words | Target: 1000+ words
   - Add featured articles section
   - Add category descriptions
   - Add blog stats/info

3. `landing-page/hu/blog/akkumulator-5-figyelmezteto-jel.html` — Current: 1418 | Target: 2000+
   - Add diagnostic procedures table
   - Expand "Common Mistakes" section
   - Add "Cost Breakdown" subsection

4. `landing-page/en/blog/5-signs-car-battery-dying.html` — Current: 1666 | Target: 2000+
   - Add battery replacement cost table
   - Expand troubleshooting guide
   - Add "When to DIY vs Professional Help"

5. `landing-page/hu/blog/ai-diagnosztika-hogyan-mukodik.html` — Current: 1573 | Target: 2000+
   - Expand AI methodology section
   - Add case studies (3-4)
   - Add comparison table (AI vs OBD2 scanner)

### 3. Missing External Links (Add 2-3 authority links to each)

**These articles need external links added:**

1. `landing-page/hu/blog/p0420-hibakod-utmutato.html` — Current: 0 | Add links to: NHTSA, auto manufacturer specs
2. `landing-page/hu/blog/akkumulator-5-figyelmezteto-jel.html` — Current: 0 | Add links to: battery manufacturer data, automotive standards
3. `landing-page/hu/blog/ai-diagnosztika-hogyan-mukodik.html` — Current: 0 | Add links to: AI research papers, diagnostic standards
4. `landing-page/en/blog/car-diagnostics-at-home-beginners-guide.html` — Current: 0 | Add links to: OBD2 standards, NHTSA guides
5. `landing-page/en/blog/dtc-trouble-code-lookup-guide.html` — Current: 0 | Add links to: SAE standards, OBD2 documentation
6. `landing-page/hu/blog/dtc-hibakod-kereso-teljes-utmutato.html` — Current: 0 | Add links to: Hungarian automotive authority, EU standards

### 4. Title Optimization (Adjust to 50-60 chars, include primary keyword)

**Landing pages - titles too long:**
- `landing-page/hu/index.html` — Current: 72 chars | Reduce & ensure "autódiagnosztika" present
- `landing-page/en/index.html` — Current: 70 chars | Reduce & ensure "car diagnostics" present

**Blog articles - missing target keywords in title:**
- `landing-page/en/blog/p0420-dtc-code-complete-guide.html` — Missing "catalytic converter" keyword
- `landing-page/en/blog/p0171-dtc-code-causes-symptoms-cost.html` — Missing "oxygen sensor" keyword

### 5. Missing Canonical URLs (Add to 7 pages)

Add `<link rel="canonical" href="...">` to:
1. `landing-page/hu/blog/dtc-hibakod-kereso-teljes-utmutato.html`
2. `landing-page/en/blog/dtc-trouble-code-lookup-guide.html`
3. `landing-page/hu/blog/autodiagnosztika-otthon-kezdoknek.html`
4. `landing-page/en/legal/privacy-policy.html`
5. `landing-page/en/legal/terms-of-service.html`
6. `landing-page/en/legal/cookie-policy.html`
7. `landing-page/en/legal/ai-disclaimer.html`

### 6. Missing Article Schema Markup (6 blog articles)

Add JSON-LD `<script type="application/ld+json">` with Article schema to:
1. `landing-page/hu/blog/ai-diagnosztika-hogyan-mukodik.html`
2. `landing-page/hu/blog/dtc-hibakod-kereso-teljes-utmutato.html`
3. `landing-page/hu/blog/autodiagnosztika-otthon-kezdoknek.html`
4. `landing-page/hu/blog/index.html`
5. `landing-page/en/blog/index.html`

### 7. Missing hreflang on one page

Add hreflang link to `landing-page/hu/blog/autodiagnosztika-otthon-kezdoknek.html`:
```html
<link rel="alternate" hreflang="en" href="/en/blog/car-diagnostics-at-home-beginners-guide/" />
```

---

## 🟠 MEDIUM PRIORITY FIXES

### 8. Trim Oversized Titles (15 pages)

Titles exceed 65 chars - trim to 50-60:
- `landing-page/hu/index.html`
- `landing-page/en/index.html`
- `landing-page/hu/blog/index.html`
- `landing-page/en/blog/index.html`
- `landing-page/hu/blog/p0420-hibakod-utmutato.html`
- `landing-page/hu/blog/ai-diagnosztika-hogyan-mukodik.html`
- `landing-page/hu/blog/p0171-hibakod-okok-tunetek-javitas.html`
- `landing-page/hu/blog/dtc-hibakod-kereso-teljes-utmutato.html`
- `landing-page/hu/blog/autodiagnosztika-otthon-kezdoknek.html`
- `landing-page/en/blog/p0420-dtc-code-complete-guide.html`
- `landing-page/en/blog/how-ai-car-diagnostics-works.html`
- `landing-page/en/blog/car-diagnostics-at-home-beginners-guide.html`

### 9. Trim Oversized Meta Descriptions (6 pages)

Meta descriptions exceed 165 chars - trim to 150-160:
- `landing-page/hu/index.html` (167 chars)
- `landing-page/en/index.html` (185 chars)
- `landing-page/hu/blog/index.html` (185 chars)
- `landing-page/en/blog/how-ai-car-diagnostics-works.html` (167 chars)
- `landing-page/hu/blog/dtc-hibakod-kereso-teljes-utmutato.html` (178 chars)
- `landing-page/en/blog/car-diagnostics-at-home-beginners-guide.html` (167 chars)

### 10. Fix Undersized Meta Description (1 page)

- `landing-page/en/legal/privacy-policy.html` — Current: 89 chars | Expand to 150-160

---

## 🟡 LOW PRIORITY FIXES

### 11. Add Open Graph & Twitter Card Tags (8 legal pages)

Add to:
1. `landing-page/hu/legal/adatvedelmi-szabalyzat.html`
2. `landing-page/hu/legal/felhasznalasi-feltetelek.html`
3. `landing-page/hu/legal/cookie-szabalyzat.html`
4. `landing-page/hu/legal/ai-felelossegi-nyilatkozat.html`
5. `landing-page/en/legal/privacy-policy.html`
6. `landing-page/en/legal/terms-of-service.html`
7. `landing-page/en/legal/cookie-policy.html`
8. `landing-page/en/legal/ai-disclaimer.html`

**Template:**
```html
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:type" content="website" />
<meta property="og:url" content="..." />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="..." />
<meta name="twitter:description" content="..." />
```

---

## 📊 SUMMARY TABLE

| Category | Files | Severity | Est. Time |
|----------|-------|----------|-----------|
| Missing meta descriptions | 3 | 🚨 Critical | 15 min |
| Content too short | 5 | 🔴 High | 3 hrs |
| Missing external links | 6 | 🔴 High | 2 hrs |
| Title optimization | 4 | 🔴 High | 1 hr |
| Missing canonical URLs | 7 | 🟠 Medium | 20 min |
| Missing Article schema | 6 | 🟠 Medium | 1 hr |
| Missing hreflang | 1 | 🟠 Medium | 10 min |
| Trim titles | 15 | 🟠 Medium | 1 hr |
| Trim descriptions | 6 | 🟠 Medium | 30 min |
| Add OG/Twitter cards | 8 | 🟡 Low | 1 hr |

**Total estimated implementation time: 10-11 hours**

---

**Generated:** 2026-03-21
**Base path:** `/sessions/clever-affectionate-hawking/mnt/AutoCognitix/`
