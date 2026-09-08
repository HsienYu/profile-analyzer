# Tests

## How to run

```bash
source .venv/bin/activate
pytest -v
```

## Structure

- `test_email_scan.py` -- email breach lookup (XposedOrNot free API; optional HIBP)
- `test_email_links.py` -- free email-to-profile link enrichment (Gravatar, DDG, GitHub, username guess)
- `test_pretty_print.py` -- CLI pretty output, including error surfacing
- `test_pretty_print_links.py` -- pretty output for link enrichment

## Coverage expectations

- Happy path, not-found, HTTP/API errors, and network exceptions for email scan
- Pretty printer shows breaches, clean results, and errors (never hides `error` behind "No breaches found")

## Mocks

External HTTP is mocked via `unittest.mock`. No live API calls in CI/unit tests.
