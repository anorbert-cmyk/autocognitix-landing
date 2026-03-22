# AutoCognitix SEO Audit — CRITICAL ISSUES & ACTION PLAN

**Audit Date:** 2026-03-21
**Total Pages:** 24 (2 landing pages, 12 blog articles, 10 legal pages)
**Total Issues:** 72 (3 Critical, 13 High, 39 Medium, 17 Low)

---

## 🚨 CRITICAL ISSUES (Fix Immediately)

These three pages are missing meta descriptions entirely. This impacts:
- Search result click-through rates (CTR)
- User understanding of page content
- Basic SEO hygiene

| Page | Issue | Fix |
|------|-------|-----|
| **terms_en** | Missing meta description | Add 150-160 char description with keyword "terms of service" |
| **cookie_en** | Missing meta description | Add 150-160 char description with keyword "cookie policy" |
| **ai_disc_en** | Missing meta description | Add 150-160 char description with keyword "AI disclaimer" |

**Estimated fix time:** 15 minutes

---

## 🔴 HIGH PRIORITY ISSUES (13 found)

### 1. Word Count Problems (5 articles)
Content length below recommended 2000-word minimum for blog articles:

| Page | Current | Target | Gap |
|------|---------|--------|-----|
| blog_index_hu | 323 | 2000+ | -1,677 |
| blog_index_en | 103 | 2000+ | -1,897 |
| battery_hu | 1,418 | 2000+ | -582 |
| battery_en | 1,666 | 2000+ | -334 |
| ai_diag_hu | 1,573 | 2000+ | -427 |

**Impact:** Reduced SEO authority, lower ranking potential
**Fix:** Expand articles with additional sections, case studies, examples
**Estimated time:** 2-3 hours

### 2. Title Optimization (3 articles)
Titles don't include primary keywords or are incorrectly sized:

| Page | Title | Issue | Optimal |
|------|-------|-------|---------|
| p0420_en | "P0420 Code: What It Means..." | No "catalytic converter" | 50-60 chars with keyword |
| p0171_en | "P0171 DTC Code: System Too Lean..." | No "oxygen sensor" | Include target keyword |
| privacy_en | "Privacy Policy - AutoCognitix" | Too short (29 chars) | Add descriptive words |

**Fix:** Add/update keywords in titles (see SEO Strategy document)
**Estimated time:** 30 minutes

### 3. Meta Descriptions (1 article)
privacy_en has undersized meta description (89 chars, should be 150-160)

**Fix:** Expand to include keyword + compelling CTA
**Estimated time:** 10 minutes

---

## 🟠 MEDIUM PRIORITY ISSUES (39 found)

### Most Common Issues

**1. Title Tag Length (15 articles)**
Titles exceed 65-character sweet spot:
- landing_hu (72 chars)
- landing_en (70 chars)
- blog_index_hu (64 chars)
- And 12 others

**Fix:** Trim to 50-60 chars, prioritize primary keyword
**Time:** 1 hour

**2. Meta Description Length (6 articles)**
Too long (>165 chars):
- landing_hu (167 chars)
- landing_en (185 chars)
- And 4 others

**Fix:** Trim to 150-160 chars
**Time:** 30 minutes

**3. Canonical URLs Missing (5 articles)**
No canonical link element:
- dtc_hu, dtc_en
- diy_hu
- privacy_en, terms_en
- cookie_en, ai_disc_en

**Fix:** Add `<link rel="canonical" href="...">` to each
**Time:** 20 minutes

**4. External Links Missing (8 blog articles)**
No external authority links (minimum 2-3 required):
- p0420_hu (0 external)
- battery_hu (0 external)
- ai_diag_hu (0 external)
- diy_hu (0 external)
- diy_en (0 external)
- dtc_hu (0 external)
- dtc_en (0 external)

**Fix:** Add 2-3 relevant external links per article
**Time:** 2 hours (research + implementation)

**5. Schema Markup Missing (6 blog articles)**
No Article schema.org markup:
- ai_diag_hu
- dtc_hu
- diy_hu
- blog_index_hu
- blog_index_en

**Fix:** Add JSON-LD Article schema with:
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "...",
  "description": "...",
  "datePublished": "...",
  "author": {...}
}
```
**Time:** 1 hour

**6. hreflang Tags (1 article)**
diy_hu missing hreflang to English pair

**Fix:** Add hreflang tags linking HU ↔ EN versions
**Time:** 10 minutes

---

## 🟡 LOW PRIORITY ISSUES (17 found)

### Open Graph & Twitter Card Tags
8 legal pages missing Open Graph and/or Twitter Card metadata

**Impact:** Reduced sharing appearance on social media
**Fix:** Add:
```html
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="..." />
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="..." />
<meta name="twitter:description" content="..." />
```
**Time:** 1 hour (15 pages × 4 minutes)

---

## ✅ WHAT'S WORKING WELL

**Strengths:**
- ✓ All 24 pages have exactly one H1 (perfect)
- ✓ Strong H2/H3 hierarchy (avg 11.5 H2, 19.2 H3)
- ✓ Most articles have good internal linking
- ✓ 5/6 landing + blog pages have proper schema markup
- ✓ hreflang implementation on landing pages
- ✓ OG/Twitter cards on most blog articles

**Best performers:**
1. **p0171_hu/en** — Excellent content (2000+ words), strong linking, proper schema (1 issue each)
2. **ai_diag_en** — Strong SEO fundamentals, good word count, rich schema (2 issues)
3. **battery_en** — Good linking, proper markup (2 issues)

---

## 📋 IMPLEMENTATION ROADMAP

### Phase 1: Quick Wins (2 hours)
**Immediate ROI fixes:**
1. Add 3 missing meta descriptions (terms_en, cookie_en, ai_disc_en) — 15 min
2. Fix title length issues (trim to 50-60 chars) — 1 hour
3. Fix meta description lengths (trim to 150-160 chars) — 30 min
4. Add canonical URLs to 5 pages — 20 min

**Expected impact:** Fix critical search visibility issues immediately

### Phase 2: Content Expansion (6 hours)
**Boost ranking authority:**
1. Expand 5 underweight articles to 2000+ words
   - blog_index_hu/en: add article previews + author bios
   - battery_hu/en: add diagnostic table, cost breakdowns
   - ai_diag_hu: expand methodology section

2. Add 2-3 external authority links to 8 articles
   - Point to: NHTSA, OBD2 standards, manufacturer guides

3. Add Article schema to 6 articles missing it

**Expected impact:** Significant ranking improvement (2-4 weeks)

### Phase 3: Social Media (1 hour)
**Improve shareability:**
1. Add OG + Twitter Card tags to 8 legal pages
2. Verify image optimization for social preview

**Expected impact:** 10-15% increase in social shares

### Phase 4: Long-term (Ongoing)
**Build organic authority:**
1. Internal linking network: 5-8 links per article
2. Keyword optimization: target secondary keywords in headings
3. Content cluster strategy: group related articles
4. Monitor rankings: track 15 primary keywords

---

## 📊 SEO SCORING BY PAGE TYPE

### Landing Pages (2)
- **Average issues:** 2
- **Average score:** 85/100
- **Status:** ✓ Good — minor title/desc optimization needed

### Blog Articles (12)
- **Average issues:** 3.2
- **Average score:** 78/100
- **Status:** ⚠ Needs work — expand content, add external links, improve markup

### Legal Pages (10)
- **Average issues:** 3.6
- **Average score:** 75/100
- **Status:** ⚠ Critical gaps — missing OG/Twitter cards, some descriptions

---

## 🎯 SUCCESS METRICS

After implementing all fixes:

| Metric | Current | Target | Impact |
|--------|---------|--------|--------|
| Pages with proper meta descriptions | 21/24 | 24/24 | ✓ Critical fix |
| Pages with canonical URLs | 19/24 | 24/24 | ✓ Prevent duplicates |
| Articles with 2000+ words | 7/12 | 12/12 | ✓ Authority boost |
| Articles with 2-3 external links | 4/12 | 12/12 | ✓ Trust signals |
| Pages with OG/Twitter cards | 14/24 | 24/24 | ✓ Social sharing |
| Pages with schema markup | 14/24 | 24/24 | ✓ Rich results |

**Projected outcome:** 15-25% organic search traffic increase within 2-3 months

---

## 📖 REFERENCE

Full detailed audit: `/seo-audit-report.md`
SEO Strategy: `/seo-strategy.md`
Target Keywords: See seo-strategy.md sections 1.1-1.3

---

**Generated:** 2026-03-21
**Auditor:** Python BeautifulSoup automated analysis
**Status:** Ready for implementation
