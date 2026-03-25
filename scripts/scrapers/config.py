"""
Brand/model mappings for hasznaltauto.hu scraper.

Slugs match the URL pattern:
  https://www.hasznaltauto.hu/szemelyauto/{brand_slug}/{model_slug}/...
"""

BRANDS = {
    "Suzuki": {
        "slug": "suzuki",
        "models": {
            "Swift": "swift",
            "Vitara": "vitara",
            "SX4": "sx4_s-cross",
            "Baleno": "baleno",
            "Ignis": "ignis",
        },
    },
    "Opel": {
        "slug": "opel",
        "models": {
            "Astra": "astra",
            "Corsa": "corsa",
            "Mokka": "mokka",
            "Insignia": "insignia",
            "Crossland": "crossland_x",
        },
    },
    "Volkswagen": {
        "slug": "volkswagen",
        "models": {
            "Golf": "golf",
            "Passat": "passat",
            "Polo": "polo",
            "Tiguan": "tiguan",
            "T-Roc": "t-roc",
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
    "Skoda": {
        "slug": "skoda",
        "models": {
            "Octavia": "octavia",
            "Fabia": "fabia",
            "Superb": "superb",
            "Kodiaq": "kodiaq",
            "Kamiq": "kamiq",
        },
    },
    "BMW": {
        "slug": "bmw",
        "models": {
            "3-series": "3-as_sorozat",
            "5-series": "5-os_sorozat",
            "X1": "x1",
            "X3": "x3",
            "1-series": "1-es_sorozat",
        },
    },
    "Mercedes-Benz": {
        "slug": "mercedes-benz",
        "models": {
            "A-class": "a_osztaly",
            "C-class": "c_osztaly",
            "E-class": "e_osztaly",
            "GLA": "gla",
            "GLC": "glc",
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
    "Renault": {
        "slug": "renault",
        "models": {
            "Clio": "clio",
            "Megane": "megane",
            "Captur": "captur",
            "Scenic": "scenic",
            "Kadjar": "kadjar",
        },
    },
    "Peugeot": {
        "slug": "peugeot",
        "models": {
            "208": "208",
            "308": "308",
            "2008": "2008",
            "3008": "3008",
            "508": "508",
        },
    },
    "Citroen": {
        "slug": "citroen",
        "models": {
            "C3": "c3",
            "C4": "c4",
            "C5 Aircross": "c5_aircross",
            "Berlingo": "berlingo",
            "C3 Aircross": "c3_aircross",
        },
    },
    "Hyundai": {
        "slug": "hyundai",
        "models": {
            "i30": "i30",
            "Tucson": "tucson",
            "i20": "i20",
            "Kona": "kona",
            "ix35": "ix35",
        },
    },
    "Kia": {
        "slug": "kia",
        "models": {
            "Ceed": "ceed",
            "Sportage": "sportage",
            "Picanto": "picanto",
            "Niro": "niro",
            "Stonic": "stonic",
        },
    },
    "Fiat": {
        "slug": "fiat",
        "models": {
            "500": "500",
            "Panda": "panda",
            "Tipo": "tipo",
            "Punto": "punto",
            "500X": "500x",
        },
    },
    "Dacia": {
        "slug": "dacia",
        "models": {
            "Duster": "duster",
            "Sandero": "sandero",
            "Logan": "logan",
            "Spring": "spring",
            "Jogger": "jogger",
        },
    },
    "Honda": {
        "slug": "honda",
        "models": {
            "Civic": "civic",
            "CR-V": "cr-v",
            "Jazz": "jazz",
            "HR-V": "hr-v",
            "Accord": "accord",
        },
    },
    "Mazda": {
        "slug": "mazda",
        "models": {
            "3": "3",
            "6": "6",
            "CX-5": "cx-5",
            "CX-3": "cx-3",
            "CX-30": "cx-30",
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
            "XC60": "xc60",
            "XC40": "xc40",
            "V40": "v40",
            "V60": "v60",
            "S60": "s60",
        },
    },
    "Mitsubishi": {
        "slug": "mitsubishi",
        "models": {
            "Outlander": "outlander",
            "ASX": "asx",
            "Eclipse Cross": "eclipse_cross",
            "Space Star": "space_star",
            "L200": "l200",
        },
    },
    "Jeep": {
        "slug": "jeep",
        "models": {
            "Renegade": "renegade",
            "Compass": "compass",
            "Cherokee": "cherokee",
            "Wrangler": "wrangler",
            "Grand Cherokee": "grand_cherokee",
        },
    },
    "Alfa Romeo": {
        "slug": "alfa_romeo",
        "models": {
            "Giulietta": "giulietta",
            "Giulia": "giulia",
            "Stelvio": "stelvio",
            "MiTo": "mito",
            "159": "159",
        },
    },
    "Mini": {
        "slug": "mini",
        "models": {
            "Cooper": "cooper",
            "Countryman": "countryman",
            "Clubman": "clubman",
            "One": "one",
            "Cabrio": "cabrio",
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
