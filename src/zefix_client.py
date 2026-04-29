import time
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ZEFIX_API_BASE = "https://www.zefix.ch/ZefixREST/api/v1"
TIMEOUT = 30
DELAY = 0.4

_session = requests.Session()
_session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ZefixChecker/1.0 (automated daily check)",
})


def get_firm_details(uid: str) -> Optional[dict]:
    """Fetch full firm record (including address) for the given UID."""
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
