"""Free email-to-profile link enrichment.

Sources (no paid API keys):
- Gravatar existence / avatar URL
- DuckDuckGo HTML search for the quoted email
- GitHub public commit search by author-email
- Username guess from the email local-part on a small platform set
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "profile-hound/2.0 (+https://github.com/HsienYu/profile-hound)"
SOCIAL_HOST_FRAGMENTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "tiktok.com",
    "youtube.com",
    "medium.com",
    "gravatar.com",
    "keybase.io",
    "about.me",
    "linktr.ee",
)

USERNAME_PLATFORMS = {
    "GitHub": "https://github.com/{username}",
    "GitLab": "https://gitlab.com/{username}",
    "Reddit": "https://www.reddit.com/user/{username}",
    "Twitter": "https://twitter.com/{username}",
    "Instagram": "https://www.instagram.com/{username}/",
    "TikTok": "https://www.tiktok.com/@{username}",
}


def extract_local_part(email: str) -> str:
    cleaned = (email or "").strip()
    if "@" not in cleaned:
        return cleaned
    return cleaned.split("@", 1)[0]


def unwrap_ddg_href(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return unquote(qs["uddg"][0])
    return href


def _is_social_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(frag in host for frag in SOCIAL_HOST_FRAGMENTS)


def _email_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def _check_gravatar(email: str) -> dict:
    digest = _email_hash(email)
    avatar_url = f"https://www.gravatar.com/avatar/{digest}?d=404"
    profile_url = f"https://gravatar.com/{digest}"
    try:
        response = requests.get(
            avatar_url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            allow_redirects=True,
        )
        exists = response.status_code == 200
    except Exception:
        exists = False
    return {
        "exists": exists,
        "avatar_url": avatar_url,
        "profile_url": profile_url if exists else None,
        "hash": digest,
    }


def _search_duckduckgo(email: str, max_links: int = 10) -> list:
    query = f'"{email}"'
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(f"DuckDuckGo HTTP {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    seen = set()
    for a_tag in soup.select("a.result__a"):
        href = unwrap_ddg_href(a_tag.get("href") or "")
        if not href or not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(
            {
                "title": (a_tag.get_text(strip=True) or "")[:200],
                "url": href,
                "social": _is_social_url(href),
            }
        )
        if len(links) >= max_links:
            break
    return links


def _search_github(email: str, max_users: int = 5) -> list:
    """Find GitHub users via public commit author-email search."""
    url = (
        "https://api.github.com/search/commits"
        f"?q=author-email:{quote(email)}&per_page=20"
    )
    response = requests.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
        timeout=15,
    )
    if response.status_code != 200:
        message = ""
        try:
            message = response.json().get("message", "")
        except Exception:
            message = response.text[:200]
        raise RuntimeError(
            f"GitHub API error: {response.status_code}"
            + (f" ({message})" if message else "")
        )

    items = response.json().get("items") or []
    users = []
    seen = set()
    for item in items:
        author = item.get("author") or {}
        login = author.get("login")
        html_url = author.get("html_url")
        if not login or login in seen:
            continue
        seen.add(login)
        users.append(
            {
                "login": login,
                "html_url": html_url or f"https://github.com/{login}",
                "via": "commit-search",
            }
        )
        if len(users) >= max_users:
            break
    return users


def _probe_username_guess(username: str) -> dict:
    """Lightweight existence probe for email local-part as a handle."""
    if not username or not re.match(r"^[A-Za-z0-9._-]{2,39}$", username):
        return {}

    results = {}
    for site, template in USERNAME_PLATFORMS.items():
        url = template.format(username=username)
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=8,
                allow_redirects=True,
            )
            if response.status_code == 200:
                results[site] = {"url": url, "exists": True}
            elif response.status_code == 404:
                results[site] = {"url": url, "exists": False}
            else:
                results[site] = {
                    "url": url,
                    "exists": None,
                    "status": response.status_code,
                }
        except Exception as exc:
            results[site] = {"url": url, "exists": None, "error": str(exc)}
    return results


def run_email_link_enrichment(email: str) -> dict:
    """Aggregate free link sources for an email address."""
    email = (email or "").strip()
    result = {
        "email": email,
        "local_part": extract_local_part(email),
        "gravatar": {"exists": False},
        "github": [],
        "web_links": [],
        "username_guess": {},
        "errors": [],
    }
    if not email or "@" not in email:
        result["errors"].append("Invalid email address")
        return result

    try:
        result["gravatar"] = _check_gravatar(email)
    except Exception as exc:
        result["errors"].append(f"Gravatar: {exc}")

    try:
        result["web_links"] = _search_duckduckgo(email)
    except Exception as exc:
        result["errors"].append(f"DuckDuckGo: {exc}")

    try:
        result["github"] = _search_github(email)
    except Exception as exc:
        result["errors"].append(f"GitHub: {exc}")

    try:
        result["username_guess"] = _probe_username_guess(result["local_part"])
    except Exception as exc:
        result["errors"].append(f"Username guess: {exc}")

    return result
