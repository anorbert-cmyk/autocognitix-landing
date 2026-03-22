# AutoCognitix — Brand Design Guide
## Verzio 1.0 | 2026-03-21

**Referencia:** [anorva.webflow.io](https://anorva.webflow.io/) look & feel adaptacio
**Cel:** Egységes vizualis rendszer az AutoCognitix weboldalhoz es minden digitalis felülethez.

---

## 1. DESIGN FILOZOFIA

### Alapelvek

Az AutoCognitix design rendszere a **premium minimalizmust** követi: tiszta tipografia, bovizsgalt whitespace, es kontrasztos szin-megkülönböztetesek. Az Anorva referencia alapjan a celunk egy B2B/B2C hibrid megjelenes, ami:

- **Professzionalis** — a profi szerelok komolyan veszik
- **Modern** — a fiatal DIY kozönseget vonzza
- **Magabiztos** — nagy szamok, bold statement-ek, social proof
- **Letisztult** — semmi felesleges vizualis zaj

### Design Pillerer

| Piller | Leiras | Peldak |
|--------|---------|--------|
| **Fehertér-dominancia** | A tartalom lelegzik, nem zsufolt | 120px section padding, generous gaps |
| **Tipografiai hierarchia** | A betumeret es vastagság vezeti a szemet | 80px heading → 22px body → 14px caption |
| **Szin-kontraszt** | Feher/szürke alap, sötét szekciok, egy erös akcentszin | Light #F2F2F4 vs Dark #12110E |
| **Kepianyag-integráció** | Valos fotok, nem stock illusztraciok | Portrek, munkafolyamat kepek |
| **Micro-interakciok** | Finom animaciok, hover effektek | Glow border, fade-in, smooth scroll |

---

## 2. SZINPALETTA

### 2.1. Elsodleges Szinek (Core Palette)

```
┌──────────────────────────────────────────────────────┐
│  LIGHT BASE          DARK BASE          ACCENT       │
│  #F2F2F4             #12110E            #D97757      │
│  rgb(242,242,244)    rgb(18,17,14)      rgb(217,119,87) │
│  ░░░░░░░░░░░░░       ████████████       ▓▓▓▓▓▓▓▓    │
│  Hatter, szekciok    Sötét szekciok     CTA, kiemelés│
└──────────────────────────────────────────────────────┘
```

| Szin | Hex | RGB | Hasznalat |
|------|-----|-----|-----------|
| **Light Base** | `#F2F2F4` | `rgb(242, 242, 244)` | Fo hattér, light szekciok, oldal alapszin |
| **Dark Base** | `#12110E` | `rgb(18, 17, 14)` | Sötét szekciok, footer, gombok, heading szöveg |
| **Warm Accent** | `#D97757` | `rgb(217, 119, 87)` | Akcent glow, CTA hover, kiemelések (terracotta/coral) |
| **White** | `#FFFFFF` | `rgb(255, 255, 255)` | Kartya hatter, input hatter, sötét szekcion belüli szöveg |
| **Mid Gray** | `#E4E4E7` | `rgb(228, 228, 231)` | Sötétebb szekciok háttere, input mezok, divider-ek |
| **Light Gray** | `#D6D6DA` | `rgb(214, 214, 218)` | Szegélyek, inaktiv állapotok |
| **Muted Text** | `#8D96A3` | `rgb(141, 150, 163)` | Masodlagos szöveg, placeholder, caption |
| **Info Surface** | `#F4F8FA` | `rgb(244, 248, 250)` | Kiemelő hattér, badge háttér |

### 2.2. Szin Hasznalat Szabalyok

**Light szekciok (alapertelmezett):**
- Hatter: `#F2F2F4`
- Szöveg: `#12110E`
- Masodlagos szöveg: `#8D96A3`

**Dark szekciok (hero feature, CTA banner):**
- Hatter: `#12110E`
- Szöveg: `#FFFFFF`
- Masodlagos szöveg: `rgba(255, 255, 255, 0.7)`

**Kartya szinek:**
- Light kartyak: `#FFFFFF` hatter, `1px solid rgba(0,0,0,0.1)` keret
- Dark kartyak (pricing featured): `#12110E` hatter, feher szöveg

**Accent hasznalat:**
- `#D97757` SOHA nem hatter szin — kizarolag:
  - Glow effektek (inset shadow: `rgba(217, 119, 87, 0.5) 0px 0px 10px 0px inset`)
  - Hover allapotok
  - Kiemelt badge/chip szegely
  - Az Aceternity glowing border effekt akcentje

### 2.3. Szin Kontraszt Ellenorzes (WCAG 2.1 AA)

| Kombinacio | Kontraszt | Megfeleles |
|-----------|-----------|------------|
| `#12110E` on `#F2F2F4` | ~18:1 | AAA |
| `#FFFFFF` on `#12110E` | ~18:1 | AAA |
| `#8D96A3` on `#F2F2F4` | ~3.5:1 | AA (nagy szöveg) |
| `#D97757` on `#12110E` | ~4.8:1 | AA |

---

## 3. TIPOGRAFIA

### 3.1. Font Család

**Elsodleges font: Funnel Sans**

```
Font:     Funnel Sans (Google Fonts)
Tipus:    Sans-serif, geometrikus-humanista hibrid
Suyok:    300 (Light), 400 (Regular), 500 (Medium), 600 (SemiBold), 700 (Bold)
Fallback: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
```

**Import:**
```html
<link href="https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

**Miert Funnel Sans?**
- Modern, tiszta megjelenes
- Kivalo olvashatosag nagy es kis mereten egyarant
- 300-700 sulytartomany biztositja a hierarchiat
- Technikai, de nem rideg — passza az autódiagnosztika temához

### 3.2. Tipografiai Skala

| Token | Elem | Meret | Suly | Sorköz | Betukoz | Hasznalat |
|-------|------|-------|------|--------|---------|-----------|
| **Display** | Hero H1/H2 | `80px` | `400` | `80px` (1.0) | `-2.4px` | Hero headline, nagy szamok (1M+, 97%) |
| **H2** | Szekció cim | `56px` | `400` | `60px` | `-1.68px` | Szekció focimet |
| **H3** | Al-cim | `40px` | `400` | `44px` | `-1.2px` | Feature cimek, kartya cimek |
| **H4** | Kis cim | `28px` | `500` | `32px` | `-0.84px` | Pricing plan nevek, blog cimek |
| **H5** | Label | `22px` | `600` | `28px` | `-0.66px` | Alszekció cimek |
| **H6** | Mikro cim | `18px` | `600` | `24px` | `-0.54px` | Kartya belso cimek |
| **Body L** | Nagy paragraph | `22px` | `400` | `32px` | `-0.66px` | Hero leiras, szekció bevezeto |
| **Body** | Alap paragraph | `16px` | `400` | `26px` | `-0.48px` | Fo szövegtörzs |
| **Body S** | Kis paragraph | `14px` | `400` | `22px` | `-0.42px` | Kartya szöveg, feature listas |
| **Caption** | Felirat | `12px` | `500` | `16px` | `0.5px` | Button label, badge, meta info |
| **Overline** | Kategória | `12px` | `600` | `16px` | `1.5px` | Uppercase tagek: TECHNOLOGY, INSIGHT |

### 3.3. Tipografiai Szabályok

**Heading-ek:**
- Mindig `font-weight: 400` (Regular) — a meret hordozza a sulyát, nem a bold
- Negativ letter-spacing (`-0.03em` ratio) — tömörebb, premiumabb megjelenes
- Line-height = font-size vagy minimálisan több (1.0–1.1 ratio)
- SOHA ne legyen Bold (700) heading — az olcsó hatast kelt

**Body szöveg:**
- `font-weight: 400` az alapertelmezett
- `font-weight: 500` kiemelésre (helyettesiti a bold-ot body-ban)
- Sortávolság: `1.625` ratio (26px / 16px)
- Max szovegszelességseg: `65ch` (~680px) az olvashatosagert

**Button szöveg:**
- `font-size: 12px`
- `font-weight: 600`
- `letter-spacing: 1.5px`
- `text-transform: uppercase`

---

## 4. SPACING RENDSZER

### 4.1. Alap Spacing Skala (8px base)

```
4px   — micro (ikon-szöveg gap)
8px   — xs (badge padding, inline gap)
12px  — sm (kartya belso padding)
16px  — md (input padding, kartya gap)
20px  — base (button padding)
24px  — lg (szekcion belüli gap)
32px  — xl (elem közötti tér)
40px  — 2xl (csoport közötti tér)
48px  — 3xl (szekció belso padding)
60px  — 4xl (szekció padding narrow)
80px  — 5xl (szekció közötti tér)
120px — 6xl (szekció padding top/bottom)
180px — 7xl (hero padding-top)
```

### 4.2. Szekció Spacing

| Szekció tipus | Padding Top | Padding Bottom | Peldak |
|---------------|-------------|----------------|--------|
| **Hero** | `180px` | `60px` | Fo landing hero |
| **Standard szekció** | `120px` | `120px` | Features, Pricing, Blog, FAQ |
| **Dark szekció** | `120px` | `120px` | Feature highlight, Case study |
| **Newsletter CTA** | `120px` | `120px` | Sötétebb hattér (#E4E4E7) |
| **Footer** | `80px` | `40px` | Sötét footer |

### 4.3. Container

```css
.container {
  max-width: 1200px;     /* Fo tartalom max-szelesseg */
  margin: 0 auto;
  padding: 0 24px;       /* Mobil padding */
}

@media (min-width: 768px) {
  .container {
    padding: 0 40px;     /* Tablet */
  }
}

@media (min-width: 992px) {
  .container {
    padding: 0 60px;     /* Desktop */
  }
}
```

---

## 5. LAYOUT RENDSZER

### 5.1. Grid

**12 oszlopos grid rendszer:**
```css
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 24px;
}
```

**Tipikus layout-ok:**
| Layout | Oszlop elosztás | Hasznalat |
|--------|-----------------|-----------|
| Teljes szelesség | `span 12` | Hero headline, CTA banner |
| Ketto oszlop 50/50 | `span 6 + span 6` | Feature + kep, Case study |
| Ketto oszlop 40/60 | `span 5 + span 7` | Szöveg + nagy kep |
| Harom oszlop | `span 4 + span 4 + span 4` | Blog kartyak, Feature grid |
| Negy oszlop | `span 3 × 4` | Statisztikak (97%, 15K, 1M+, 99%) |

### 5.2. Responsive Breakpoints

| Token | Meret | Eszkoz |
|-------|-------|--------|
| `sm` | `480px` | Kis mobil |
| `md` | `768px` | Tablet |
| `lg` | `992px` | Kis desktop |
| `xl` | `1200px` | Desktop |
| `2xl` | `1440px` | Nagy desktop |

### 5.3. Szekció Sorrend (Ajanlott Landing Page Struktura)

```
1. Navigation (sticky)
2. Hero (Light base hatter)
3. Social Proof / Statistics (szamok: 97%, 15K+, stb.)
4. Features / Szolgaltatasok (Light + kep)
5. Video / Demo szekció (Dark hatter)
6. Case Study / Testimonial (Light)
7. Brand logos / Trust badges (Dark)
8. Pricing (Light/Dark mix)
9. Blog / Insights (Light)
10. FAQ (Light, accordion)
11. Testimonial Carousel (Light)
12. Newsletter CTA (sötétebb szürke #E4E4E7)
13. Footer (Dark #12110E)
```

---

## 6. KOMPONENSEK

### 6.1. Gombok (Buttons)

#### Primary Button (Sötét)
```css
.btn-primary {
  background-color: #12110E;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 20px 32px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}
.btn-primary:hover {
  background-color: #2F3640;
  box-shadow: rgba(217, 119, 87, 0.3) 0px 0px 20px 0px;
}
```

#### Secondary Button (Outlined)
```css
.btn-secondary {
  background-color: transparent;
  color: #12110E;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 20px 32px;
  border-radius: 8px;
  border: 1px solid #12110E;
  cursor: pointer;
  transition: all 0.3s ease;
}
.btn-secondary:hover {
  background-color: #12110E;
  color: #FFFFFF;
}
```

#### Ghost Button (Sötét háttéren)
```css
.btn-ghost {
  background-color: transparent;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 20px 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}
.btn-ghost:hover {
  background-color: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.6);
}
```

#### CTA Elrendezés
```
Mindig parban:
[  START SCALING  ] [  BOOK A DEMO  ]
   (Primary)           (Secondary)
```

### 6.2. Kartyak (Cards)

#### Standard Kartya
```css
.card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px;
  box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px,
              rgba(0, 0, 0, 0.1) 0px 1px 3px 0px;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px,
              rgba(0, 0, 0, 0.15) 0px 4px 12px 0px;
}
```

#### Testimonial Kartya
```css
.testimonial-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 40px;
  box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px,
              rgba(0, 0, 0, 0.1) 0px 1px 3px 0px;
  /* Tartalom sorrend: idezet → csillagok → avatar + nev + cimkek */
}
```

#### Pricing Kartya — Standard
```css
.pricing-card {
  background: #FFFFFF;
  border-radius: 20px;
  padding: 40px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
```

#### Pricing Kartya — Featured (Kiemelt)
```css
.pricing-card-featured {
  background: #12110E;
  color: #FFFFFF;
  border-radius: 20px;
  padding: 40px;
  /* Nincs kulon border — a sötét hatter maga a kiemelés */
}
```

#### Blog Kartya
```css
.blog-card {
  background: #FFFFFF;
  border-radius: 16px;
  overflow: hidden;  /* kep felül, szöveg alul */
  box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px,
              rgba(0, 0, 0, 0.1) 0px 1px 3px 0px;
}
.blog-card img {
  width: 100%;
  height: 220px;
  object-fit: cover;
}
.blog-card-body {
  padding: 24px;
}
```

### 6.3. Badge / Tag / Chip

```css
.badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
  padding: 6px 16px;
  border-radius: 100px;       /* Pill forma */
  border: 1px solid #D6D6DA;
  background: transparent;
  color: #12110E;
}

/* Sötét valtozat */
.badge-dark {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
  color: #FFFFFF;
}

/* Kiemelt badge (Popular, Best Value) */
.badge-featured {
  background: #12110E;
  border-color: #12110E;
  color: #FFFFFF;
  font-weight: 600;
}
```

### 6.4. Input Mezok

```css
.input {
  width: 100%;
  height: 70px;
  background: #E4E4E7;
  color: #12110E;
  border: none;
  border-radius: 8px;
  padding: 16px 24px;
  font-size: 18px;
  font-family: "Funnel Sans", sans-serif;
  font-weight: 400;
  transition: background 0.2s ease;
}
.input::placeholder {
  color: #8D96A3;
}
.input:focus {
  background: #D6D6DA;
  outline: 2px solid #12110E;
  outline-offset: 2px;
}
```

### 6.5. Navigacio

```css
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(242, 242, 244, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 16px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.nav-logo {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: #12110E;
  text-transform: uppercase;
}

.nav-link {
  font-size: 14px;
  font-weight: 500;
  color: #12110E;
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 8px;
  transition: background 0.2s ease;
}
.nav-link:hover {
  background: rgba(0, 0, 0, 0.05);
}
.nav-link.active {
  background: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

.nav-cta {
  /* Hasznald a .btn-primary stilust */
  padding: 12px 24px;
  font-size: 12px;
}
```

### 6.6. FAQ Accordion

```css
.faq-item {
  background: #E4E4E7;
  border-radius: 12px;
  padding: 24px 32px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}
.faq-item:hover {
  background: #D6D6DA;
}
.faq-question {
  font-size: 18px;
  font-weight: 500;
  color: #12110E;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.faq-arrow {
  width: 24px;
  height: 24px;
  transition: transform 0.3s ease;
}
.faq-item.active .faq-arrow {
  transform: rotate(180deg);
}
.faq-answer {
  font-size: 16px;
  line-height: 26px;
  color: #8D96A3;
  margin-top: 16px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
}
```

### 6.7. Pricing Toggle

```css
.pricing-toggle {
  display: inline-flex;
  border-radius: 12px;
  border: 1px solid #D6D6DA;
  padding: 4px;
  background: #FFFFFF;
}
.pricing-toggle-option {
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #8D96A3;
}
.pricing-toggle-option.active {
  background: #12110E;
  color: #FFFFFF;
}
```

### 6.8. Social Proof Bar

```css
.social-proof {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: #FFFFFF;
  border-radius: 100px;
  box-shadow: rgba(16, 24, 40, 0.05) 1px 1px 2px 0px;
}
.avatar-stack {
  display: flex;
}
.avatar-stack img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid #FFFFFF;
  margin-left: -8px;
}
.avatar-stack img:first-child {
  margin-left: 0;
}
.social-proof-text {
  font-size: 14px;
  font-weight: 500;
  color: #12110E;
}
```

---

## 7. ARNYEK RENDSZER (Shadows)

### 7.1. Shadow Tokenek

| Token | Erték | Hasznalat |
|-------|-------|-----------|
| **Shadow XS** | `rgba(16, 24, 40, 0.05) 1px 1px 2px 0px` | Social proof pill, finom elem kiemelés |
| **Shadow SM** | `rgba(0, 0, 0, 0.2) 0px 0px 1px 0px` | Kep szegely effekt |
| **Shadow MD** | `rgba(0, 0, 0, 0.1) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 1px 3px 0px` | Kartyak alapertelmezett |
| **Shadow LG** | `rgba(0, 0, 0, 0.1) 0px 0px 0px 1px, rgba(0, 0, 0, 0.15) 0px 4px 12px 0px` | Kartya hover |
| **Glow Accent** | `rgba(217, 119, 87, 0.5) 0px 0px 10px 0px inset, rgba(217, 119, 87, 0.3) 0px 0px 20px 0px inset, rgba(217, 119, 87, 0.1) 0px 0px 30px 0px inset` | Akcent glow effekt (specialis) |

### 7.2. Glow Effekt — Aceternity Border

Az AutoCognitix egyedi eleme: az Aceternity UI glowing border animacio.

```css
/* A glow-wrap ::after pszeudo-elem */
.glow-wrap::after {
  /* ... mask-composite: intersect technologia ... */
  /* Reszletes implementacio: v6-aceternity-glowing.html */
  /* Szinek a palettabol: #dd7bbb, #d79f1e, #5a922c, #4c7894 */
  /* Ez a premium tech-erzetet adja az AutoCognitix-nak */
}
```

---

## 8. BORDER RADIUS RENDSZER

| Token | Erték | Hasznalat |
|-------|-------|-----------|
| `radius-xs` | `4px` | Checkbox, kis ikonok |
| `radius-sm` | `8px` | Gombok, input mezok, nav link hover |
| `radius-md` | `12px` | FAQ accordion, pricing toggle belsok |
| `radius-lg` | `16px` | Kartyak, blog kartyak |
| `radius-xl` | `20px` | Pricing kartyak, feature szekciok |
| `radius-2xl` | `24px` | Specialis nagy kartyak |
| `radius-full` | `100px` | Badge/pill, avatar, social proof bar |

**Alapelv:** Nagyobb elem = nagyobb radius. Soha nem hasznalunk éles sarkokat (0px).

---

## 9. IKONOGRAFIA

### 9.1. Ikon Stilus

| Tulajdonság | Ertek |
|-------------|-------|
| **Stilus** | Line icons (nem filled) |
| **Vastagsag** | 1.5px stroke |
| **Meret** | 24px (standard), 32px (feature icon), 48px (hero icon) |
| **Szin** | `#12110E` light háttéren, `#FFFFFF` dark háttéren |
| **Forras** | Lucide React / Heroicons / custom SVG |

### 9.2. Feature Ikon Keret

```css
.feature-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Nincs hatter, nincs keret — az ikon maga a dizajn elem */
}
```

### 9.3. Social Media Ikonok

```css
.social-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  color: #FFFFFF;
  transition: background 0.2s ease;
}
.social-icon:hover {
  background: rgba(255, 255, 255, 0.2);
}
```

---

## 10. KEPIANYAG (Photography)

### 10.1. Kep Stilus Iranyelvek

| Szempont | Iranymutatás |
|----------|-------------|
| **Tipus** | Valos fotok, nem AI-generalt, nem illusztracio |
| **Tema** | Emberek munka közben: szerelomuhelyben, autoval, telefonnal |
| **Szinvilag** | Meleg, termeszetes szinek — passzonak a #D97757 akcenthez |
| **Megvilagitas** | Termeszetes feny, ablak feny, meleg tonusok |
| **Kompozicio** | Tömor, portré-szeru vagy 3:2 / 16:9 arany |
| **Szurok** | Enyhe melegites (+5% warmth), enyhe kontraszt noveles |

### 10.2. Kep Meretezesi Szabalyok

```css
/* Hero kepek */
.hero-image {
  width: 100%;
  max-height: 500px;
  object-fit: cover;
  border-radius: 16px;
}

/* Blog kep */
.blog-image {
  width: 100%;
  height: 220px;
  object-fit: cover;
  border-radius: 16px 16px 0 0;
}

/* Avatar */
.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  object-fit: cover;
}

/* Case study kep */
.case-study-image {
  width: 100%;
  aspect-ratio: 4/3;
  object-fit: cover;
  border-radius: 16px;
}
```

---

## 11. ANIMACIOK ES TRANZICIOK

### 11.1. Transition Tokenek

| Token | Erték | Hasznalat |
|-------|-------|-----------|
| **Fast** | `0.15s ease` | Hover szin, opacity valtozas |
| **Normal** | `0.3s ease` | Gomb hover, kartya hover, transform |
| **Slow** | `0.5s ease` | Szekció fade-in, layout shift |
| **Glow** | `0.4s ease` | Aceternity glow opacity |

### 11.2. Hover Effektek

```css
/* Kartya hover — felemelkedes */
.card:hover {
  transform: translateY(-4px);
}

/* Link/gomb hover — szin valtas */
.btn:hover {
  /* szin valtas, lasd gomb definiociokat */
}

/* Kep hover — enyhe zoom */
.image-container:hover img {
  transform: scale(1.03);
  transition: transform 0.5s ease;
}
```

### 11.3. Scroll Animaciok

```css
/* Fade-in from bottom */
.animate-on-scroll {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.animate-on-scroll.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Staggered children (kartya grid) */
.stagger-children > *:nth-child(1) { transition-delay: 0s; }
.stagger-children > *:nth-child(2) { transition-delay: 0.1s; }
.stagger-children > *:nth-child(3) { transition-delay: 0.2s; }
```

### 11.4. Specialis Effektek

**Aceternity Glowing Border:**
- Szekció: Feature kartyak (pricing, szolgaltatasok)
- Trigger: Mouse enter
- Technológia: CSS `mask-composite: intersect` + JS `Math.atan2()` mouse tracking
- Részletes implementáció: `v6-aceternity-glowing.html`

**Carousel / Logo scroll:**
- Folyamatos horizontal scroll animation
- `animation: scroll 20s linear infinite`
- Pause on hover

---

## 12. FOOTER DESIGN

```css
.footer {
  background: #12110E;
  color: #FFFFFF;
  padding: 80px 0 40px;
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
  margin-bottom: 60px;
}

.footer-heading {
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 24px;
}

.footer-link {
  font-size: 14px;
  font-weight: 400;
  color: #8D96A3;
  text-decoration: none;
  display: block;
  padding: 6px 0;
  transition: color 0.2s ease;
}
.footer-link:hover {
  color: #FFFFFF;
}

.footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-copyright {
  font-size: 14px;
  color: #8D96A3;
}
```

---

## 13. NEWSLETTER CTA SZEKCIÓ

```css
.newsletter-section {
  background: #12110E;
  border-radius: 24px;
  padding: 60px;
  /* Opcionalisan: hatterkep overlay narancs gradienssel */
  background-image: /* decorativ gradient overlay */;
  background-size: cover;
}

.newsletter-title {
  font-size: 40px;
  font-weight: 400;
  color: #FFFFFF;
  letter-spacing: -1.2px;
}

.newsletter-form {
  display: flex;
  gap: 12px;
  align-items: center;
}
```

---

## 14. AUTOCOGNITIX-SPECIALIS ADAPTACIOK

### 14.1. Szin Bovites az Autós Temához

Az Anorva paletta bovitese az AutoCognitix DTC / diagnosztika vilaghoz:

| Szin | Hex | Hasznalat |
|------|-----|-----------|
| **Success Green** | `#22C55E` | Sikeres diagnózis, "Nincs kritikus hiba" |
| **Warning Amber** | `#F59E0B` | Figyelmeztetés, közepes prioritasu hiba |
| **Error Red** | `#EF4444` | Kritikus hiba, sulyos DTC kod |
| **Info Blue** | `#3B82F6` | Informativ, tipp, "Tudtad hogy?" |

Ezeket KIZAROLAG a diagnosztikai interfesz es eredmeny oldalon hasznaljuk, a landing page-en NEM.

### 14.2. DTC Kod Tipografia

```css
.dtc-code {
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #12110E;
  background: #E4E4E7;
  padding: 4px 12px;
  border-radius: 6px;
}
```

### 14.3. AutoCognitix Logo Hasznalat

| Kontextus | Logo verzió |
|-----------|-------------|
| Light hatter | Sötét logo (#12110E) |
| Dark hatter | Feher logo (#FFFFFF) |
| Minimum meret | 120px szelesseg |
| Kizarasi zóna | Logo magassag × 0.5 minden oldalon |

### 14.4. Magyar Nyelvi Specifikumok a Designban

- **Szoveg hosszusag:** Magyar szöveg ~15-20%-kal hosszabb mint angol — tervezz rá!
- **Ékezetek:** Font MUSZAJ tamogassa a teljes magyar karakterkeszletet (á, é, í, ó, ö, ő, ú, ü, ű)
- **Funnel Sans:** Tamogatja a magyar ekezetes karaktereket (ellenorizve)
- **Line-height:** A magyar ekezetek miatt 1.6+ line-height ajanlott body-ban

---

## 15. DO'S AND DON'TS — VIZUALIS CHECKLIST

### DO (Csinalj)

- Hasznalj generous whitespace-t (120px section padding)
- Heading-eket Regular (400) sulyban tartsd — a meret beszél
- Tartsd a text-width-ot 65ch alatt
- Kartya hover-re mindig adj finom emelkedest
- Sötét es vilagos szekciokat valtogasd ritmikusan
- Hasznalj valos, meleg tonusu fotokat
- Button szöveg MINDIG uppercase + extra letter-spacing
- Az akcent szin (#D97757) legyen takarekosan, glow/hover effektekhez

### DON'T (Ne csinalj)

- NE hasznalj bold (700) heading-eket — túl nehéz, olcsó hatás
- NE tegyel tobb mint 2 CTA gombot egymasra
- NE hasznalj eles sarkokat (border-radius: 0) sehol
- NE zsufold tele a szekciokat — ha kétséges, adj hozza tobb teret
- NE hasznalj stock illusztraciokat vagy flat vector ikonokat
- NE keverd a szinpalettát mas szinekkel (foleg nem neon/vibrálóval)
- NE hasznalj border-t kartyakon, ha shadow is van — valaszd az egyiket
- NE legyen a hatter soha tiszta feher (#FFFFFF) — mindig az off-white #F2F2F4

---

## 16. CSS VALTOZOK (Custom Properties) — IMPLEMENTACIOS REFERENCIA

```css
:root {
  /* Colors */
  --color-base-light: #F2F2F4;
  --color-base-dark: #12110E;
  --color-accent: #D97757;
  --color-white: #FFFFFF;
  --color-gray-200: #E4E4E7;
  --color-gray-300: #D6D6DA;
  --color-muted: #8D96A3;
  --color-info-surface: #F4F8FA;

  /* Diagnostic Colors (only for app UI) */
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;

  /* Typography */
  --font-primary: "Funnel Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;

  /* Font Sizes */
  --text-display: 80px;
  --text-h2: 56px;
  --text-h3: 40px;
  --text-h4: 28px;
  --text-h5: 22px;
  --text-h6: 18px;
  --text-body-lg: 22px;
  --text-body: 16px;
  --text-body-sm: 14px;
  --text-caption: 12px;

  /* Spacing */
  --space-xs: 8px;
  --space-sm: 12px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 40px;
  --space-3xl: 48px;
  --space-4xl: 60px;
  --space-5xl: 80px;
  --space-section: 120px;
  --space-hero-top: 180px;

  /* Border Radius */
  --radius-xs: 4px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-2xl: 24px;
  --radius-full: 100px;

  /* Shadows */
  --shadow-xs: rgba(16, 24, 40, 0.05) 1px 1px 2px 0px;
  --shadow-sm: rgba(0, 0, 0, 0.2) 0px 0px 1px 0px;
  --shadow-md: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 1px 3px 0px;
  --shadow-lg: rgba(0, 0, 0, 0.1) 0px 0px 0px 1px, rgba(0, 0, 0, 0.15) 0px 4px 12px 0px;
  --shadow-glow: rgba(217, 119, 87, 0.5) 0px 0px 10px 0px inset,
                 rgba(217, 119, 87, 0.3) 0px 0px 20px 0px inset,
                 rgba(217, 119, 87, 0.1) 0px 0px 30px 0px inset;

  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.5s ease;

  /* Layout */
  --container-max: 1200px;
  --container-padding: 24px;
}
```

---

## 17. FAJL REFERENCIA

| Fajl | Leiras |
|------|--------|
| `v6-aceternity-glowing.html` | Aceternity glowing border implementacio |
| `v7-serif-orange.html` | Korabbi serif/orange landing page valtozat |
| `brand-voice-guidelines.md` | Nyelvi es kommunikacios iranyelvek |
| `legal-risk-assessment.md` | Jogi megfelelosegi elemzes |
| `communication-strategy.md` | Kommunikacios strategia |
| `feature-inventory.md` | Feature lista es piackutatás |

---

*Ez a dokumentum az AutoCognitix vizualis identitasanak egyetlen igazsagforrasa (single source of truth). Minden uj oldal, komponens es marketing anyag ebbol a rendszerbol kell hogy épüljön.*
