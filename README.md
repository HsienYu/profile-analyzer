# profile-analyzer

`profile-analyzer` is a modular Python CLI OSINT tool for authorized recon: usernames,
emails, phones, free breach checks, and profile-link enrichment.

Maintained by [HsienYu](https://github.com/HsienYu).

---

## Features

- Concurrent username probes across 40 sites (`data/sites.json`)
- Optional [social-analyzer](https://github.com/qeeqbox/social-analyzer) bridge (900+ sites; AGPL dependency, not vendored)
- Email breach checks via free [XposedOrNot](https://xposedornot.com/) (optional HIBP with `HIBP_API_KEY`)
- Email-to-profile link enrichment (Gravatar, DuckDuckGo, GitHub commit search, local-part probes)
- Phone validation via Numverify when `NUMVERIFY_API_KEY` is set
- Pretty terminal summary + JSON export under `results/`

---

## Setup (uv)

```bash
git clone https://github.com/HsienYu/profile-analyzer.git
cd profile-analyzer
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements-full.txt
# optional browsers
python -m playwright install chromium
```

---

## Usage

```bash
# Built-in username scanner
python profile_analyzer.py --username johndoe --no-google --output pretty

# Username + social-analyzer (requires social-analyzer package)
python profile_analyzer.py --username johndoe --social-analyzer --sa-top 50 --no-google

# Email breach + link enrichment
python profile_analyzer.py --email someone@example.com --output pretty

# Combined
python profile_analyzer.py --username johndoe --email someone@example.com --all --social-analyzer --no-google
```

---

## API keys (optional)

```bash
export HIBP_API_KEY="your-hibp-key"         # optional; default is XposedOrNot
export NUMVERIFY_API_KEY="your-numverify-key"
```

---

## Tests

```bash
source .venv/bin/activate
pytest -v
```

---

## License

MIT for this repository. Optional `social-analyzer` remains AGPL-3.0 (see `LICENSE` and `NOTICE`).

## Legal

Authorized use only. Do not scan people or systems without permission. Respect privacy law and site terms.
