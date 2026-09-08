"""Unit tests for profile_hound.pretty_print error and breach display."""

from profile_hound import pretty_print


def test_pretty_print_shows_email_error(capsys):
    pretty_print(
        {
            "email": {
                "email": "user@example.com",
                "breaches": [],
                "error": "API error: 401",
                "source": "hibp",
            }
        }
    )
    out = capsys.readouterr().out
    assert "API error: 401" in out
    assert "No breaches found." not in out


def test_pretty_print_shows_breaches(capsys):
    pretty_print(
        {
            "email": {
                "email": "user@example.com",
                "breaches": [{"Name": "Adobe"}, {"Name": "LinkedIn"}],
                "source": "xposedornot",
            }
        }
    )
    out = capsys.readouterr().out
    assert "Breached on 2 sites" in out
    assert "Adobe" in out
    assert "LinkedIn" in out
    assert "xposedornot" in out


def test_pretty_print_clean_email(capsys):
    pretty_print(
        {
            "email": {
                "email": "clean@example.com",
                "breaches": [],
                "source": "xposedornot",
            }
        }
    )
    out = capsys.readouterr().out
    assert "No breaches found." in out
    assert "xposedornot" in out


def test_pretty_print_shows_phone_error(capsys):
    pretty_print(
        {
            "phone": {
                "phone": "+10000000000",
                "valid": False,
                "error": "API error: 401",
            }
        }
    )
    out = capsys.readouterr().out
    assert "API error: 401" in out
