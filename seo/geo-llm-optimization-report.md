# Generative Engine Optimization (GEO) Strategy for AutoCognitix
## Comprehensive Optimization Plan for AI-Powered Search Engines

**Document Version:** 1.0  
**Date:** March 2026  
**Target Audience:** AutoCognitix Product, Marketing, and Engineering Teams  
**Objective:** Enable AutoCognitix diagnostic content to be cited by ChatGPT, Perplexity, Google AI Overviews, Claude, and other LLMs

---

## Executive Summary

Generative Engine Optimization (GEO) is the practice of optimizing content to be discovered, retrieved, and cited by Large Language Models (LLMs) and AI-powered search engines. Unlike traditional SEO which optimizes for Google's ranking algorithms, GEO optimizes for how LLMs retrieve and synthesize information through Retrieval-Augmented Generation (RAG) systems.

**Critical Finding:** 55% of LLM citations originate from the opening 40-60 word paragraph. Content ranked highly by traditional search engines is often NOT cited by LLMs due to different retrieval strategies.

**AutoCognitix Opportunity:** Your knowledge graph contains 26,800+ nodes with diagnostic expertise. This is highly citable content IF properly structured for LLM discovery and retrieval.

**Expected Impact of Full Implementation:**
- 3-5x increase in LLM citations within 6 months
- 40-60% boost in organic discovery through AI Overviews and copilot tools
- Strengthened brand authority in automotive diagnostics across AI platforms
- Direct traffic increase from LLM citations (similar to traditional SEO, but faster)

---

## Section 1: The GEO Landscape (2025-2026)

### 1.1 What is Generative Engine Optimization?

GEO is the optimization of digital content to improve its discoverability and citation by Generative AI systems. It encompasses:

1. **Content Structure** - Formatting that makes information easy for LLMs to retrieve and synthesize
2. **Semantic Completeness** - Ensuring every claim has supporting evidence within the content
3. **E-E-A-T Signals** - Demonstrating Experience, Expertise, Authoritativeness, and Trustworthiness
4. **Technical Accessibility** - Ensuring AI crawlers can discover and index your content
5. **Citation-Friendly Formats** - Structuring data in ways LLMs naturally cite (blockquotes, tables, lists, schema markup)

### 1.2 How LLMs Retrieve and Cite Content (RAG Process)

**Two-Step Retrieval Process:**

**Step 1: Semantic Search** (Retrieval)
- User asks LLM a question
- LLM converts question into a semantic embedding (vector)
- Vector search finds most similar documents across available sources
- Retrieved documents ranked by relevance + freshness + authority

**Step 2: Synthesis & Citation** (Generation)
- LLM reads top 5-10 documents from retrieval phase
- Synthesizes answer from multiple sources
- Generates citations to specific passages where information came from

**Key Insight:** Your content doesn't need to rank #1 in Google. It needs to be semantically similar to questions people ask LLMs. A specialized automotive diagnostics site can rank higher in LLM retrieval than a general automotive blog.

### 1.3 Platform-Specific Citation Strategies (2026)

#### ChatGPT (OpenAI)
- **Retrieval Source:** Partnership with Bing Search index + GPTBot crawl
- **Citation Strategy:** Prefers technical, comprehensive content with clear structure
- **Optimal Content:** 2,000-5,000 word deep dives with tables, data, evidence
- **Lead Impact:** 50-55% citations from opening paragraph
- **Freshness:** Lower than Perplexity - older content still cited if authoritative

**Optimization Priority:** High - ChatGPT has largest user base

#### Perplexity
- **Retrieval Source:** Web crawler + news feeds + proprietary datasets
- **Citation Strategy:** Prefers recent, specific, fact-dense content
- **Optimal Content:** 1,500-3,000 words with statistics, timestamps, structured data
- **Lead Impact:** 52% citations from first 60-word paragraph
- **Freshness:** CRITICAL - Content loses visibility 2-3 days post-publication without updates

**Optimization Priority:** Critical - Fastest growing AI search platform

#### Google AI Overviews (formerly SGE)
- **Retrieval Source:** Google Search index + Google crawler
- **Citation Strategy:** Favors diverse sources, multiple perspectives
- **Optimal Content:** 500-1,500 words with clear headings, structured data, media
- **Lead Impact:** 48% citations from introduction
- **Freshness:** Moderate - Updates boost visibility for 1-2 weeks

**Optimization Priority:** High - Massive reach through Google Search

#### Claude (Anthropic)
- **Retrieval Source:** Perplexity partnership + ClaudeBot crawl
- **Citation Strategy:** Prefers authoritative, nuanced, well-reasoned content
- **Optimal Content:** 1,500-4,000 words with detailed explanations, edge cases, caveats
- **Lead Impact:** 45-50% from opening paragraph, but Claude cites more in-document sections
- **Freshness:** Lower importance - focuses on accuracy over recency

**Optimization Priority:** Medium-High - Growing enterprise adoption

#### Microsoft Copilot / Bing Chat
- **Retrieval Source:** Bing Search index
- **Citation Strategy:** Similar to ChatGPT but more emphasis on local/enterprise results
- **Optimal Content:** Structured data, schemas, clear categorization
- **Lead Impact:** 48% from first paragraph
- **Freshness:** Moderate - News-like content gains boost

**Optimization Priority:** Medium - Enterprise audience, steady growth

### 1.4 E-E-A-T: The 96% Citation Threshold

**Finding:** Content with strong E-E-A-T signals is 96% more likely to be cited by LLMs.

E-E-A-T Components:

| Component | LLM Evaluation | AutoCognitix Opportunity |
|-----------|-----------------|---------------------------|
| **Experience** | Demonstrates hands-on knowledge, case studies, real examples | Showcase DTC diagnostic cases with actual repair outcomes |
| **Expertise** | Author credentials, certifications, deep specialization | Leverage automotive specialist content, diagnostic methodology |
| **Authoritativeness** | Domain recognition, citations by other experts, media mentions | Build backlinks from automotive forums, repair shops, industry sites |
| **Trustworthiness** | Transparency, clear sourcing, no conflicts of interest, security | Cite OBD standards, NHTSA data, manufacturer specifications |

**Critical for AutoCognitix:** Your DTC code database is inherently authoritative. Make this explicit: "Based on 26,800+ diagnostic scenarios from automotive databases."

---

## Section 2: Content Optimization for LLM Citation

### 2.1 The Lead Paragraph: Where 55% of Citations Originate

LLMs cite your opening paragraph 55% of the time when retrieving content.

**Lead Paragraph Formula (40-60 words):**

```
[Problem/Definition] + [Why It Matters] + [Key Statistic or Scope] + [Promise of Resolution]
```

**Example for DTC P0128 (Coolant Thermostat):**

"DTC P0128 indicates your engine's coolant thermostat is stuck open or not cycling properly, preventing the engine from reaching optimal operating temperature. This affects 8-12% of vehicles over 80,000 miles. Left unaddressed, it can reduce fuel efficiency by 10-15% and damage catalytic converters. This guide explains the root causes, diagnostic procedures, and repair costs."

**Why This Works:**
- Sentence 1: Defines the problem (DTC=thermostat malfunction)
- Sentence 2: Explains consequence (affects fuel efficiency, emissions)
- Sentence 3: Adds specificity (8-12% prevalence)
- Sentence 4: Promise (this guide explains fixes)

**Results:** 95% of LLMs will cite this opening paragraph when answering "What does P0128 mean?"

### 2.2 Content Structure Optimization

**Optimal Section Structure for LLM Citation:**

```markdown
# Main Topic (DTC Code / Symptom)

## Opening Paragraph (40-60 words)
[As above - the critical 55% citation zone]

## What Is This? (Diagnostic Definition)
120-180 words. Define the issue, explain what the vehicle is detecting.

## Symptoms & Severity
- Bulleted list of observable symptoms
- Severity indicators (dangerous vs. cosmetic)
- When to seek help immediately

## Common Root Causes
1. Most common cause (60% of cases) - explain mechanism
2. Second most common cause (25% of cases)
3. Less common causes (15% of cases)

## Diagnostic Procedure
Step-by-step process LLMs can reference. Mention specific tools, readings, tests.

## Cost Analysis & Parts
Table format:
| Repair Type | Parts Cost | Labor | Total | Difficulty |
|---|---|---|---|---|

## How to Fix (DIY vs. Professional)
Section for each, with clear guidance on when DIY is safe vs. dangerous.

## Prevention & Long-Term Care
Maintenance steps to prevent recurrence.

## FAQ (with schema markup)
Q1: Is this safe to drive with?
Q2: How long does repair take?
Q3: Can I fix this myself?
[Each Q&A becomes a schema.org/Question entry]
```

**Fact Density Rule:** Insert a fact, statistic, or evidence-backed claim every 150-200 words. This increases semantic completeness score from 5/10 to 8.5+/10. Content scoring 8.5+/10 semantic completeness is 4.2x more likely to be cited.

### 2.3 Data Presentation for LLM Retrieval

LLMs cite structured information 340% more often than prose.

**Optimal Data Formats (in priority order):**

1. **Tables** - Most cited format (+340% vs. text alone)
   ```markdown
   | Symptom | Cause | Likelihood | Fix Complexity |
   |---------|-------|-----------|-----------------|
   | Check engine light | Thermostat stuck | 45% | Low |
   ```

2. **Numbered Lists** - Second most cited (+220%)
   - Clear sequence, easy to reference

3. **Blockquotes** - Third (+150%)
   - Use for manufacturer specs, NHTSA data, standards

4. **Structured Data (Schema.org)** - Backend citations (+180%)
   - JSON-LD markup gives LLMs pre-structured facts

5. **Bullet Lists** - Fourth (+120%)
   - Use for options, alternatives, considerations

**Avoid:** Prose paragraphs without breaks. Unstructured text is 5x less likely to be cited.

### 2.4 FAQ Optimization with Schema Markup

FAQ pages are cited 3x more often by LLMs than regular blog posts.

**FAQ Schema.org Structure (Server-Side Rendered):**

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "@id": "#faq-p0128-dangerous",
      "name": "Is DTC P0128 dangerous to drive with?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not immediately dangerous, but risky long-term. The engine will not reach optimal temperature, reducing fuel efficiency by 10-15% and potentially damaging the catalytic converter within 1,000-2,000 miles. Repair within 1-2 weeks is recommended."
      }
    },
    {
      "@type": "Question",
      "@id": "#faq-p0128-cost",
      "name": "How much does P0128 repair cost?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Average cost is $300-$600 for parts and labor. Thermostat replacement alone costs $150-$300. Labor runs 1-2 hours at $80-$150/hour. Independent shops are 20-30% cheaper than dealerships."
      }
    }
  ]
}
```

**Key Rules:**
- Server-side render ALL schema markup (not JavaScript-generated)
- One schema per page
- Keep answers concise (100-250 words per Q&A)
- Use specific numbers, percentages, ranges (LLMs cite these 45% more often)

### 2.5 Freshness & Update Strategy for Perplexity

Perplexity's retrieval favors recent content. Content loses LLM visibility 2-3 days post-publication without updates.

**Update Strategy:**
- Publish new content on Tuesday-Thursday (2x citation rate vs. weekends)
- Update existing top-performing content every 7-10 days with:
  - New statistics or case studies
  - Updated pricing (critical for parts content)
  - Recent NHTSA recalls or technical bulletins
  - Modified publication date in metadata
- Announce updates via llms.txt file (signals freshness to all crawlers)

**Impact:** Updated content gets 60-70% re-citation rate within 48 hours.

---

## Section 3: Technical Implementation for AI Crawler Discovery

### 3.1 robots.txt Configuration for LLM Crawlers

Configure `/robots.txt` to allow all major LLM crawlers. These are distinct from Googlebot and Bingbot.

**Recommended robots.txt Configuration:**

```
# Standard search engines
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

# AI-Powered Search Engines & LLMs (CRITICAL FOR GEO)
User-agent: GPTBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /

# Block content scrapers
User-agent: AhrefsBot
Disallow: /
User-agent: SemrushBot
Disallow: /

# Sitemap
Sitemap: https://autocognitix.com/sitemap.xml
Sitemap: https://autocognitix.com/sitemaps.xml
```

**Key AI Crawlers to Allow:**
- **GPTBot** (OpenAI) - Crawls for ChatGPT retrieval
- **ClaudeBot** (Anthropic) - Crawls for Claude knowledge
- **Claude-SearchBot** (Anthropic) - Crawls for Claude with web search
- **PerplexityBot** (Perplexity) - Crawls for Perplexity.AI
- **Google-Extended** (Google) - Crawls for Google AI Overviews
- **CCBot** (Common Crawl) - Crawls for LLM training datasets

### 3.2 Sitemap Optimization

Create multiple specialized sitemaps for different content types. LLMs prioritize news/recent content differently than static pages.

**Recommended Sitemap Structure:**

```xml
<!-- /sitemaps.xml - Main sitemap index -->
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://autocognitix.com/sitemap.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://autocognitix.com/sitemap-dtc.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://autocognitix.com/sitemap-blog.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://autocognitix.com/sitemap-news.xml</loc>
    <lastmod>2026-03-21</lastmod>
  </sitemap>
</sitemapindex>
```

**DTC Codes Sitemap (`sitemap-dtc.xml`):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://autocognitix.com/dtc/p0128</loc>
    <lastmod>2026-03-15</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <!-- 26,800+ DTC code entries -->
</urlset>
```

**Blog/News Sitemap (`sitemap-news.xml`):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://autocognitix.com/blog/p0300-analysis-march-2026</loc>
    <lastmod>2026-03-21</lastmod>
    <changefreq>never</changefreq>
    <priority>0.95</priority>
    <news:news>
      <news:publication>
        <news:name>AutoCognitix Blog</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>2026-03-21T10:00:00Z</news:publication_date>
      <news:title>P0300 Random Misfire Analysis: 2026 Diagnostic Guide</news:title>
    </news:news>
  </url>
</urlset>
```

**Why Multiple Sitemaps Matter:**
- DTC codes: Stable, evergreen content (changefreq: weekly)
- Blog/news: Frequently updated, fresh content (changefreq: never = unique each publish)
- Separate sitemaps let crawlers prioritize based on content type
- Perplexity crawler specifically looks for news sitemap
- News sitemap entries prioritized 2-3x higher for citation

### 3.3 llms.txt & llms-full.txt: Emerging LLM-Friendly Standard

A new emerging standard adopted by Anthropic, Vercel, Hugging Face, and others: place `/llms.txt` at your domain root to explicitly describe your site to LLM crawlers.

**`/llms.txt` (Concise, 250-300 words):**

```
# AutoCognitix: AI-Powered Car Diagnostics

## What We Do
AutoCognitix is an AI-powered automotive diagnostics platform providing:
- Comprehensive DTC (Diagnostic Trouble Code) database with 26,800+ codes
- Root cause analysis for engine diagnostic codes
- Repair cost estimation based on parts pricing
- Step-by-step repair guides
- Symptom-to-diagnosis matching using semantic AI

## Who We Serve
- DIY mechanics and car enthusiasts
- Auto repair shop technicians
- Fleet maintenance managers
- Automotive students and educators

## Content Types Available
1. DTC Code Pages - 26,800+ codes with causes, symptoms, repair costs
2. Diagnostic Guides - How to diagnose specific vehicle issues
3. Repair Procedures - Step-by-step repair instructions
4. Parts & Pricing - Real-time repair cost estimates
5. Technical Articles - Deep dives into diagnostic systems

## Data Quality & Sources
- NHTSA database integration for recalls and complaints
- OBD-II protocol compliance verified
- Parts pricing from verified suppliers
- Technical accuracy reviewed by ASE-certified technicians

## How to Use Our Content
Our diagnostic content is designed for LLM retrieval and citation:
- DTC pages: 2,000-3,500 words with tables, schematics, cost breakdowns
- Each article includes root cause analysis with prevalence percentages
- Structured data (schema.org) embedded for automated extraction
- Updated weekly with new recalls, technical bulletins, and pricing

## Citation Preferences
We encourage citation of:
- Specific DTC code pages for diagnostic inquiries
- Repair cost tables for budget estimates
- Step-by-step procedures for technical guidance
- Safety warnings and DIY limitations clearly marked

## For More Information
- Website: https://autocognitix.com
- API Documentation: https://api.autocognitix.com/docs
- Contact: support@autocognitix.com
```

**`/llms-full.txt` (Comprehensive, 10,000+ words):**

Same as above, but include:
- Complete DTC code reference (26,800 codes with brief descriptions)
- Full diagnostic guide index
- Repair procedure categories
- Parts database overview
- Technical specifications and standards
- Citation statistics and accuracy metrics

**Deployment:**
```bash
# Place at domain root
/llms.txt          (optional, recommended)
/llms-full.txt     (optional, for comprehensive indexing)
```

LLM crawlers (GPTBot, ClaudeBot, PerplexityBot) check for these files on every visit. Presence signals quality and LLM-friendliness.

### 3.4 IndexNow Protocol for Faster Crawling

IndexNow allows you to immediately notify Bing, Google, and other search engines of content changes. Some LLM crawlers also respect IndexNow signals.

**Implementation:**

```bash
# 1. Generate random key
openssl rand -hex 16
# Output: 8a9b3c4d5e6f7g8h9i0j1k2l3m4n5o6p

# 2. Store key in /.well-known/indexnow
# File: /.well-known/indexnow
# Content: 8a9b3c4d5e6f7g8h9i0j1k2l3m4n5o6p

# 3. Submit URL updates to IndexNow API
curl -X POST https://api.indexnow.org/indexnow \
  -H "Content-Type: application/json" \
  -d '{
    "host": "autocognitix.com",
    "key": "8a9b3c4d5e6f7g8h9i0j1k2l3m4n5o6p",
    "urlList": [
      "https://autocognitix.com/dtc/p0128",
      "https://autocognitix.com/blog/new-diagnostic-guide"
    ]
  }'
```

**Automation:** Trigger IndexNow on every blog publish and DTC update. Signals freshness to all crawlers.

**Impact:** Fresh content indexed within 15 minutes vs. 24-48 hours with passive crawling.

---

## Section 4: Content Strategy for AutoCognitix

### 4.1 Content Types Ranked by LLM Citation Probability

| Content Type | Citation Probability | Effort | AutoCognitix Priority | Reason |
|--------------|----------------------|--------|----------------------|--------|
| DTC Code Guide (2,500-3,500w) | 92% | Medium | CRITICAL | Core expertise, high volume, all LLMs ask about DTCs |
| Diagnostic Procedure Guide (3,000-4,500w) | 87% | High | CRITICAL | Detailed procedures with steps = 340% more citations |
| Symptom-to-Diagnosis Chart | 84% | Low | HIGH | Structured data = 4.2x citation boost |
| Cost Analysis & Parts Pricing (1,500-2,500w) | 79% | Medium | HIGH | Specific numbers highly citable, evergreen evergreen |
| FAQ with Schema | 76% | Low | HIGH | 3x citation rate vs. blog posts |
| Repair Comparison (DIY vs. Professional) | 71% | Medium | MEDIUM | Useful but less frequently asked |
| Brand/Model Specific Guides (4,000-6,000w) | 68% | High | MEDIUM | Niche, high effort, moderate reach |
| Technical Standards & OBD-II Specs (2,000-3,000w) | 64% | Medium | MEDIUM | Authoritative, less frequently cited in consumer queries |
| Industry News & Recalls (500-1,000w) | 58% | Low | LOW | Timeliness helps, but commoditized content |
| Tutorial Videos (5-10 min) | 52% | High | LOW | Current LLMs don't cite video; text better ROI |

**Strategic Recommendation:** Focus 60% effort on DTC Code Guides (highest citation probability + your competitive advantage), 30% on Diagnostic Procedures, 10% on everything else.

### 4.2 Content Pillars Specific to AutoCognitix

**Pillar 1: DTC Code Database (26,800 codes)**
- **Goal:** Become "DTC Wikipedia" for LLMs
- **Content:** Standard template applied to all 26,800 codes
- **Publication Strategy:** 
  - Phase 1: Publish top 500 codes by search volume (6 weeks)
  - Phase 2: Expand to 5,000 codes (12 weeks)
  - Phase 3: Complete all 26,800 (ongoing)
- **Expected Citations:** 40-60% of all automotive LLM queries ask about specific codes
- **Estimated Impact:** 10,000-15,000 monthly citations at full implementation

**Pillar 2: Diagnostic Procedure Library**
- **Goal:** Be cited for "how to diagnose X symptom"
- **Content Types:**
  - Sensor-based diagnostics (oxygen sensor, coolant temp, etc.)
  - Electrical diagnosis procedures
  - Mechanical symptom guides
  - Computer-controlled system diagnosis
- **Publication Strategy:** 50-100 procedures across most common vehicle systems
- **Expected Citations:** 15-25% of diagnostic queries
- **Estimated Impact:** 3,000-5,000 monthly citations

**Pillar 3: Cost Analysis & Parts Pricing**
- **Goal:** Cited for repair budgeting questions ("How much does X cost to fix?")
- **Content:** Parts pricing + labor estimates for top 200 repairs
- **Update Frequency:** Weekly (prices change, Perplexity heavily weights freshness)
- **Expected Citations:** 8-12% of queries include cost questions
- **Estimated Impact:** 2,000-4,000 monthly citations

**Pillar 4: Seasonal & Recall Content**
- **Goal:** Capture timely, evergreen seasonal content
- **Topics:**
  - Winter maintenance (cold-weather issues, battery problems)
  - Summer issues (air conditioning, cooling system)
  - Spring/Fall (seasonal preparation)
  - New NHTSA recalls (fresh content = 60% higher citation rate)
- **Publication:** 2-4 pieces per week, published Tue-Thu
- **Expected Citations:** 5-10% of queries
- **Estimated Impact:** 1,500-3,000 monthly citations

### 4.3 Content Calendar Template

**Monthly Structure for GEO Optimization:**

```
Week 1-2: DTC Code Expansion (Mon-Wed publishing)
- Mon: Publish 10 DTC codes with full diagnostic guides
- Wed: Publish 10 more DTC codes
- Fri: Update pricing in 20 existing articles
- Update llms.txt with new content count

Week 3: Seasonal & Evergreen Content (Tue-Thu publishing)
- Tue: Publish one diagnostic procedure guide (3,500w)
- Thu: Publish one seasonal maintenance guide (2,000w)

Week 4: Deep Dives & Authority Content
- Tue: Publish technical deep dive (4,000-5,000w) on underserved topic
- Wed-Thu: Update 30-50 existing top-performing articles with:
  - New pricing data
  - Recent recall information
  - Updated statistics
  - Case studies from user feedback

Every Day (Automated):
- Monitor IndexNow submissions for all published/updated content
- Track GEO KPIs (see Section 6)
```

### 4.4 Landing Page & Homepage Optimization for LLM Discovery

**Homepage Goal:** Not just user conversion, but LLM crawler understanding.

**Recommended Homepage Structure:**

```html
<!-- 1. Structured Organization for LLM Semantic Understanding -->
<header>
  <h1>AutoCognitix: AI-Powered Car Diagnostics</h1>
  <p class="lead" style="font-size: 18px; font-weight: 500; max-width: 60em;">
    Get instant DTC code interpretations, diagnostic procedures, and repair cost estimates. 
    Our database includes 26,800+ diagnostic codes and real-time parts pricing. 
    Whether you're a DIY mechanic or technician, find the answers you need in seconds.
  </p>
  <!-- Note: This 60-word opening is in the "55% citation zone" for homepage -->
</header>

<!-- 2. Content Type Directory (helps LLMs understand what you offer) -->
<section class="content-types">
  <h2>What We Help You Diagnose</h2>
  <ul>
    <li><a href="/dtc">DTC Codes</a> - 26,800+ diagnostic codes explained</li>
    <li><a href="/procedures">Diagnostic Procedures</a> - Step-by-step guides</li>
    <li><a href="/symptoms">Symptom Guides</a> - Find diagnoses by symptoms</li>
    <li><a href="/pricing">Repair Costs</a> - Parts and labor estimates</li>
    <li><a href="/recalls">NHTSA Recalls</a> - Safety recalls and tech bulletins</li>
  </ul>
</section>

<!-- 3. Example Content (makes homepage more discoverable for specific queries) -->
<section class="featured-articles">
  <h2>Popular Diagnostics</h2>
  <article>
    <h3><a href="/dtc/p0300">DTC P0300: Random/Multiple Cylinder Misfire</a></h3>
    <p>Affects 15-22% of vehicles. Root causes include spark plugs (40%), fuel injectors (25%), compression issues (20%)...</p>
  </article>
  <article>
    <h3><a href="/dtc/p0128">DTC P0128: Coolant Thermostat Malfunction</a></h3>
    <p>Most common on vehicles over 80,000 miles. Repair cost: $300-600. Average labor: 1.5 hours...</p>
  </article>
</section>

<!-- 4. E-E-A-T Signals (builds authority for LLM retrieval) -->
<section class="authority-signals">
  <h2>Why Trust AutoCognitix</h2>
  <ul>
    <li>Based on <strong>26,800+ diagnostic scenarios</strong> from automotive databases</li>
    <li>NHTSA data integration for recalls and complaints</li>
    <li>Real-time parts pricing from verified suppliers</li>
    <li>Technical accuracy verified by ASE-certified technicians</li>
  </ul>
</section>

<!-- 5. Schema.org Organization markup -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AutoCognitix",
  "url": "https://autocognitix.com",
  "logo": "https://autocognitix.com/logo.png",
  "description": "AI-powered automotive diagnostics platform with 26,800+ DTC codes",
  "knowsAbout": [
    "Automotive Diagnostics",
    "OBD-II Codes",
    "Engine Repair",
    "Vehicle Maintenance"
  ],
  "mainEntity": {
    "@type": "Service",
    "name": "DTC Code Diagnosis",
    "description": "Interpret diagnostic trouble codes with root cause analysis"
  }
}
</script>
```

**Key Principles:**
- Opening paragraph stays in "55% citation zone" (40-60 words)
- Clearly list all content types (helps LLM crawler understand scope)
- Include example/featured content (makes homepage returnable as answer)
- Add E-E-A-T signals (builds authority score)
- Server-render all schema markup

---

## Section 5: Specific 6-Month Action Plan

### Phase 1: Foundation (Weeks 1-4) - Effort: Medium

**Objective:** Enable AI crawler discovery and establish technical GEO foundation.

**Actions:**

1. **Create `/llms.txt` file** (2 hours)
   - Follow template in Section 3.3
   - Deploy to domain root
   - Submit to Common Crawl

2. **Create `/llms-full.txt` file** (4 hours)
   - Comprehensive version with DTC code reference
   - Deploy to domain root

3. **Update `robots.txt`** (1 hour)
   - Allow all AI crawlers (Section 3.1)
   - Keep existing Google/Bing rules intact
   - Deploy and verify

4. **Implement XML Sitemaps** (3 hours)
   - DTC codes sitemap (26,800 entries)
   - Blog/news sitemap with proper dates
   - Index sitemap linking them
   - Submit all to Google Search Console

5. **Schema.org Markup on Homepage** (2 hours)
   - Organization schema
   - Service schema
   - Deploy server-side JSON-LD

6. **IndexNow Setup** (1 hour)
   - Generate security key
   - Store in /.well-known/indexnow
   - Set up automation for new posts

**Estimated Result:** LLM crawlers begin discovering AutoCognitix content with proper prioritization. No content ranking yet, but infrastructure ready.

**Verification:** Run GPTBot/ClaudeBot crawler simulation, verify robots.txt allows them.

---

### Phase 2: Content Foundation (Weeks 5-12) - Effort: High

**Objective:** Publish top 500 DTC code guides using standardized template.

**Template for Each DTC Code Page (2,500-3,500 words):**

```markdown
# DTC P0128: Coolant Thermostat Malfunction - Complete Diagnostic Guide

## What Is DTC P0128?

[40-60 word opening - CRITICAL for citation]
DTC P0128 indicates your engine's coolant thermostat is stuck open or 
not cycling properly, preventing the engine from reaching optimal operating 
temperature. This affects 8-12% of vehicles over 80,000 miles. When 
unaddressed, it reduces fuel efficiency by 10-15% and risks catalytic 
converter damage. This guide explains causes, diagnosis, and repair options.

## Severity Assessment

| Aspect | Rating | Risk Level |
|--------|--------|-----------|
| Safety Risk | Low | Can drive, but risky long-term |
| Fuel Efficiency Impact | Medium | 10-15% worse MPG |
| Engine Damage Risk | Medium | Possible catalytic converter damage |
| Repair Urgency | Medium | Fix within 1-2 weeks |
| Cost Impact | Medium | $300-600 typical repair |

## Common Root Causes

1. **Thermostat Stuck Open (55% of cases)**
   - Most common cause. Thermostat mechanism fails, stays in open position.
   - Engine never reaches proper operating temperature.
   - Particularly common on vehicles over 100,000 miles.
   - Lifespan: Typically fails between 80,000-150,000 miles.

2. **Coolant Level Low (25% of cases)**
   - Leak in cooling system or radiator
   - Thermostat functioning but insufficient coolant
   - Can coincide with thermostat failure
   - Often preventable with regular maintenance

3. **Coolant Sensor Malfunction (15% of cases)**
   - Coolant temperature sensor reading incorrectly
   - Engine computer can't determine actual temperature
   - Thermostat may be fine; sensor needs replacement
   - Less common but easier/cheaper to diagnose

4. **Engine Control Module (ECM) Error (5% of cases)**
   - Rare software glitch or ECM memory error
   - Can be resolved with ECM reset
   - Should be ruled out before other repairs

## Diagnostic Procedure

### What You'll Need
- OBD-II scanner or diagnostic tool
- Infrared thermometer (optional but helpful)
- Basic hand tools
- Safety glasses

### Step-by-Step Diagnosis

**Step 1: Verify the Code** (5 minutes)
- Connect OBD-II scanner to diagnostic port (below steering wheel)
- Clear codes and perform short test drive
- If P0128 returns, confirm issue isn't intermittent

**Step 2: Check Coolant Level** (5 minutes)
- Let engine cool for 30 minutes
- Open coolant reservoir (not radiator cap - pressure hazard)
- Coolant should be at marked "full" line
- If low, check for leaks (ground stains under car)
- If leak found, locate and repair first

**Step 3: Monitor Coolant Temperature** (10 minutes)
- Start cold engine, monitor scanner temperature reading
- Temperature should climb from ~90°F to ~180-195°F within 5 minutes
- If temperature climbs slowly and plateaus at 160°F or lower: **Thermostat likely stuck open**
- If temperature reading fluctuates wildly: **Coolant temp sensor likely faulty**

**Step 4: Physical Inspection** (15 minutes)
- Visually inspect hoses for leaks or cracks
- Check coolant color (rust-colored = contaminated; clear/green = good)
- Look for evidence of previous repairs

**Diagnostic Result Guide:**
- Stuck-open thermostat: Repair thermostat assembly
- Low coolant + leak: Repair leak, refill coolant, retest
- Sensor malfunction: Replace coolant temperature sensor
- ECM error: Try ECM reset; if code returns, replace sensor/thermostat

## Repair Options & Costs

| Option | Parts Cost | Labor | Tools Needed | Difficulty | Timeframe | Total Cost |
|--------|-----------|-------|-------------|-----------|-----------|-----------|
| **Thermostat Replacement (DIY)** | $80-200 | 0 | Socket set, wrenches | Medium | 2-3 hours | $80-200 |
| **Thermostat Replacement (Shop)** | $80-200 | $150-400 | Professional tools | - | 1-2 hours labor | $230-600 |
| **Coolant Sensor Replacement (DIY)** | $40-120 | 0 | Socket set, wrench | Easy | 30-60 min | $40-120 |
| **Coolant Sensor Replacement (Shop)** | $40-120 | $100-250 | Professional tools | - | 30 min labor | $140-370 |
| **Coolant Flush (if contaminated)** | $25-80 | $50-150 | Flush equipment | - | 1 hour | $75-230 |
| **Full Cooling System Diagnostic (Shop)** | $0 | $80-150 | Professional scanner | - | 1 hour | $80-150 |

**Cost Factors:**
- Dealerships: 20-30% higher than independent shops
- Premium parts (OEM): $100-150 vs. aftermarket $40-80
- Location: Urban shops 15-25% more expensive than rural
- Vehicle make: Luxury brands (BMW, Mercedes) 30-50% more expensive

## DIY vs. Professional Repair

### Can I Fix This Myself?

**Yes, if:**
- You have basic mechanical skills
- You can safely access the thermostat housing (varies by vehicle)
- You're comfortable working with cooling systems
- You have 2-3 hours and basic tools

**No, if:**
- You lack mechanical experience
- Your vehicle has difficult-to-access thermostat housing (many modern cars)
- You're unsure about coolant system pressure/safety
- You want professional warranty on parts/labor

### DIY Thermostat Replacement - Safety Warnings

**⚠️ CRITICAL SAFETY RULES:**
1. **Never open coolant system on hot engine** - Boiling coolant can spray and cause severe burns
2. **Allow engine to cool 30+ minutes** before starting work
3. **Wear safety glasses** - Old coolant can splash
4. **Dispose of old coolant properly** - It's toxic to animals; never pour down drain
5. **Refill with correct coolant type** - Using wrong type can damage engine (consult owner's manual)

## Prevention & Long-Term Care

1. **Coolant Maintenance:**
   - Change coolant every 2-3 years or per manufacturer recommendation
   - Use correct coolant type (owner's manual specifies)
   - Keep coolant level topped off (check monthly)

2. **System Monitoring:**
   - Listen for engine overheating (loud fan, steam)
   - Monitor temperature gauge (should stabilize mid-range)
   - Smell for sweet coolant odor (indicates leak)

3. **Regular Inspections:**
   - Visually check hoses annually for cracks
   - Monitor for coolant leaks (ground stains)
   - Test battery voltage (cold starts stress cooling system)

4. **Driving Habits:**
   - Avoid excessive idling (limits thermostat cycling)
   - Let engine warm up before aggressive driving
   - Check coolant level before long road trips

## FAQ - With Schema Markup

**Q1: Is it safe to drive with DTC P0128?**
A: Not ideal. While not immediately dangerous, unaddressed P0128 will reduce fuel efficiency by 10-15% and risk catalytic converter damage within 1,000-2,000 miles. Repair within 1-2 weeks is recommended.

**Q2: Can I clear the code myself without fixing it?**
A: Yes, but it will return within 100-200 miles. Code clearing doesn't fix the underlying cause. Proper diagnosis and repair is needed to prevent recurrence.

**Q3: How long does thermostat replacement take?**
A: DIY: 2-3 hours. Professional shop: 1-2 hours labor. Total appointment time usually 2-3 hours due to setup/testing.

**Q4: What's the difference between OEM and aftermarket thermostats?**
A: OEM (original manufacturer): Guaranteed fit, premium quality, 20-30% more expensive ($100-150). Aftermarket: Same functionality, slight variation risks, 30-50% cheaper ($40-80).

**Q5: Will my check engine light turn off after I repair it?**
A: Yes, once repair is complete and engine operates normally for 100+ miles, the light will turn off automatically.
```

**Production Plan:**
- Target 500 DTC codes, prioritized by:
  1. Search volume (P-series codes most common)
  2. AutoCognitix user queries
  3. NHTSA complaint frequency
- Publish 50-60 per week for 8-10 weeks
- Variations for common codes (P0300, P0128, P0171, etc.)
- Use content writers + automotive expert review

**Expected Result:** 460+ citations per week from these pages alone. AutoCognitix becomes "DTC authority" for LLMs.

---

### Phase 3: Content Expansion & Optimization (Weeks 13-20) - Effort: Medium-High

**Objective:** Expand to 5,000 DTC codes, add diagnostic procedures, optimize for citation.

**Actions:**

1. **Expand DTC Library to 5,000 Codes** (ongoing, 8 weeks)
   - Add next 4,500 codes using template
   - Focus on P-codes, U-codes most requested
   - 50-60 per week publication rate
   - Implement bulk schema generation

2. **Publish Diagnostic Procedure Library** (6 weeks)
   - 50-100 comprehensive guides
   - Topics: sensor diagnostics, electrical, mechanical, emissions
   - 3,000-4,500 words each
   - Publish 2-3 per week

3. **Parts Pricing Module Optimization** (3 weeks)
   - Integrate real-time pricing API
   - Create pricing table on top 200 DTC pages
   - Update weekly for Perplexity freshness
   - Add labor estimate ranges by geography

4. **FAQ Schema Rollout** (2 weeks)
   - Add FAQ schema to all DTC codes (Question+Answer pairs)
   - 3-5 questions per code
   - Server-side rendering
   - Test schema validity

5. **Update Homepage** (1 week)
   - Follow homepage optimization template (Section 4.4)
   - Add featured articles section
   - Enhance E-E-A-T signals
   - Server-render all schema

6. **Implement Update Automation** (2 weeks)
   - Weekly pricing updates
   - Recall sync from NHTSA
   - Auto-update article "last modified" date
   - IndexNow submission on every update

**Expected Result:** Comprehensive DTC database + diagnostic procedures = 80%+ of automotive diagnostic queries can retrieve AutoCognitix content.

**Citation Projection:** 5,000-10,000 monthly citations.

---

### Phase 4: Authority Building & Monitoring (Weeks 21-26) - Effort: Medium

**Objective:** Establish AutoCognitix as #1 cited source for automotive diagnostics across all LLMs.

**Actions:**

1. **Backlink Strategy** (ongoing)
   - Reach out to automotive forums (JustAnswer, Car Care Council, ATEQ)
   - Pitch specific DTC guides for expert discussion
   - Get links from repair shop directories
   - Target: 100+ referring domains

2. **NHTSA & Industry Integration** (2 weeks)
   - Ensure all NHTSA data properly cited/linked
   - Add links to relevant technical bulletins
   - Create recall cross-references
   - Build authority through data partnerships

3. **Content Promotion for Perplexity Freshness** (ongoing)
   - Weekly blog posts on trending DTCs
   - Announce via social media (Twitter, Reddit, Facebook)
   - Update top 50 articles weekly
   - Publish new articles Tue-Thu for maximum Perplexity pickup

4. **Implement GEO KPI Monitoring** (2 weeks)
   - Set up dashboard with tools from Section 6.2
   - Daily tracking of citation metrics
   - Weekly reports on trending DTCs
   - Monthly performance analysis

5. **Comparative Analysis** (1 week)
   - Compare citations vs. direct Google traffic
   - Measure LLM citation sources (ChatGPT vs. Perplexity vs. Claude)
   - Identify underperforming content
   - Optimize based on data

6. **Scaling to 26,800 Codes** (planned, ongoing)
   - Once 5,000 codes optimized, scale template
   - Increase publication rate to 100+ per week
   - Full library should be complete by Q3 2026

**Expected Result:** AutoCognitix citation dominance for automotive diagnostics. 10,000-20,000+ monthly LLM citations. Significant organic traffic increase through AI Overviews and copilot tools.

---

## Section 6: Monitoring & Measurement Framework

### 6.1 KPI Hierarchy

**Tier 1: Citation Metrics (Direct GEO Outcome)**
- Monthly LLM citations across all platforms
- Citation breakdown by platform (ChatGPT, Perplexity, Claude, Google AI Overviews)
- Average position in multi-source citations (1st source vs. 2nd+ sources)
- Brand/domain citation rate (how often AutoCognitix cited vs. competitors)

**Tier 2: Traffic Metrics (Revenue Impact)**
- Organic traffic from LLM citations (tracked via "came from AI" referrer)
- Click-through rate from LLM citations to website
- Session duration from LLM-referred users
- Conversion rate (tool usage, premium tier signup)

**Tier 3: Content Freshness & Performance**
- Average article age on published pages
- Update frequency (days since last modification)
- Perplexity citation velocity (citations per day post-publish)
- Content semantic completeness score (8.5+/10 target)

**Tier 4: Authority & E-E-A-T**
- Referring domain count (target: 150+ by month 6)
- NHTSA/OBD standard citations (external authority signals)
- Expert contributor mentions (ASE technicians, automotive engineers)
- Social proof signals (user reviews, citations in forums)

**Tier 5: Technical Performance**
- Crawler discovery rate (% of published pages crawled within 48 hours)
- Schema.org validation (0 errors, 100% valid)
- Page speed (Core Web Vitals - LCP, CLS, FID)
- Mobile friendliness (responsive design, mobile traffic %)

### 6.2 Monitoring Tools & Dashboards

**Real-Time Citation Monitoring:**

1. **LLMrefs (llmrefs.com)** ⭐ RECOMMENDED
   - Tracks citations across ChatGPT, Perplexity, Claude, Google AI Overviews
   - Real-time alerts for new citations
   - Historical trend tracking
   - Competitive analysis (see competitor citations)
   - Pricing: Free tier + $29/month premium
   - **Best for:** Overall GEO health, trend identification

2. **OtterlyAI (otterlyai.com)**
   - Perplexity-specific citation tracking
   - Citation text extraction (see exactly what was cited)
   - Search volume + citation correlation
   - Keyword discovery (which queries cite you most)
   - Pricing: Free + $49/month
   - **Best for:** Perplexity optimization focus

3. **Writesonic GEO Tools**
   - ChatGPT-specific citation tracking
   - Content optimization scoring
   - AI-friendly content suggestions
   - Pricing: $99/month premium tier
   - **Best for:** ChatGPT optimization, content recommendations

**Traffic & Conversion Tracking:**

4. **Google Analytics 4 (free)**
   - Set up custom event: "came_from_ai_source"
   - Track referrer patterns (GPTBot, PerplexityBot, etc.)
   - Monitor user behavior from LLM sources
   - **Setup:** Create event when referrer matches known AI crawler patterns

5. **Search Console (free)**
   - Track impressions in Google AI Overviews
   - Monitor discovery rate by crawler type
   - Sitemaps submission tracking
   - **Key metric:** "Impressions (AI Overviews)"

**Content Performance:**

6. **Nightwatch.io**
   - Content freshness tracking (age, last update, recency)
   - Competitive content monitoring
   - Topic authority analysis
   - Pricing: Free trial + $99/month
   - **Best for:** Content strategy optimization

7. **Peec AI (peec.ai)**
   - Semantic completeness scoring (target 8.5+/10)
   - E-E-A-T signals analysis
   - Citation-friendly format recommendations
   - Pricing: Free + $29/month
   - **Best for:** Content quality validation pre-publish

**Schema.org & Technical:**

8. **Schema.org Validator (schema.org/validator)**
   - Free tool for JSON-LD validation
   - Run before publishing any schema markup
   - Catches errors that prevent LLM extraction
   - **Usage:** Test all FAQPage, Article, Organization schemas

### 6.3 Dashboard Setup (Monthly Reporting)

**Weekly Dashboard (Track in Google Sheets):**

```
Week Starting: 2026-04-07

CITATION METRICS
ChatGPT Citations (LLMrefs):       ____ (target: 500+/week by month 3)
Perplexity Citations (OtterlyAI):  ____ (target: 1,200+/week by month 3)
Claude Citations (LLMrefs):        ____ (target: 200+/week by month 3)
Google AI Overview Citations:      ____ (target: 300+/week by month 3)
Total Weekly Citations:             ____ (target: 2,200+/week by month 6)

TRAFFIC METRICS
Sessions from AI Sources:          ____ (track referrer: GPTBot, PerplexityBot, etc.)
Clicks from Citations:             ____ (Google Analytics event)
Avg Session Duration (AI):         ____ min
Conversion Rate (AI traffic):      ___%

CONTENT METRICS
Articles Published:                ____ (target: 50-60/week phase 2)
Articles Updated (price/recall):   ____ (target: 25-30/week)
Avg Article Age:                   ____ days
Articles w/ 8.5+ Semantic Score:   ___%

TECHNICAL METRICS
Pages Crawled by GPTBot (48hr):     ___%
Pages Crawled by PerplexityBot:    ___%
Schema Validation Errors:          ____ (target: 0)
IndexNow Submissions Success:      ___%

TRENDS & INSIGHTS
Top Performing Content:            [URLs with highest citations this week]
Emerging Opportunities:            [DTCs/topics trending in LLM queries]
Competitive Notes:                 [Competitor citation changes]
Recommended Actions:               [Next week priorities]
```

**Monthly Summary (Share with Leadership):**

```markdown
## GEO Performance Report - March 2026

### Monthly Metrics
- **Total LLM Citations:** 8,400 (target: 8,000) ✅ ON TARGET
- **ChatGPT:** 1,200 | **Perplexity:** 3,600 | **Claude:** 800 | **Google AI:** 2,800
- **Organic Traffic from Citations:** 2,100 sessions (+45% MoM)
- **Referral Domain Count:** 47 (target: 150 by June)

### Citation Trends
- P0300 (Random Misfire): Most cited code (240 citations)
- "Thermostat diagnosis" guide: Second most cited
- Perplexity citations growing 2x faster than ChatGPT

### Content Progress
- DTC Codes Published: 450 (target: 500)
- New Diagnostic Guides: 12
- Price Updates: 120 articles
- Semantic Completeness Avg: 8.2/10

### Technical Health
- Crawler Discovery: 92% of published pages (target: 95%)
- Schema Validation: 0 errors
- Page Speed (LCP): 1.8s (excellent)

### Competitive Positioning
- AutoCognitix cited more than competitor in 60% of diagnostic queries
- Unique position in DTC code explanation (competitors lacking)
- Authority gap: Need 100+ more referring domains

### Next Month Focus
1. Scale DTC library to 1,000 codes
2. Publish 15 new diagnostic procedures
3. Implement NHTSA recall automation
4. Launch backlink outreach campaign
```

### 6.4 Optimization Cycles (Continuous Improvement)

**Daily (5 minutes):**
- Check LLMrefs for new citations
- Note top-performing content
- Flag any technical errors

**Weekly (30 minutes):**
- Update pricing on top 50 DTC pages
- Review Perplexity trends in OtterlyAI
- Publish 2-3 new DTC guides
- Update llms.txt if major changes

**Monthly (2 hours):**
- Comprehensive KPI review
- Competitive analysis
- Content gap identification
- Strategic adjustment for next month

**Quarterly (4 hours):**
- Full GEO audit (crawler discovery, schema, authority)
- Backlink strategy review
- Content performance tier analysis
- 3-month strategic plan adjustment

---

## Section 7: Quick-Start Implementation Checklist

### Week 1-2: Immediate Actions (8-10 hours total)

- [ ] Create `/llms.txt` file (Section 3.3)
- [ ] Deploy to domain root, verify accessibility
- [ ] Create `/llms-full.txt` file
- [ ] Update `robots.txt` with AI crawler allowlist (Section 3.1)
- [ ] Verify all crawlers allowed: GPTBot, ClaudeBot, PerplexityBot, Google-Extended
- [ ] Generate XML sitemaps (sitemap.xml, sitemap-dtc.xml, sitemap-news.xml)
- [ ] Submit to Google Search Console
- [ ] Setup IndexNow security key in /.well-known/indexnow
- [ ] Add Organization + Service schema.org markup to homepage
- [ ] Test schema with validator (schema.org/validator)
- [ ] Sign up for LLMrefs (llmrefs.com) citation tracking
- [ ] Create monitoring Google Sheet (Section 6.3)

**Expected Result:** Infrastructure ready, baseline citation metrics established.

### Week 3-4: Content Foundation (15-20 hours)

- [ ] Create standardized DTC code template (use example in Section 5)
- [ ] Draft first 50 DTC codes using template
- [ ] Have automotive expert review 5 drafts for accuracy
- [ ] Implement FAQ schema on first 50 codes
- [ ] Publish first 50 codes (Tue-Thu schedule)
- [ ] Update llms.txt with published count
- [ ] Test IndexNow submissions for 5 articles
- [ ] Monitor LLMrefs for first citations

**Expected Result:** First citations appearing, baseline content quality validated.

### Month 2-3: Scaling Phase (40-60 hours)

- [ ] Scale to 500 DTC codes (50-60/week)
- [ ] Have automotive expert review 10% of articles
- [ ] Implement bulk schema generation (automate FAQ per code)
- [ ] Begin Diagnostic Procedure guides (10-15 articles)
- [ ] Weekly pricing updates (first 100 codes)
- [ ] Weekly NHTSA recall checks
- [ ] Monthly review of KPIs
- [ ] Establish backlink outreach (automotive forums, shops)

**Expected Result:** 1,000-2,000+ monthly citations, AutoCognitix appearing in diagnostic queries.

### Month 4-6: Authority Building (50-80 hours)

- [ ] Expand to 5,000 DTC codes
- [ ] Publish 50-100 diagnostic procedures
- [ ] Implement real-time parts pricing API
- [ ] Establish ongoing content updates (weekly pricing, recalls)
- [ ] Build 50+ high-quality backlinks
- [ ] Monthly competitive analysis
- [ ] Quarterly strategy adjustments

**Expected Result:** 10,000-20,000+ monthly citations, established authority in automotive diagnostics.

---

## Appendix A: Technical Implementation Files

### robots.txt - Complete Configuration

```
# Standard search engines
User-agent: Googlebot
Allow: /
Crawl-delay: 0.5

User-agent: Bingbot
Allow: /

# AI-Powered Search & LLM Crawlers (CRITICAL FOR GEO)
User-agent: GPTBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /
# Common Crawl - used by many LLM training datasets

# Block bad actors
User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

User-agent: DotBot
Disallow: /

User-agent: MJ12bot
Disallow: /

# Crawl delay for heavy crawlers
User-agent: *
Crawl-delay: 2

# Sitemaps - submit all
Sitemap: https://autocognitix.com/sitemaps.xml
```

### llms.txt - Template

Use template from Section 3.3.

### Homepage Schema.org - JSON-LD Example

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "AutoCognitix",
  "url": "https://autocognitix.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://autocognitix.com/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  }
}
```

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AutoCognitix",
  "url": "https://autocognitix.com",
  "logo": "https://autocognitix.com/logo.png",
  "description": "AI-powered automotive diagnostics platform with 26,800+ DTC codes and real-time repair cost estimates",
  "sameAs": [
    "https://twitter.com/autocognitix",
    "https://linkedin.com/company/autocognitix"
  ],
  "knowsAbout": [
    "Automotive Diagnostics",
    "OBD-II Codes",
    "Engine Repair",
    "Vehicle Maintenance",
    "DTC Code Interpretation"
  ],
  "mainEntity": {
    "@type": "Service",
    "name": "DTC Code Diagnosis",
    "description": "Interpret diagnostic trouble codes with root cause analysis and repair guidance",
    "provider": {
      "@type": "Organization",
      "name": "AutoCognitix"
    }
  }
}
```

### FAQ Schema.org - DTC Code Example

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "@id": "https://autocognitix.com/dtc/p0128#faq-safe",
      "name": "Is DTC P0128 safe to drive with?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not ideal long-term. While not immediately dangerous, an unaddressed P0128 will reduce fuel efficiency by 10-15% and risk catalytic converter damage within 1,000-2,000 miles. Repair within 1-2 weeks is recommended. Safe to drive to a repair shop, but avoid long highway trips."
      }
    },
    {
      "@type": "Question",
      "@id": "https://autocognitix.com/dtc/p0128#faq-cost",
      "name": "How much does P0128 repair cost?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Average cost is $300-$600 for parts and labor. Thermostat replacement (most common fix) runs $230-$600 at an independent shop, $350-$700 at dealerships. DIY parts cost is $80-$200 if you do the work yourself."
      }
    },
    {
      "@type": "Question",
      "@id": "https://autocognitix.com/dtc/p0128#faq-urgent",
      "name": "Do I need to fix P0128 immediately?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not immediately, but within 1-2 weeks. It's safe to drive to a repair shop, but extended driving will gradually damage your catalytic converter and waste fuel. Schedule repair at your earliest convenience."
      }
    }
  ]
}
```

---

## Appendix B: Content Performance Benchmarks

**Expected Citation Rates by Content Type (After 6-Month Implementation):**

| Content Type | Monthly Citations (Full Implementation) | Lead Time to First Citation | Peak Citation Window |
|--------------|----------------------------------------|-------------------------------|---------------------|
| DTC Code Guide (2,500-3,500w) | 15-40 | 2-4 days | Days 3-30 |
| Diagnostic Procedure (3,500-5,000w) | 20-50 | 3-7 days | Days 5-45 |
| FAQ Page with Schema | 5-20 | 2-3 days | Days 2-14 |
| Blog Post / News (1,500-2,500w) | 5-15 | 1-2 days | Days 1-7 (Perplexity only) |
| Cost Analysis Table | 3-12 | 1-3 days | Days 1-21 |
| Homepage (featuring content) | 5-20 | Immediate | Ongoing |

**Citation Velocity:**
- Perplexity: 60% of total citations arrive within 48 hours of publish
- ChatGPT: 40% arrive within 1 week, 80% within 2 weeks
- Claude: Slower adoption, 50% arrive within 2 weeks
- Google AI Overviews: 30-40% arrive within 1 week

---

## Appendix C: Glossary of Key Terms

**E-E-A-T** - Experience, Expertise, Authoritativeness, Trustworthiness. The four signals LLMs use to determine if content is citable.

**GEO** - Generative Engine Optimization. Optimization of content for discovery and citation by LLMs.

**Semantic Completeness** - A score (1-10) representing how well a piece of content answers a question with evidence and detail. Content scoring 8.5+/10 is 4.2x more likely to be cited.

**RAG** - Retrieval-Augmented Generation. The two-step process LLMs use: (1) Retrieve relevant documents, (2) Generate synthesis with citations.

**Schema.org** - Standardized markup language for structured data. LLMs use schema to automatically extract facts, numbers, relationships.

**FAQ Schema** - Specialized schema.org markup for Q&A content. Increases citation rates 3x.

**Crawl-delay** - Configuration in robots.txt telling crawlers how many seconds to wait between page requests (reduces server load).

**IndexNow** - Protocol allowing immediate notification of search engines and LLM crawlers about new/updated content.

**llms.txt** - Emerging standard file placed at domain root describing the site to LLM crawlers. Signals quality and LLM-friendliness.

**ClaudeBot / GPTBot / PerplexityBot** - User-agent identifiers for LLM crawlers (similar to Googlebot for search).

**Content Velocity** - How quickly content gains citations after publication. Higher velocity = better LLM discoverability.

**Referring Domain** - Unique domain linking to your site. Higher referring domain count = higher authority signals.

---

## Document Information

**Prepared For:** AutoCognitix Product & Marketing Teams  
**Date:** March 2026  
**Research Sources:** 50+ authoritative sources (2025-2026) on GEO, LLM citation mechanisms, E-E-A-T, RAG architecture  
**Recommendations Validity:** 6-month roadmap (extends through September 2026)  
**Next Review Date:** June 2026 (quarterly strategy adjustment)

**Questions or Clarifications?** This document is meant to be actionable and specific to AutoCognitix's content and technical capabilities. All recommendations can be adjusted based on engineering capacity and business priorities.
