import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ZEFIX_API_BASE = "https://www.zefix.ch/ZefixREST/api/v1"
TIMEOUT = 30
DELAY = 0.4  # seconds between requests – be respectful to the public API

_session = requests.Session()
_session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ZefixChecker/1.0 (automated daily check)",
})


def search_firms_in_canton(canton_id: str = "AG", active_only: bool = True) -> list[dict]:
    """Return all firms in the given canton, paginating through all results."""
    all_firms: list[dict] = []
    offset = 0
    batch = 500

    while True:
        payload = {
            "cantonIds": [canton_id],
            "activeOnly": active_only,
            "maxEntries": batch,
            "offset": offset,
            "searchType": "STARTS_WITH",
            "name": "",
        }
        try:
            resp = _session.post(
                f"{ZEFIX_API_BASE}/firm/search",
                json=payload,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("Zefix search error at offset %d: %s", offset, exc)
            break

        firms = data.get("list", [])
        all_firms.extend(firms)

        total = data.get("total", 0)
        offset += batch

        if not firms or offset >= total:
            break

        time.sleep(DELAY)

    return all_firms


def get_firm_details(uid: str) -> Optional[dict]:
    """Fetch full firm record (including address) for the given UID."""
    # The Zefix REST API exposes firm details via the UID endpoint.
    # Try the most common path variants.
    candidates = [
        f"{ZEFIX_API_BASE}/firm/uid/{uid}",
        f"{ZEFIX_API_BASE}/firm/{uid}",
    ]
    for url in candidates:
        try:
            resp = _session.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict):
                    return data
        except requests.RequestException as exc:
            logger.debug("GET %s failed: %s", url, exc)

    logger.warning("Could not fetch details for UID %s", uid)
    return None
