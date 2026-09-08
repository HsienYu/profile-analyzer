"""Tests for expanded username scanner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.username_scan import load_sites, run_username_scan


def test_load_sites_default():
    sites = load_sites()
    assert len(sites) >= 10
    assert any(s["name"] == "GitHub" for s in sites)


def test_run_username_scan_parallel_probes(tmp_path):
    sites = [
        {"name": "GitHub", "url": "https://github.com/{username}", "category": "dev"},
        {"name": "Reddit", "url": "https://www.reddit.com/user/{username}", "category": "social"},
    ]
    path = tmp_path / "sites.json"
    path.write_text(__import__("json").dumps(sites), encoding="utf-8")

    def fake_get(url, **kwargs):
        r = MagicMock()
        r.status_code = 200 if "github.com" in url else 404
        return r

    with patch("modules.username_scan.requests.Session") as sess_cls:
        session = MagicMock()
        session.get.side_effect = fake_get
        sess_cls.return_value = session
        result = run_username_scan(
            "alice", sites_path=path, include_google=False, workers=2
        )

    assert result["GitHub"]["exists"] is True
    assert result["Reddit"]["exists"] is False
