import os
from urllib.parse import quote

import requests

XPOSEDORNOT_URL = "https://api.xposedornot.com/v1/check-email/{email}"
HIBP_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"
USER_AGENT = "profile-hound"


def run_email_scan(email):
    """Check email against breach databases.

    Default: free XposedOrNot API (no key).
    Optional: set HIBP_API_KEY to use Have I Been Pwned instead.
    """
    api_key = os.environ.get("HIBP_API_KEY", "").strip()
    if api_key and api_key != "YOUR_HIBP_API_KEY":
        return _scan_hibp(email, api_key)
    return _scan_xposedornot(email)


def _scan_xposedornot(email):
    result = {
        "email": email,
        "breaches": [],
        "source": "xposedornot",
    }
    try:
        response = requests.get(
            XPOSEDORNOT_URL.format(email=quote(email, safe="@.")),
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
        if response.status_code != 200:
            result["error"] = f"API error: {response.status_code}"
            return result

        data = response.json()
        if isinstance(data, dict) and data.get("Error"):
            result["breaches"] = []
            return result

        names = _extract_xposedornot_names(data)
        result["breaches"] = [{"Name": name} for name in names]
    except Exception as e:
        result["error"] = str(e)
    return result


def _extract_xposedornot_names(data):
    """Normalize XposedOrNot payload to a flat list of breach names."""
    breaches = data.get("breaches") if isinstance(data, dict) else None
    if not breaches:
        return []
    # Typical shape: {"breaches": [["Adobe", "LinkedIn", ...]]}
    if isinstance(breaches, list) and breaches and isinstance(breaches[0], list):
        return [str(name) for name in breaches[0] if name]
    if isinstance(breaches, list):
        names = []
        for item in breaches:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and item.get("Name"):
                names.append(str(item["Name"]))
        return names
    return []


def _scan_hibp(email, api_key):
    result = {
        "email": email,
        "breaches": [],
        "source": "hibp",
    }
    headers = {
        "hibp-api-key": api_key,
        "User-Agent": USER_AGENT,
    }
    try:
        response = requests.get(
            HIBP_URL.format(email=quote(email, safe="@.")),
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            payload = response.json()
            result["breaches"] = payload if isinstance(payload, list) else []
        elif response.status_code == 404:
            result["breaches"] = []
        else:
            result["error"] = f"API error: {response.status_code}"
    except Exception as e:
        result["error"] = str(e)
    return result
