import os

ZEFIX_API_BASE = "https://www.zefix.ch/ZefixREST/api/v1"
STATE_FILE = "data/seen_companies.json"
LETTERS_DIR = "letters"

CANTON_ID = "AG"

SENDER_INFO = {
    "company":  os.getenv("SENDER_COMPANY",  "Advisia"),
    "name":     os.getenv("SENDER_NAME",     ""),
    "address":  os.getenv("SENDER_ADDRESS",  "Schlyffistäg 4"),
    "zip_city": os.getenv("SENDER_ZIP_CITY", "5630 Muri"),
    "phone":    os.getenv("SENDER_PHONE",    "+41 79 948 56 30"),
    "email":    os.getenv("SENDER_EMAIL",    "info@advisia.ch"),
    "website":  os.getenv("SENDER_WEBSITE",  "advisia.ch"),
}
