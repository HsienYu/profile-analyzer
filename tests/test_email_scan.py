"""Unit tests for modules.email_scan (free XposedOrNot + optional HIBP)."""

from unittest.mock import MagicMock, patch

from modules.email_scan import run_email_scan


def test_xposedornot_breaches_normalized_to_name_dicts():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"breaches": [["Adobe", "LinkedIn"]]}

    with patch.dict("os.environ", {"HIBP_API_KEY": ""}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response) as get:
            result = run_email_scan("user@example.com")

    assert result["email"] == "user@example.com"
    assert result["source"] == "xposedornot"
    assert result["breaches"] == [{"Name": "Adobe"}, {"Name": "LinkedIn"}]
    assert "error" not in result
    get.assert_called_once()
    called_url = get.call_args.args[0]
    assert "api.xposedornot.com" in called_url
    assert "user@example.com" in called_url


def test_xposedornot_not_found_returns_empty_breaches():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Error": "Not found", "email": None}

    with patch.dict("os.environ", {"HIBP_API_KEY": ""}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response):
            result = run_email_scan("clean@example.com")

    assert result["breaches"] == []
    assert "error" not in result
    assert result["source"] == "xposedornot"


def test_xposedornot_http_error_sets_error():
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json.return_value = {}

    with patch.dict("os.environ", {"HIBP_API_KEY": ""}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response):
            result = run_email_scan("user@example.com")

    assert result["breaches"] == []
    assert "error" in result
    assert "503" in result["error"]


def test_network_exception_sets_error():
    with patch.dict("os.environ", {"HIBP_API_KEY": ""}, clear=False):
        with patch(
            "modules.email_scan.requests.get",
            side_effect=ConnectionError("network down"),
        ):
            result = run_email_scan("user@example.com")

    assert result["breaches"] == []
    assert "network down" in result["error"]


def test_optional_hibp_used_when_api_key_present():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"Name": "Dropbox", "Domain": "dropbox.com"}]

    with patch.dict("os.environ", {"HIBP_API_KEY": "test-key"}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response) as get:
            result = run_email_scan("user@example.com")

    assert result["source"] == "hibp"
    assert result["breaches"] == [{"Name": "Dropbox", "Domain": "dropbox.com"}]
    headers = get.call_args.kwargs.get("headers") or get.call_args[1].get("headers")
    assert headers["hibp-api-key"] == "test-key"
    assert "haveibeenpwned.com" in get.call_args.args[0]


def test_hibp_401_sets_error_not_empty_silent_success():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {}

    with patch.dict("os.environ", {"HIBP_API_KEY": "bad-key"}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response):
            result = run_email_scan("user@example.com")

    assert result["breaches"] == []
    assert "401" in result["error"]
    assert result["source"] == "hibp"


def test_hibp_404_means_no_breaches():
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.dict("os.environ", {"HIBP_API_KEY": "test-key"}, clear=False):
        with patch("modules.email_scan.requests.get", return_value=mock_response):
            result = run_email_scan("clean@example.com")

    assert result["breaches"] == []
    assert "error" not in result
