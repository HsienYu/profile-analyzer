"""Pretty-print coverage for email link enrichment."""

from profile_analyzer import pretty_print


def test_pretty_print_links_section(capsys):
    pretty_print(
        {
            "links": {
                "email": "user@example.com",
                "local_part": "user",
                "gravatar": {
                    "exists": True,
                    "avatar_url": "https://www.gravatar.com/avatar/abc",
                    "profile_url": "https://gravatar.com/abc",
                },
                "github": [
                    {
                        "login": "user",
                        "html_url": "https://github.com/user",
                        "via": "commit-search",
                    }
                ],
                "web_links": [
                    {
                        "title": "Profile",
                        "url": "https://linkedin.com/in/user",
                        "social": True,
                    }
                ],
                "username_guess": {
                    "GitHub": {"url": "https://github.com/user", "exists": True},
                    "Reddit": {"url": "https://www.reddit.com/user/user", "exists": False},
                },
                "errors": [],
            }
        }
    )
    out = capsys.readouterr().out
    assert "Link Enrichment" in out
    assert "gravatar.com" in out
    assert "https://github.com/user" in out
    assert "linkedin.com/in/user" in out
    assert "GitHub: Found" in out or "GitHub: found" in out.lower()


def test_pretty_print_links_errors(capsys):
    pretty_print(
        {
            "links": {
                "email": "user@example.com",
                "local_part": "user",
                "gravatar": {"exists": False},
                "github": [],
                "web_links": [],
                "username_guess": {},
                "errors": ["GitHub: API error: 403"],
            }
        }
    )
    out = capsys.readouterr().out
    assert "GitHub: API error: 403" in out
