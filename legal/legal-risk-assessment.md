# AutoCognitix — Jogi Kockázatelemzés és Megfelelőségi Terv

**Dátum:** 2026-03-21
**Értékelő:** AI Legal Risk Assessment (jogi felülvizsgálat szükséges)
**Tárgy:** AutoCognitix AI-alapú autódiagnosztikai platform — európai piacra lépés
**Privilegizált:** Nem — belső üzleti célú dokumentum

> **FONTOS JOGI NYILATKOZAT:** Ez a dokumentum nem minősül jogi tanácsadásnak. Kockázatelemzés és ajánlás, amelyet képzett jogász szakembernek kell felülvizsgálnia a véglegesítés előtt. A framework kiindulópontként szolgál, amelyet az AutoCognitix sajátos kockázatvállalási hajlandóságához és az iparági kontextushoz kell igazítani.

---

## 1. ÖSSZEFOGLALÓ KOCKÁZATI MÁTRIX

```
                    VALÓSZÍNŰSÉG
                Távoli  Val.tlen  Lehetséges  Valószínű  Szinte biztos
                  (1)     (2)       (3)         (4)         (5)
SÚLYOSSÁG
Kritikus  (5)  |       |         |    R6     |           |             |
Magas     (4)  |       |   R3    |  R1,R4,R7 |    R5     |             |
Közepes   (3)  |       |   R8    |    R2     |   R10     |             |
Alacsony  (2)  |       |         |    R9     |           |             |
Elhanyag. (1)  |       |         |           |           |             |
```

### Kockázatok összesítése

| ID | Kockázat | Súly. | Val. | Pont | Szint |
|----|----------|-------|------|------|-------|
| R1 | AI felelősség — hibás diagnózis | 4 | 3 | **12** | 🟠 MAGAS |
| R2 | GDPR / adatvédelmi megfelelés | 3 | 3 | **9** | 🟡 KÖZEPES |
| R3 | EU AI Act megfelelés | 4 | 2 | **8** | 🟡 KÖZEPES |
| R4 | Fogyasztóvédelmi kommunikáció | 4 | 3 | **12** | 🟠 MAGAS |
| R5 | Gépjármű-biztonsági felelősség | 4 | 4 | **16** | 🔴 KRITIKUS |
| R6 | Orvosi/szerviz tanácsadási engedélyek | 5 | 3 | **15** | 🟠 MAGAS |
| R7 | Szellemi tulajdon — adatforrások (NHTSA, OBDb) | 4 | 3 | **12** | 🟠 MAGAS |
| R8 | Árazási állítások felelőssége | 3 | 2 | **6** | 🟡 KÖZEPES |
| R9 | Marketing kommunikáció — félrevezető állítások | 2 | 3 | **6** | 🟡 KÖZEPES |
| R10 | Multi-piaci jogi fragmentáció | 3 | 4 | **12** | 🟠 MAGAS |

---

## 2. RÉSZLETES KOCKÁZATELEMZÉSEK

---

### R1: AI FELELŐSSÉG — HIBÁS DIAGNÓZIS

**Kockázati leírás:** Az AI rendszer hibás diagnózist ad, a felhasználó ennek alapján helytelen javítást végez, ami anyagi kárhoz vagy jármű károsodáshoz vezet.

**Háttér és kontextus:**
- Az AutoCognitix AI-alapú RAG rendszert használ (LangChain + Claude/GPT-4)
- Konfidencia-értékelést ad (high/medium/low), de ez nem garancia
- A felhasználók DIY javításokat végezhetnek az AI javaslatok alapján
- A tervezett mobilapp AI agentje kamerán keresztül vezeti a javítást

**Súlyosság: 4 (Magas)**
- Hibás diagnózis → helytelen javítás → anyagi kár (alkatrészek, munkadíj)
- Extrém esetben: biztonsági kockázat (fékrendszer, kormánymű hibás diagnózisa)
- Jogi igény lehetősége: kártérítés, termékfelelősség

**Valószínűség: 3 (Lehetséges)**
- AI rendszerek hallucination kockázata ismert
- 63+ DTC kód, 26 800+ csomópont — de nem teljes lefedettség
- A konfidencia-értékelés csökkenti, de nem eliminálja a kockázatot

**Kockázati pont: 12 — 🟠 MAGAS**

**Növelő tényezők:**
- AI hallucination (LLM-ek ismert korlátja)
- Nem teljes DTC adatbázis (63 kód vs. 10 000+ létező kód)
- Magyar nyelvű feldolgozás — kisebb tréning adathalmaz
- Felhasználók túlzott bizalom az AI-ban

**Csökkentő tényezők:**
- Konfidencia-értékelés minden diagnózisnál
- RAG alapú keresés (nem csak LLM hallucination)
- Brand voice guidelines: "becslés", nem "diagnózis"

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség/Erőfeszítés | Javasolt? |
|---|---|---|---|
| ÁSZF-be felelősségi nyilatkozat (disclaimer) | Magas | Alacsony | ✅ Igen |
| UI-ban kötelező figyelmeztetés minden diagnózisnál | Magas | Alacsony | ✅ Igen |
| Biztonsági kódoknál (fék, kormány, légzsák) automatikus "fordulj szakemberhez" üzenet | Magas | Közepes | ✅ Igen |
| Konfidencia-küszöb: <60% alatt nem ad javítási javaslatot | Közepes | Közepes | ✅ Igen |
| Szakmai felelősségbiztosítás (E&O insurance) | Magas | Magas | ✅ Igen |
| Felhasználói visszaigazolás ("Megértettem, hogy ez AI becslés") | Közepes | Alacsony | ✅ Igen |

**Javasolt megközelítés:**
Implementálj háromszintű felelősségi rendszert:
1. **Regisztrációkor:** ÁSZF elfogadás AI-felelősségi nyilatkozattal
2. **Minden diagnózisnál:** "Ez AI-alapú elemzés, nem szakszerviz diagnózis"
3. **Biztonsági kódoknál:** Blokkoló figyelmeztetés + "Fordulj szakemberhez!"

**Reziduális kockázat:** 🟡 KÖZEPES (6-8 pont) a mérséklések után

---

### R2: GDPR / ADATVÉDELMI MEGFELELÉS

**Kockázati leírás:** A platform személyes adatokat kezel (email, jármű VIN, diagnosztikai előzmények) — EU-s GDPR megfelelés szükséges.

**Háttér és kontextus:**
- PostgreSQL: Users, Sessions, History tárolás
- VIN dekódolás → járműazonosítás (potenciálisan személyes adat)
- Diagnosztikai előzmények → felhasználó autóhasználati profil
- Redis: session cache
- Qdrant: embeddings (anonimizáltak, de a forrásadat visszakövethető)
- Railway deployment (EU/US régió?)

**Súlyosság: 3 (Közepes)**
- GDPR bírság: max 4% éves árbevétel vagy €20M (de startup-nál arányosabb)
- Reputációs kár egy adatszivárgásnál
- Felhasználói bizalom elvesztése

**Valószínűség: 3 (Lehetséges)**
- Startup fázis → GDPR compliance gyakran nem teljes
- VIN = potenciálisan személyes adat (járműtulajdonoshoz köthető)
- Több adatbázis = több támadási felület

**Kockázati pont: 9 — 🟡 KÖZEPES**

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség | Javasolt? |
|---|---|---|---|
| Adatvédelmi tájékoztató (Privacy Policy) magyar + angol | Magas | Alacsony | ✅ Igen |
| Cookie policy + consent banner | Magas | Alacsony | ✅ Igen |
| GDPR Data Processing Agreement (DPA) a Railway-jel | Magas | Alacsony | ✅ Igen |
| VIN anonimizálás/hashelés a tárolásban | Közepes | Közepes | ✅ Igen |
| Felhasználói adat export/törlés funkció (GDPR Art. 15, 17) | Magas | Közepes | ✅ Igen |
| Data Protection Impact Assessment (DPIA) | Magas | Közepes | ✅ Igen |
| Adatvédelmi tisztviselő (DPO) kijelölése (ha szükséges) | Közepes | Magas | ⚠️ Értékelendő |
| EU-s hosting biztosítása (Railway EU régió) | Magas | Alacsony | ✅ Igen |

**Javasolt megközelítés:**
1. **Azonnal:** Privacy Policy + Cookie Policy elkészítése
2. **Launch előtt:** DPIA elvégzése, DPA Railway-jel, GDPR Art. 15/17 funkciók
3. **6 hónapon belül:** DPO szükségességének értékelése (felhasználószámtól függően)

**Reziduális kockázat:** 🟢 ALACSONY (3-4 pont) megfelelő implementáció után

---

### R3: EU AI ACT MEGFELELÉS

**Kockázati leírás:** Az EU AI Act (2024/1689 rendelet) 2026-ban lépett hatályba — AI rendszerek kockázat-alapú osztályozása és megfelelési kötelezettségek.

**Háttér és kontextus:**
- Az AutoCognitix AI rendszer diagnosztikai javaslatokat ad
- Gépjárművek biztonsági rendszereire is vonatkozhat (fék, kormány DTC-k)
- RAG + LLM kombináció → "general-purpose AI" kategória lehetséges
- 2026 augusztustól a legtöbb kötelezettség érvényes

**Súlyosság: 4 (Magas)**
- AI Act bírság: max €35M vagy 7% globális árbevétel
- Compliance hiánya → EU piacról való kizárás
- Reputációs kár

**Valószínűség: 2 (Valószínűtlen, de fejlődő)**
- Az AutoCognitix valószínűleg "limited risk" vagy "minimal risk" kategória
- NEM orvosi eszköz, NEM biztonsági rendszer (hanem információs eszköz)
- De a biztonsági kódoknál a határvonal elmosódik

**Kockázati pont: 8 — 🟡 KÖZEPES**

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség | Javasolt? |
|---|---|---|---|
| AI Act kockázat-osztályozás elvégzése (legal review) | Magas | Közepes | ✅ Igen |
| Átláthatósági kötelezettség: jelölés, hogy AI generálja a tartalmat | Magas | Alacsony | ✅ Igen |
| AI rendszer dokumentáció (model card, data card) | Közepes | Közepes | ✅ Igen |
| Biztonsági kódok elkülönítése — explicit disclaimer | Magas | Alacsony | ✅ Igen |
| Emberi felülvizsgálat lehetőségének biztosítása | Közepes | Közepes | ⚠️ Értékelendő |

**Javasolt megközelítés:**
1. **Launch előtt:** AI Act osztályozás jogi szakértővel
2. **UI-ban:** "Ez az eredmény AI által generált" jelölés minden diagnózisnál
3. **Dokumentáció:** Model card, adatforrások listája, pontossági metrikák

**Reziduális kockázat:** 🟢 ALACSONY (4 pont) osztályozás és compliance után

---

### R4: FOGYASZTÓVÉDELMI KOMMUNIKÁCIÓ

**Kockázati leírás:** A marketing kommunikáció állításai (pl. "profi szintű diagnosztika", "26 800+ csomópont", megtakarítási ígéretek) félrevezetőnek minősülhetnek.

**Háttér és kontextus:**
- A landing page állítások: "92% of users report feeling more confident", "Average repair cost savings: €340/year"
- A kommunikációs stratégia "fictional but relatable" proof pointokat tartalmaz
- Brand voice: "Masszív szervízdíjak nélkül tudod meg, mi a gond"
- Ár-összehasonlítások szervizekkel
- "Profi szintű diagnosztika" állítás

**Súlyosság: 4 (Magas)**
- Magyar Fogyasztóvédelmi Hatóság (NFH) bírság
- EU-szintű Unfair Commercial Practices Directive megsértése
- Versenytársi feljelentés lehetősége
- Médiabotrány kockázat ("megtévesztő app")

**Valószínűség: 3 (Lehetséges)**
- A "fictional but relatable" proof pointok nyíltan fiktívek a belső dokumentumban
- Ha ezek a landing page-re kerülnek valós adatként → félrevezető
- A "profi szintű" állítás bizonyítandó

**Kockázati pont: 12 — 🟠 MAGAS**

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség | Javasolt? |
|---|---|---|---|
| Fiktív statisztikák eltávolítása a landing page-ről | Magas | Alacsony | ✅ Azonnal |
| Állítások alátámasztása valós adatokkal (beta teszt) | Magas | Közepes | ✅ Igen |
| "Profi szintű" → "haladó" vagy pontosabb megfogalmazás | Közepes | Alacsony | ✅ Igen |
| Árazási összehasonlítások forrásmegjelöléssel | Közepes | Alacsony | ✅ Igen |
| Jogi review a marketing anyagokról launch előtt | Magas | Közepes | ✅ Igen |
| "Eredmények egyénenként eltérhetnek" disclaimerek | Közepes | Alacsony | ✅ Igen |

**Javasolt megközelítés:**
1. **Azonnal:** Fiktív proof pointok eltávolítása vagy "illusztráció" jelöléssel
2. **Beta fázisban:** Valós felhasználói adatok gyűjtése az állítások alátámasztásához
3. **Launch előtt:** Fogyasztóvédelmi jogi review minden marketing anyagon

**Reziduális kockázat:** 🟢 ALACSONY (4 pont) valós adatok és disclaimerek után

---

### R5: GÉPJÁRMŰ-BIZTONSÁGI FELELŐSSÉG 🔴 KRITIKUS

**Kockázati leírás:** A felhasználó biztonsági rendszerre (fék, kormány, légzsák, ABS) vonatkozó hibás AI diagnózis alapján cselekszik, ami balesethez, sérüléshez vagy halálhoz vezet.

**Háttér és kontextus:**
- A DTC adatbázis tartalmaz biztonsági rendszer kódokat (C prefixű chassis kódok)
- A mobilapp kamerás AI segédje fékrendszeri javításra is adhat útmutatást
- A brand voice: "Ezt a cserét otthon is elvégezheted... de fékrendszernél bízd szakemberre"
- Ez a legkomolyabb jogi kockázat: személyi sérülés / haláleset → polgári és büntetőjogi felelősség

**Súlyosság: 4 (Magas) → Potenciálisan 5 (Kritikus)**
- Személyi sérülés / haláleset → kártérítési igények (millió Ft-os nagyságrend)
- Büntetőjogi felelősség lehetősége (gondatlanság)
- Termékfelelősségi per
- Teljes üzlet ellehetetlenülése

**Valószínűség: 4 (Valószínű)**
- A felhasználók egy része biztonsági rendszeren is próbálkozik DIY javítással
- A "kamerás AI segéd" különösen kockázatos biztonsági munkáknál
- Nincs fizikai ellenőrzés — az AI nem látja a valós állapotot (csak a kód alapján dolgozik)

**Kockázati pont: 16 — 🔴 KRITIKUS**

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség | Javasolt? |
|---|---|---|---|
| **Biztonsági kódok kategorizálása és elkülönítése** | Magas | Közepes | ✅ Azonnal kötelező |
| **Blokkoló figyelmeztetés biztonsági kódoknál** | Magas | Alacsony | ✅ Azonnal kötelező |
| **"NE javítsd otthon" explicit figyelmeztetés** fék/kormány/légzsák kódoknál | Magas | Alacsony | ✅ Azonnal kötelező |
| **Mobilapp: biztonsági rendszer javítás kizárása** a kamerás AI segédből | Magas | Közepes | ✅ Igen |
| **Termékfelelősségi biztosítás** (product liability insurance) | Magas | Magas | ✅ Igen |
| **ÁSZF: biztonsági rendszeri felelősség explicit kizárása** | Magas | Alacsony | ✅ Igen |
| **Biztonsági audit** a DTC adatbázis biztonsági kódjairól | Közepes | Közepes | ✅ Igen |

**Javasolt megközelítés:**
1. **AZONNAL:** Biztonsági kódok (fék, kormány, légzsák, ABS, ESP, SRS) listázása és jelölése
2. **Launch előtt:** Blokkoló UI — biztonsági kódoknál NEM ad javítási lépéseket, CSAK "fordulj szakemberhez"
3. **Mobilapp:** Kamerás AI segéd KIZÁRJA a biztonsági rendszereket
4. **Biztosítás:** Termékfelelősségi biztosítás kötése

**Reziduális kockázat:** 🟡 KÖZEPES (8 pont) teljes mérséklés után — a kockázat soha nem eliminálandó teljesen

---

### R6: SZERVIZ-TANÁCSADÁSI ENGEDÉLYEK

**Kockázati leírás:** Egyes EU tagállamokban a gépjármű-diagnosztikai tanácsadás szabályozott tevékenység lehet — engedélyköteles vagy regisztrációs kötelezettséggel.

**Háttér és kontextus:**
- Magyarországon a gépjármű-szerviz tevékenység engedélyköteles
- Az AutoCognitix nem szerviz, hanem "információs platform"
- De a javítási lépések + árbecslés → tanácsadási tevékenységnek minősülhet
- Németországban: TÜV és egyéb szabályozók — diagnosztika erősen szabályozott

**Súlyosság: 5 (Kritikus)**
- Engedély nélküli tevékenység → bírság, betiltás
- Országonként eltérő szabályozás → multi-piaci kockázat

**Valószínűség: 3 (Lehetséges)**
- Az "információs platform" vs. "szerviz-tanácsadás" határvonal elmosódó
- Eddig nem volt precedens AI-alapú autódiagnosztikai app szabályozására HU-ban
- De a német piac sokkal szigorúbb

**Kockázati pont: 15 — 🟠 MAGAS**

**Mérséklési terv:**

| Intézkedés | Hatékonyság | Költség | Javasolt? |
|---|---|---|---|
| Jogi vélemény kérése: "információs platform" vs. "szerviz-tanácsadás" | Magas | Közepes | ✅ Igen |
| ÁSZF: "Nem vagyunk szerviz, nem adunk hivatalos diagnózist" | Magas | Alacsony | ✅ Igen |
| Országspecifikus jogi review (HU, DE, ES, FR, UK) | Magas | Magas | ✅ Igen |
| "Tájékoztatási célú" pozicionálás a UI-ban és marketingben | Közepes | Alacsony | ✅ Igen |
| Regisztráció releváns hatóságoknál ha szükséges | Magas | Közepes | ⚠️ Értékelendő |

**Reziduális kockázat:** 🟡 KÖZEPES (6-8 pont) jogi review és pozicionálás után

---

### R7: SZELLEMI TULAJDON — ADATFORRÁSOK

**Kockázati leírás:** Az NHTSA, OBDb GitHub, és egyéb adatforrások felhasználási jogai nem egyértelműen tisztázottak kereskedelmi célú alkalmazásra.

**Súlyosság: 4 (Magas)** — IP per, adatforrás elvesztése
**Valószínűség: 3 (Lehetséges)** — NHTSA publikus, de kereskedelmi felhasználás szabályai eltérőek
**Kockázati pont: 12 — 🟠 MAGAS**

**Mérséklési terv:**
1. NHTSA API felhasználási feltételek jogi review-ja
2. OBDb GitHub licensz ellenőrzés
3. Saját adatbázis építésének megkezdése (csökkenti a függőséget)
4. Adatforrás-attribúció minden kimeneten

---

### R8: ÁRAZÁSI ÁLLÍTÁSOK FELELŐSSÉGE

**Kockázati leírás:** Az alkatrészár-becslések pontatlanok lehetnek, ami félrevezető árinformációhoz vezet.

**Súlyosság: 3 (Közepes)** — anyagi kár a felhasználónak, fogyasztóvédelmi probléma
**Valószínűség: 2 (Valószínűtlen)** — a "becslés" szó használata csökkenti
**Kockázati pont: 6 — 🟡 KÖZEPES**

**Mérséklési terv:**
1. Mindig "becsült ár" / "tájékoztató jellegű ár" megjelölés
2. Ár-tartomány (min-max) a pontos ár helyett
3. Forrás és dátum megjelölés az áraknál
4. "Az árak változhatnak" disclaimer

---

### R9: MARKETING — FÉLREVEZETŐ ÁLLÍTÁSOK

**Kockázati leírás:** Landing page és social media állítások nem alátámaszthatók.

**Súlyosság: 2 (Alacsony)** — bírság, de kezelhető
**Valószínűség: 3 (Lehetséges)** — fiktív proof pointok jelenleg a stratégiában
**Kockázati pont: 6 — 🟡 KÖZEPES**

**Mérséklési terv:**
1. Fiktív statisztikák eltávolítása vagy "illusztráció" jelöléssel
2. Beta tesztelésből származó valós adatok használata
3. Marketing jogi review launch előtt

---

### R10: MULTI-PIACI JOGI FRAGMENTÁCIÓ

**Kockázati leírás:** 5+ EU ország különböző fogyasztóvédelmi, adatvédelmi és szerviz-szabályozási keretei.

**Súlyosság: 3 (Közepes)** — compliance költségek, piaci késedelem
**Valószínűség: 4 (Valószínű)** — ismert tény az EU fragmentáció
**Kockázati pont: 12 — 🟠 MAGAS**

**Mérséklési terv:**
1. Országonkénti jogi review (nem egységes EU megközelítés)
2. Lokalizált ÁSZF és Privacy Policy minden piacon
3. Szekvenciális piacralépés (HU → DE → ES → FR → UK) — időt ad a compliance-re
4. Helyi jogi partner minden célpiacon

---

## 3. KÖTELEZŐ JOGI DOKUMENTUMOK — LAUNCH ELŐTT

### Azonnali prioritás (Launch előtt kötelező)

| Dokumentum | Státusz | Prioritás | Felelős |
|---|---|---|---|
| **Általános Szerződési Feltételek (ÁSZF)** — HU + EN | ❌ Hiányzik | 🔴 Kritikus | Jogi |
| **Adatvédelmi Tájékoztató (Privacy Policy)** — HU + EN | ❌ Hiányzik | 🔴 Kritikus | Jogi |
| **Cookie Policy + Consent Banner** | ❌ Hiányzik | 🔴 Kritikus | Jogi + Dev |
| **AI Felelősségi Nyilatkozat (AI Disclaimer)** | ❌ Hiányzik | 🔴 Kritikus | Jogi |
| **Biztonsági rendszer figyelmeztetés (Safety Warning)** | ❌ Hiányzik | 🔴 Kritikus | Dev + Jogi |
| **Termékfelelősségi biztosítás** | ❌ Hiányzik | 🟠 Magas | Üzleti |

### Közepes prioritás (Launch utáni 3 hónapon belül)

| Dokumentum | Státusz | Prioritás |
|---|---|---|
| DPIA (Data Protection Impact Assessment) | ❌ Hiányzik | 🟡 Közepes |
| AI Act kockázat-osztályozási dokumentum | ❌ Hiányzik | 🟡 Közepes |
| NHTSA / OBDb felhasználási jogi vélemény | ❌ Hiányzik | 🟡 Közepes |
| Német piaci jogi review | ❌ Hiányzik | 🟡 Közepes |

---

## 4. ÁSZF KULCSELEMEK — AJÁNLOTT STRUKTÚRA

Az ÁSZF-nek az alábbi elemeket kell tartalmaznia:

### 4.1 Szolgáltatás meghatározás
- "Tájékoztatási célú AI-alapú diagnosztikai platform"
- NEM szerviz, NEM hivatalos diagnózis
- NEM helyettesíti a szakszerviz véleményt

### 4.2 AI felelősség korlátozás
- Az AI eredmények becslés jellegűek
- Konfidencia-értékelés tájékoztató jellegű
- A felhasználó saját felelőssége az AI javaslatok alapján hozott döntés

### 4.3 Biztonsági rendszer kizárás
- **EXPLICIT:** Fékrendszer, kormánymű, légzsák, ABS, ESP, SRS hibakódok esetén a platform NEM ad javítási útmutatást
- A felhasználó KÖTELES szakemberhez fordulni

### 4.4 Árazási nyilatkozat
- Alkatrészárak becsült, tájékoztató jellegűek
- Nem minősülnek árajánlatnak
- Valós árak eltérhetnek

### 4.5 Adatkezelés
- GDPR megfelelő adatkezelési tájékoztatás
- Adat export / törlés joga
- Adatmegőrzési időszak

### 4.6 Felelősség korlátozás
- Maximális kártérítés: az előfizetési díj 12 havi összege
- Következményi károk kizárása
- Force majeure

---

## 5. BRAND VOICE JOGI SZEMPONTOK

A brand voice guidelines-ban azonosított jogi érintettségek:

| Brand Voice elem | Jogi kockázat | Javasolt módosítás |
|---|---|---|
| "Diagnózis 3 percen belül" | Félrevezető ha nem teljesül | + "átlagosan" vagy "akár" |
| "Profi szintű diagnosztika" | Bizonyítandó állítás | → "Haladó AI diagnosztika" |
| "26 800+ csomópont" | Verifikálandó szám | ✅ OK ha valós (dokumentáld) |
| "Masszív szervízdíjak nélkül" | Összehasonlító reklám szabályok | + kontextus / forrás |
| Alkatrészárak megjelenítése | Árazási felelősség | + "becsült", "tájékoztató" |
| "92% magabiztosabb" | Fiktív statisztika | ❌ Eltávolítandó amíg nincs valós adat |
| "€340/év megtakarítás" | Fiktív statisztika | ❌ Eltávolítandó amíg nincs valós adat |
| Mobilapp kamerás segéd | Biztonsági felelősség | + Biztonsági rendszer kizárás |

---

## 6. KÖVETKEZŐ LÉPÉSEK ÉS HATÁRIDŐK

### Azonnali (Launch előtt — Q2 2026)
1. ⬜ **ÁSZF + Privacy Policy készítés** — Jogi — 2 hét
2. ⬜ **AI Disclaimer implementálás** a UI-ban — Dev + Jogi — 1 hét
3. ⬜ **Biztonsági kódok kategorizálása** és blokkoló figyelmeztetés — Dev — 1 hét
4. ⬜ **Fiktív statisztikák eltávolítása** a landing page-ről — Marketing — Azonnal
5. ⬜ **Cookie consent banner** implementálás — Dev — 1 hét
6. ⬜ **Termékfelelősségi biztosítás** ajánlatkérés — Üzleti — 2 hét

### Rövid távú (Launch utáni 3 hónap)
7. ⬜ **DPIA elvégzése** — Jogi + DPO — 1 hónap
8. ⬜ **AI Act osztályozás** — Jogi partner — 1 hónap
9. ⬜ **IP jogi review** (NHTSA, OBDb felhasználás) — Jogi — 2 hét
10. ⬜ **Német piaci jogi előkészítés** — Helyi jogi partner — 2 hónap

### Közép távú (6-12 hónap)
11. ⬜ **Multi-piaci ÁSZF lokalizáció** (DE, ES, FR, UK) — Jogi + Fordító — Folyamatos
12. ⬜ **Beta teszt adatok gyűjtése** marketing állítások alátámasztásához — Product — Folyamatos
13. ⬜ **Mobilapp AI agent jogi review** — Jogi — Launch előtt 3 hónap

---

## 7. KÜLSŐ JOGI TANÁCSADÓ BEVONÁS

### Kötelező bevonás
- **ÁSZF és Privacy Policy:** Magyar ügyvéd (fogyasztóvédelem + GDPR szakértelem)
- **Termékfelelősségi biztosítás:** Biztosítási bróker

### Erősen ajánlott
- **AI Act osztályozás:** EU technológiai jogi szakértő
- **Német piac:** Német ügyvéd (Kraftfahrzeug-Sachverständiger szabályozás)
- **IP kérdések:** Szellemi tulajdon jogi szakértő

### Mérlegelendő
- **Több országos launch:** Nemzetközi jogi iroda vagy hálózat
- **Mobilapp biztonsági review:** Termékbiztonsági szakértő

---

*Ez a dokumentum az AutoCognitix jogi kockázatelemzésének kiindulópontja. Minden ajánlást képzett jogi szakembernek kell felülvizsgálnia és az AutoCognitix sajátos körülményeihez igazítania.*
