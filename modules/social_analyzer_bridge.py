"""Optional bridge to qeeqbox social-analyzer (AGPL-3.0, separate package).

Invokes `python -m social-analyzer` as a subprocess so this repo does not
vendor AGPL source. Install with: pip/uv install social-analyzer
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any


def social_analyzer_available() -> bool:
    try:
        import social_analyzer  # noqa: F401

        return True
    except Exception:
        return shutil.which("social-analyzer") is not None


def run_social_analyzer(
    username: str,
    *,
    top: int = 50,
    mode: str = "fast",
    timeout: int = 10,
    filter_status: str = "good",
    python_exe: str | None = None,
) -> dict[str, Any]:
    """Run social-analyzer and return a normalized result dict."""
    if not username or not username.strip():
        return {"username": username, "detected": [], "error": "username required"}

    exe = python_exe or sys.executable
    cmd = [
        exe,
        "-m",
        "social-analyzer",
        "--username",
        username.strip(),
        "--output",
        "json",
        "--mode",
        mode,
        "--top",
        str(top),
        "--filter",
        filter_status,
        "--timeout",
        str(timeout),
        "--method",
        "find",
        "--profiles",
        "detected",
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(60, timeout * max(top // 5, 5)),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "username": username,
            "detected": [],
            "error": "social-analyzer timed out",
            "source": "social-analyzer",
        }
    except FileNotFoundError:
        return {
            "username": username,
            "detected": [],
            "error": "Python executable not found for social-analyzer",
            "source": "social-analyzer",
        }

    stdout = (completed.stdout or "").strip()
    if not stdout:
        err = (completed.stderr or "").strip() or f"exit {completed.returncode}"
        return {
            "username": username,
            "detected": [],
            "error": f"social-analyzer produced no JSON: {err[:300]}",
            "source": "social-analyzer",
        }

    # SA sometimes prints logs before JSON; find the outermost object.
    payload = _extract_json_object(stdout)
    if payload is None:
        return {
            "username": username,
            "detected": [],
            "error": "failed to parse social-analyzer JSON",
            "raw_preview": stdout[:500],
            "source": "social-analyzer",
        }

    detected_raw = payload.get("detected") or payload.get("profiles") or []
    if isinstance(payload, list):
        detected_raw = payload

    detected = []
    for item in detected_raw:
        if not isinstance(item, dict):
            continue
        detected.append(
            {
                "link": item.get("link"),
                "status": item.get("status"),
                "rate": item.get("rate"),
                "title": item.get("title"),
                "type": item.get("type"),
                "country": item.get("country"),
                "language": item.get("language"),
            }
        )

    return {
        "username": username,
        "detected": detected,
        "count": len(detected),
        "source": "social-analyzer",
        "returncode": completed.returncode,
    }


def _extract_json_object(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
