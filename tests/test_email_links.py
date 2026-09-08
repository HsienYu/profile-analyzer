"""Unit tests for modules.email_links (free email-to-profile enrichment)."""

from unittest.mock import MagicMock, patch

from modules.email_links import (
    extract_local_part,
    run_email_link_enrichment,
    unwrap_ddg_href,
)


def test_extract_local_part():
    assert extract_local_part("ryanfoo23@gmail.com") == "ryanfoo23"
    assert extract_local_part("  A.B+tag@Example.COM ") == "A.B+tag"


def test_unwrap_ddg_href():
    href = (
        "//duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Fsomeone"
        "&rut=abc"
    )
    assert unwrap_ddg_href(href) == "https://github.com/someone"
    assert unwrap_ddg_href("https://example.com/x") == "https://example.com/x"


def test_gravatar_exists():
    avatar = MagicMock(status_code=200)
    with patch("modules.email_links.requests.get", return_value=avatar) as get:
        # Only gravatar path exercised by isolating other providers
        with patch("modules.email_links._search_duckduckgo", return_value=[]):
            with patch("modules.email_links._search_github", return_value=[]):
                with patch("modules.email_links._probe_username_guess", return_value={}):
                    result = run_email_link_enrichment("user@example.com")

    assert result["gravatar"]["exists"] is True
    assert "gravatar.com/avatar/" in result["gravatar"]["avatar_url"]
    assert result["local_part"] == "user"
    get.assert_called()


def test_gravatar_missing():
    avatar = MagicMock(status_code=404)
    with patch("modules.email_links.requests.get", return_value=avatar):
        with patch("modules.email_links._search_duckduckgo", return_value=[]):
            with patch("modules.email_links._search_github", return_value=[]):
                with patch("modules.email_links._probe_username_guess", return_value={}):
                    result = run_email_link_enrichment("nobody@example.com")

    assert result["gravatar"]["exists"] is False


def test_duckduckgo_links_unwrapped_and_flagged_social():
    html = """
    <html><body>
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Fryanfoo23&rut=x">GH</a>
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=y">Other</a>
    </body></html>
    """
    resp = MagicMock(status_code=200, text=html)
    with patch("modules.email_links.requests.get", return_value=resp):
        links = __import__("modules.email_links", fromlist=["_search_duckduckgo"])._search_duckduckgo(
            "ryanfoo23@gmail.com"
        )

    assert links[0]["url"] == "https://github.com/ryanfoo23"
    assert links[0]["social"] is True
    assert links[1]["url"] == "https://example.com/page"
    assert links[1]["social"] is False


def test_github_commit_search_extracts_unique_authors():
    payload = {
        "items": [
            {
                "author": {
                    "login": "ryanfoo23",
                    "html_url": "https://github.com/ryanfoo23",
                }
            },
            {
                "author": {
                    "login": "ryanfoo23",
                    "html_url": "https://github.com/ryanfoo23",
                }
            },
            {"author": None},
            {
                "author": {
                    "login": "otherdev",
                    "html_url": "https://github.com/otherdev",
                }
            },
        ]
    }
    resp = MagicMock(status_code=200)
    resp.json.return_value = payload
    with patch("modules.email_links.requests.get", return_value=resp):
        users = __import__("modules.email_links", fromlist=["_search_github"])._search_github(
            "ryanfoo23@gmail.com"
        )

    assert users == [
        {
            "login": "ryanfoo23",
            "html_url": "https://github.com/ryanfoo23",
            "via": "commit-search",
        },
        {
            "login": "otherdev",
            "html_url": "https://github.com/otherdev",
            "via": "commit-search",
        },
    ]


def test_github_rate_limit_records_error_not_crash():
    resp = MagicMock(status_code=403)
    resp.json.return_value = {"message": "API rate limit exceeded"}
    with patch("modules.email_links.requests.get", return_value=resp):
        with patch("modules.email_links._check_gravatar", return_value={"exists": False}):
            with patch("modules.email_links._search_duckduckgo", return_value=[]):
                with patch("modules.email_links._probe_username_guess", return_value={}):
                    result = run_email_link_enrichment("user@example.com")

    assert result["github"] == []
    assert any("GitHub" in e or "github" in e.lower() for e in result["errors"])


def test_username_guess_probes_platforms():
    def fake_get(url, **kwargs):
        r = MagicMock()
        if "github.com/ryanfoo23" in url:
            r.status_code = 200
        elif "reddit.com" in url:
            r.status_code = 404
        else:
            r.status_code = 404
        return r

    with patch("modules.email_links.requests.get", side_effect=fake_get):
        guess = __import__(
            "modules.email_links", fromlist=["_probe_username_guess"]
        )._probe_username_guess("ryanfoo23")

    assert guess["GitHub"]["exists"] is True
    assert guess["GitHub"]["url"] == "https://github.com/ryanfoo23"
    assert guess["Reddit"]["exists"] is False


def test_full_enrichment_aggregates_providers():
    with patch(
        "modules.email_links._check_gravatar",
        return_value={
            "exists": True,
            "avatar_url": "https://www.gravatar.com/avatar/abc",
            "profile_url": "https://gravatar.com/abc",
        },
    ):
        with patch(
            "modules.email_links._search_duckduckgo",
            return_value=[
                {"title": "GH", "url": "https://github.com/x", "social": True}
            ],
        ):
            with patch(
                "modules.email_links._search_github",
                return_value=[
                    {
                        "login": "x",
                        "html_url": "https://github.com/x",
                        "via": "commit-search",
                    }
                ],
            ):
                with patch(
                    "modules.email_links._probe_username_guess",
                    return_value={
                        "GitHub": {"url": "https://github.com/x", "exists": True}
                    },
                ):
                    result = run_email_link_enrichment("x@example.com")

    assert result["email"] == "x@example.com"
    assert result["gravatar"]["exists"] is True
    assert len(result["web_links"]) == 1
    assert result["github"][0]["login"] == "x"
    assert result["username_guess"]["GitHub"]["exists"] is True
    assert result["errors"] == []
