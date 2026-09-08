"""Username presence scanner (clean-room site list + optional Google fallback)."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from modules.utils import search_google

USER_AGENT = "profile-analyzer/2.0 (+https://github.com/HsienYu/profile-analyzer)"
DEFAULT_SITES_PATH = Path(__file__).resolve().parent.parent / "data" / "sites.json"


def load_sites(path: str | Path | None = None) -> list[dict]:
    sites_path = Path(path) if path else DEFAULT_SITES_PATH
    with open(sites_path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("sites.json must be a list")
    return data


def _probe_site(session: requests.Session, name: str, url: str, timeout: float) -> dict:
    try:
        response = session.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        status = response.status_code
        if status == 200:
            return {"url": url, "exists": True, "status": status}
        if status == 404:
            return {"url": url, "exists": False, "status": status}
        return {"url": url, "exists": None, "status": status}
    except requests.RequestException as exc:
        return {"url": url, "exists": None, "error": str(exc)}


def run_username_scan(
    username: str,
    *,
    sites_path: str | Path | None = None,
    workers: int = 12,
    timeout: float = 8.0,
    include_google: bool = True,
) -> dict:
    username = (username or "").strip()
    results: dict = {}
    if not username:
        return results

    sites = load_sites(sites_path)
    session = requests.Session()

    def job(site: dict):
        name = site["name"]
        url = site["url"].format(username=username)
        return name, _probe_site(session, name, url, timeout)

    max_workers = max(1, min(workers, len(sites) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(job, site) for site in sites]
        for fut in as_completed(futures):
            name, detail = fut.result()
            category = next((s.get("category") for s in sites if s["name"] == name), None)
            if category:
                detail = {**detail, "category": category}
            results[name] = detail

    if include_google and os.environ.get("PROFILE_ANALYZER_SKIP_GOOGLE", os.environ.get("PROFILE_HOUND_SKIP_GOOGLE")) != "1":
        google_sites = {
            "LinkedIn": f"site:linkedin.com/in {username}",
            "Facebook": f"site:facebook.com {username}",
        }
        for site, query in google_sites.items():
            links = search_google(query)
            results[site] = {"query": query, "results": links}

    return results
