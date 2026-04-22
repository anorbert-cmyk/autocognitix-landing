"""
Brand/model mappings for hasznaltauto.hu scraper.

Slugs match the URL pattern:
  https://www.hasznaltauto.hu/szemelyauto/{brand_slug}/{model_slug}/...

Canonical keys (brand + model) MUST match shared/data/hungarian-market-prices.json
so aggregate-prices.py can join scraped observations to seeded estimates without
silent case/spelling drift. The slug values are the actual hasznaltauto URL
fragments and are independent of the canonical key. If you change a key here,
verify the URL still resolves (the slug stays the same; only the dict key needs
to match the prices.json taxonomy).

Wave 4 (2026-04-21): brand/model keys aligned to prices.json taxonomy.
- BMW models renamed: "3-series" -> "3-Series" etc. (case-sensitive match needed)
- Mercedes-Benz models renamed: "A-class" -> "A-Class" etc.
- Suzuki: added S-Cross/Jimny/Alto/Splash/Wagon R+ + renamed SX4 entry slug
- Opel: added Grandland/Zafira/Meriva/Vectra/Combo
- Skoda: replaced Fabia/Kamiq with Karoq (per prices.json)
- Renault: added Kadjar (already present), removed/kept by prices.json
- Peugeot: added 5008
- Citroen: replaced C3/C4 sub-variants per prices.json
- Fiat: added Doblo, removed Punto (not in prices.json)
- Hyundai: added i10, removed ix35
- Kia: added Rio, removed Picanto
- Honda: added "e", removed Accord
- Mazda: added 2 + 6, removed CX-3/CX-30 dup
- Volvo: added XC90, removed V40
- Mitsubishi: kept all 5
- Alfa Romeo: added Tonale, removed 159
- Mini: brand removed (not in prices.json)
- Jeep: brand removed (not in prices.json)
- Chevrolet: ADDED (was missing) — slugs follow hasznaltauto convention
- Lancia: ADDED (was missing) — production-cap years note in prices.json
"""

BRANDS = {
    "Suzuki": {
        "slug": "suzuki",
        "models": {
            "Swift": "swift",
            "Vitara": "vitara",
            "S-Cross": "s-cross",
            "Ignis": "ignis",
            "Jimny": "jimny",
            "SX4": "sx4",
            "Baleno": "baleno",
            "Alto": "alto",
            "Splash": "splash",
            "Wagon R+": "wagon_r_",
        },
    },
    "Opel": {
        "slug": "opel",
        "models": {
            "Astra": "astra",
            "Corsa": "corsa",
            "Mokka": "mokka",
            "Crossland": "crossland_x",
            "Grandland": "grandland_x",
            "Insignia": "insignia",
            "Zafira": "zafira",
            "Meriva": "meriva",
            "Vectra": "vectra",
            "Combo": "combo",
        },
    },
    "Volkswagen": {
        "slug": "volkswagen",
        "models": {
            "Golf": "golf",
            "Polo": "polo",
            "Tiguan": "tiguan",
            "Passat": "passat",
            "T-Roc": "t-roc",
        },
    },
    "Skoda": {
        "slug": "skoda",
        "models": {
            "Octavia": "octavia",
            "Fabia": "fabia",
            "Superb": "superb",
            "Karoq": "karoq",
            "Kodiaq": "kodiaq",
        },
    },
    "Ford": {
        "slug": "ford",
        "models": {
            "Focus": "focus",
            "Fiesta": "fiesta",
            "Kuga": "kuga",
            "Puma": "puma",
            "Mondeo": "mondeo",
        },
    },
    "Toyota": {
        "slug": "toyota",
        "models": {
            "Corolla": "corolla",
            "Yaris": "yaris",
            "RAV4": "rav4",
            "C-HR": "c-hr",
            "Aygo": "aygo",
        },
    },
    "BMW": {
        "slug": "bmw",
        "models": {
            "3-Series": "3-as_sorozat",
            "1-Series": "1-es_sorozat",
            "5-Series": "5-os_sorozat",
            "X1": "x1",
            "X3": "x3",
            "X5": "x5",
            "2-es": "2-es_sorozat",
            "4-es": "4-es_sorozat",
            "7-es": "7-es_sorozat",
            "i3": "i3",
        },
    },
    "Audi": {
        "slug": "audi",
        "models": {
            "A3": "a3",
            "A4": "a4",
            "A6": "a6",
            "Q3": "q3",
            "Q5": "q5",
        },
    },
    "Mercedes-Benz": {
        "slug": "mercedes-benz",
        "models": {
            "A-Class": "a_osztaly",
            "C-Class": "c_osztaly",
            "E-Class": "e_osztaly",
            "GLA": "gla",
            "GLC": "glc",
        },
    },
    "Renault": {
        "slug": "renault",
        "models": {
            "Clio": "clio",
            "Megane": "megane",
            "Captur": "captur",
            "Kadjar": "kadjar",
            "Scenic": "scenic",
        },
    },
    "Peugeot": {
        "slug": "peugeot",
        "models": {
            "208": "208",
            "308": "308",
            "2008": "2008",
            "3008": "3008",
            "5008": "5008",
        },
    },
    "Citroen": {
        "slug": "citroen",
        "models": {
            "C3": "c3",
            "C4": "c4",
            "C3 Aircross": "c3_aircross",
            "C5 Aircross": "c5_aircross",
            "Berlingo": "berlingo",
        },
    },
    "Fiat": {
        "slug": "fiat",
        "models": {
            "500": "500",
            "Panda": "panda",
            "Tipo": "tipo",
            "500X": "500x",
            "Doblo": "doblo",
        },
    },
    "Hyundai": {
        "slug": "hyundai",
        "models": {
            "i30": "i30",
            "i20": "i20",
            "Tucson": "tucson",
            "Kona": "kona",
            "i10": "i10",
        },
    },
    "Kia": {
        "slug": "kia",
        "models": {
            "Ceed": "ceed",
            "Sportage": "sportage",
            "Rio": "rio",
            "Stonic": "stonic",
            "Niro": "niro",
        },
    },
    "Dacia": {
        "slug": "dacia",
        "models": {
            "Sandero": "sandero",
            "Duster": "duster",
            "Logan": "logan",
            "Jogger": "jogger",
            "Spring": "spring",
        },
    },
    "Honda": {
        "slug": "honda",
        "models": {
            "Civic": "civic",
            "HR-V": "hr-v",
            "CR-V": "cr-v",
            "Jazz": "jazz",
            "e": "e",
        },
    },
    "Mazda": {
        "slug": "mazda",
        "models": {
            "3": "3",
            "CX-5": "cx-5",
            "CX-30": "cx-30",
            "2": "2",
            "6": "6",
        },
    },
    "Nissan": {
        "slug": "nissan",
        "models": {
            "Qashqai": "qashqai",
            "Juke": "juke",
            "Micra": "micra",
            "X-Trail": "x-trail",
            "Leaf": "leaf",
        },
    },
    "Seat": {
        "slug": "seat",
        "models": {
            "Leon": "leon",
            "Ibiza": "ibiza",
            "Arona": "arona",
            "Ateca": "ateca",
            "Tarraco": "tarraco",
        },
    },
    "Volvo": {
        "slug": "volvo",
        "models": {
            "XC40": "xc40",
            "XC60": "xc60",
            "V60": "v60",
            "S60": "s60",
            "XC90": "xc90",
        },
    },
    "Mitsubishi": {
        "slug": "mitsubishi",
        "models": {
            "ASX": "asx",
            "Outlander": "outlander",
            "Eclipse Cross": "eclipse_cross",
            "Space Star": "space_star",
            "L200": "l200",
        },
    },
    "Chevrolet": {
        "slug": "chevrolet",
        "models": {
            "Spark": "spark",
            "Aveo": "aveo",
            "Cruze": "cruze",
            "Trax": "trax",
            "Orlando": "orlando",
        },
    },
    "Alfa Romeo": {
        "slug": "alfa_romeo",
        "models": {
            "Giulietta": "giulietta",
            "Giulia": "giulia",
            "Stelvio": "stelvio",
            "MiTo": "mito",
            "Tonale": "tonale",
        },
    },
    "Lancia": {
        "slug": "lancia",
        "models": {
            "Ypsilon": "ypsilon",
            "Delta": "delta",
            "Musa": "musa",
            "Voyager": "voyager",
            "Thema": "thema",
        },
    },
}

# Rate limiting: seconds between requests
REQUEST_DELAY = 2.0

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# User-Agent for polite scraping
USER_AGENT = (
    "AutoCognitix-PriceBot/1.0 "
    "(+https://autocognitix.hu; market research; respectful crawling)"
)

# Maximum number of listing URLs to process per brand/model query
MAX_LISTINGS_PER_QUERY = 200

# Maximum number of sub-sitemaps to process
MAX_SUB_SITEMAPS = 50
