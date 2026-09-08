"""Tests for social-analyzer subprocess bridge."""

from unittest.mock import MagicMock, patch

from modules.social_analyzer_bridge import _extract_json_object, run_social_analyzer


def test_extract_json_object_plain():
    assert _extract_json_object('{"detected":[]}') == {"detected": []}


def test_extract_json_object_with_prefix():
    text = 'log line\n{"detected":[{"link":"https://x"}]}\n'
    assert _extract_json_object(text)["detected"][0]["link"] == "https://x"


def test_run_social_analyzer_parses_detected():
    payload = '{"detected":[{"link":"https://github.com/a","status":"good","rate":"%100.0","type":"dev"}]}'
    completed = MagicMock(stdout=payload, stderr="", returncode=0)
    with patch("modules.social_analyzer_bridge.subprocess.run", return_value=completed):
        result = run_social_analyzer("a", top=5)

    assert result["count"] == 1
    assert result["detected"][0]["link"] == "https://github.com/a"
    assert result["source"] == "social-analyzer"
    assert "error" not in result


def test_run_social_analyzer_timeout():
    with patch(
        "modules.social_analyzer_bridge.subprocess.run",
        side_effect=__import__("subprocess").TimeoutExpired(cmd="x", timeout=1),
    ):
        result = run_social_analyzer("a")
    assert "timed out" in result["error"]


def test_pretty_print_social_analyzer(capsys):
    from profile_analyzer import pretty_print

    pretty_print(
        {
            "social_analyzer": {
                "detected": [
                    {
                        "link": "https://github.com/x",
                        "status": "good",
                        "rate": "%100",
                        "type": "dev",
                    }
                ],
                "count": 1,
            }
        }
    )
    out = capsys.readouterr().out
    assert "Social Analyzer" in out
    assert "https://github.com/x" in out
