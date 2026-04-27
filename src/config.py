import os

ZEFIX_API_BASE = "https://www.zefix.ch/ZefixREST/api/v1"
STATE_FILE = "data/seen_companies.json"
LETTERS_DIR = "letters"

# On first run, only process firms registered within this many days
FIRST_RUN_DAYS_LOOKBACK = 30

# All municipalities (Gemeinden) in Bezirk Muri, Kanton Aargau
BEZIRK_MURI_MUNICIPALITIES = {
    "Abtwil",
    "Auw",
    "Besenbüren",
    "Bettwil",
    "Beinwil (Freiamt)",
    "Boswil",
    "Bünzen",
    "Buttwil",
    "Dintikon",
    "Geltwil",
    "Hilfikon",
    "Islisberg",
    "Kallern",
    "Merenschwand",
    "Muri (AG)",
    "Mühlau",
    "Rottenschwil",
    "Sins",
    "Sünikon",
    "Villmergen",
    "Waltenschwil",
}

SENDER_INFO = {
    "company":  os.getenv("SENDER_COMPANY",  "Ihre Treuhand GmbH"),
    "name":     os.getenv("SENDER_NAME",     ""),
    "address":  os.getenv("SENDER_ADDRESS",  "Musterstrasse 1"),
    "zip_city": os.getenv("SENDER_ZIP_CITY", "5630 Muri AG"),
    "phone":    os.getenv("SENDER_PHONE",    "+41 56 XXX XX XX"),
    "email":    os.getenv("SENDER_EMAIL",    "info@ihre-treuhand.ch"),
    "website":  os.getenv("SENDER_WEBSITE",  "www.ihre-treuhand.ch"),
}
