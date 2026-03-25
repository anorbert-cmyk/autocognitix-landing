# AutoCognitix Landing Page — Handoff (2026-03-25)

## Session összefoglaló

### Amit csináltunk (12 commit, `f6f638a` → `700d524`):

1. **3 HU + 3 EN interaktív tool oldal** — Megéri megjavítani, Műszaki Vizsga Prediktor, Szervizkeresős
2. **22 bugfix** — 3 CRITICAL (break-even inverzió, MIL short-circuit, .dockerignore), 4 HIGH, 14 MEDIUM
3. **Fázis A hardening** — input validáció, metamorphic self-test, confidence display, escapeHTML shared
4. **CI/CD pipeline** — GitHub Actions + 337 Vitest teszt (unit, integration, smoke, a11y) + QA review
5. **Hybrid architektúra** — Python proxy sidecar (CSRF bypass) + progressive enhancement
6. **Adatbázisok**:
   - 125 modell piaci áradatok (HUF, 2010-2024)
   - 4,934 DTC kód (open-source, EN leírás)
   - 50 javítási költség becslés (HU+EN, HUF)
   - MNB EUR/HUF napi szinkron
7. **4 scraper** — hasznaltauto.hu, OOYYO.com, AutoBazar.eu, Bazos.sk
8. **Napi automatikus árfrissítés** — 5,250 listing/nap, 4 párhuzamos GitHub Action runner

---

## AKTÍV PROBLÉMA: Railway deploy nem tölt

**Legutóbbi fix (`700d524`):**
- `nginx:1.27-alpine` → `nginx:alpine` (tag valószínűleg nem létezett)
- start.sh `head -1` pipe fix

**Ha még mindig nem működik, Plan B:**
A multi-stage Python build lehet a probléma. Ilyenkor:
1. Vedd ki a proxy-t a Dockerfile-ból teljesen
2. Állítsd vissza az eredeti egyszerű nginx-es Dockerfile-t:
```dockerfile
FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY sitemap.xml /usr/share/nginx/html/
COPY robots.txt /usr/share/nginx/html/
COPY hu/ /usr/share/nginx/html/hu/
COPY en/ /usr/share/nginx/html/en/
COPY shared/ /usr/share/nginx/html/shared/
COPY unsubscribe.html /usr/share/nginx/html/unsubscribe.html
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget --no-verbose --tries=1 --spider http://localhost:8080/hu/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
```
3. A proxy-t deploy-old külön Railway service-ként (saját repó vagy mono-repo service)

**Ha a proxy-t kiveszed**, a tool oldalak továbbra is működnek a client-side JS-sel. A progressive enhancement (API hívások) nem fog működni, de a core funkcionalitás megmarad.

---

## Következő lépések (prioritás sorrendben):

### P0 — Railway deploy fix
- Ellenőrizd: `autocognitix-landing-production.up.railway.app`
- Ha nem tölt: alkalmazd a Plan B-t (proxy nélküli Dockerfile)

### P1 — BACKEND_DB_READ_URL secret beállítás
- GitHub repo Settings → Secrets → `BACKEND_DB_READ_URL`
- Ez a backend PostgreSQL read-only connection string
- Ezzel a heti data-export.yml valódi adatokat húz

### P2 — Scraper éles teszt
- Futtasd kézzel: Actions → "Update Market Prices" → Run workflow
- Ellenőrizd hogy a hasznaltauto.hu parser valódi adatot szed le
- OOYYO 30s crawl-delay miatt lassú de működik

### P3 — Tier 2 Deep Research (proxy bővítés)
- CRAG retrieval evaluator a proxy-ban
- Self-RAG reflection (LLM hívás)
- RAGAS eval pipeline (golden dataset szükséges)

### P4 — hasznaltauto.hu parser kiterjesztés
- Jelenleg sitemap-based → lassú
- Alternatíva: listing URL pattern-based keresés (gyorsabb)
- Cél: 5,000+ listing/brand/hét

---

## Fájl struktúra (új fájlok):

```
hu/eszkozok/                          # 3 HU tool + hub
en/tools/                             # 3 EN tool + hub
shared/js/
  vehicle-data.js                     # VehicleDB + market price integration
  tool-common.js                      # Validáció, DTC, formatting, selfTest
  api-client.js                       # Progressive enhancement API client
shared/data/
  hungarian-market-prices.json        # 125 modell × 8 év piaci árak
  dtc-database.json                   # 4,934 DTC kód
  repair-costs.json                   # 50 javítási költség
  exchange-rate.json                  # EUR/HUF (MNB)
proxy/
  main.py                             # Starlette ASGI proxy (CSRF bypass)
  requirements.txt                    # httpx, uvicorn, starlette
scripts/
  scrapers/
    config.py                         # 25 brand × 5 model mapping
    hasznaltauto_parser.py            # hasznaltauto.hu sitemap parser
    ooyyo_parser.py                   # OOYYO.com 27 market scraper
    autobazar_parser.py               # AutoBazar.eu Slovak market
    bazos_parser.py                   # Bazos.sk Slovak classifieds
  aggregate-prices.py                 # Multi-source price aggregator
  run-scraper.py                      # Universal scraper runner
  fetch-mnb-rate.py                   # MNB SOAP API EUR/HUF
  fetch-mobile-de-prices.py           # EUR/HUF rate adjustment
  build-dtc-database.py               # Open-source DTC builder
  export-vehicle-data.py              # Backend DB export
  export-dtc-data.py                  # Backend DB export
  export-repair-costs.py              # Backend DB export
tests/                                # 337 teszt (Vitest)
.github/workflows/
  ci.yml                              # CI pipeline (build, test, validate)
  data-export.yml                     # Heti backend DB export
  price-update.yml                    # Napi 4 párhuzamos scraper
```

---

## Architektúra szabály (MEMÓRIÁBAN)

**A fő AutoCognitix backend repót (`anorbert-cmyk/AutoCognitix`) SOHA NE MÓDOSÍTSD.** Minden új fejlesztés a landing page repóba megy. A backend adatait read-only proxy-n vagy static JSON export-on keresztül érjük el.
