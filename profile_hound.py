#!/usr/bin/env python3
# profile_hound.py
import argparse
import json
import os

from modules.address_enrichment import run_address_enrichment
from modules.email_links import run_email_link_enrichment
from modules.email_scan import run_email_scan
from modules.phone_scan import run_phone_scan
from modules.social_analyzer_bridge import run_social_analyzer, social_analyzer_available
from modules.username_scan import run_username_scan

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)


def save_results(target, data):
    output_file = os.path.join(RESULTS_DIR, f"{target}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[+] Results saved to {output_file}")


def pretty_print(data):
    print("\n====== Profile Summary ======")
    if "username" in data:
        print("\n[+] Username Scan:")
        for site, details in data["username"].items():
            if "results" in details:
                print(f"  {site}: query={details.get('query')} links={details.get('results')}")
                continue
            exists = details.get("exists")
            if exists is True:
                status = "Found"
            elif exists is False:
                status = "Not Found"
            else:
                status = f"Unknown ({details.get('status') or details.get('error') or 'n/a'})"
            print(f"  {site}: {status} - {details.get('url')}")

    if "social_analyzer" in data:
        print("\n[+] Social Analyzer:")
        sa = data["social_analyzer"]
        if sa.get("error"):
            print(f"  Error: {sa['error']}")
        detected = sa.get("detected") or []
        print(f"  Detected profiles: {sa.get('count', len(detected))}")
        for item in detected:
            print(
                f"  - {item.get('link')} "
                f"(status={item.get('status')}, rate={item.get('rate')}, type={item.get('type')})"
            )

    if "email" in data:
        print("\n[+] Email Scan:")
        email_data = data["email"]
        if email_data.get("error"):
            print(f"  Error: {email_data['error']}")
        elif email_data.get("breaches"):
            print(f"  Breached on {len(email_data['breaches'])} sites:")
            for breach in email_data["breaches"]:
                name = breach.get("Name") if isinstance(breach, dict) else breach
                print(f"    - {name}")
        else:
            print("  No breaches found.")
        if email_data.get("source"):
            print(f"  Source: {email_data['source']}")

    if "phone" in data:
        print("\n[+] Phone Scan:")
        phone_data = data["phone"]
        if phone_data.get("error"):
            print(f"  Error: {phone_data['error']}")
        for key in ["valid", "carrier", "location", "line_type"]:
            if phone_data.get(key) is not None:
                print(f"  {key.capitalize()}: {phone_data.get(key)}")

    if "links" in data:
        print("\n[+] Link Enrichment:")
        links = data["links"]
        if links.get("local_part"):
            print(f"  Local-part guess: {links['local_part']}")
        gravatar = links.get("gravatar") or {}
        if gravatar.get("exists"):
            print(
                f"  Gravatar: Found - {gravatar.get('profile_url') or gravatar.get('avatar_url')}"
            )
        else:
            print("  Gravatar: Not Found")
        github_users = links.get("github") or []
        if github_users:
            print("  GitHub (commit email match):")
            for user in github_users:
                print(f"    - {user.get('login')}: {user.get('html_url')}")
        web_links = links.get("web_links") or []
        social = [item for item in web_links if item.get("social")]
        other = [item for item in web_links if not item.get("social")]
        if social:
            print("  Social / profile web hits:")
            for item in social:
                print(f"    - {item.get('url')}")
        if other:
            print("  Other web hits:")
            for item in other[:8]:
                print(f"    - {item.get('url')}")
        username_guess = links.get("username_guess") or {}
        if username_guess:
            print("  Username guess probes:")
            for site, details in username_guess.items():
                exists = details.get("exists")
                if exists is True:
                    status = "Found"
                elif exists is False:
                    status = "Not Found"
                else:
                    status = f"Unknown ({details.get('status') or details.get('error') or 'n/a'})"
                print(f"    - {site}: {status} - {details.get('url')}")
        for err in links.get("errors") or []:
            print(f"  Error: {err}")

    if "person" in data:
        print("\n[+] Enrichment Info:")
        for k, v in data["person"].items():
            if isinstance(v, list):
                for item in v:
                    print(f"  {k.capitalize()}: {item}")
            elif v:
                print(f"  {k.capitalize()}: {v}")
    print("=================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="profile-hound: OSINT profiler for usernames, phones, and emails"
    )
    parser.add_argument("--username", help="Username to scan")
    parser.add_argument("--email", help="Email address to scan")
    parser.add_argument("--phone", help="Phone number to scan")
    parser.add_argument(
        "--all", action="store_true", help="Run all scans if data available"
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format",
    )
    parser.add_argument(
        "--social-analyzer",
        action="store_true",
        help="Also run qeeqbox social-analyzer (optional AGPL dependency)",
    )
    parser.add_argument(
        "--sa-top",
        type=int,
        default=50,
        help="social-analyzer --top (default: 50)",
    )
    parser.add_argument(
        "--sa-timeout",
        type=int,
        default=8,
        help="social-analyzer per-request timeout seconds (default: 8)",
    )
    parser.add_argument(
        "--no-google",
        action="store_true",
        help="Skip Google fallback queries in username scan",
    )

    args = parser.parse_args()
    collected_data = {}

    if args.all or args.username:
        if args.username:
            print(f"[*] Scanning username: {args.username}")
            collected_data["username"] = run_username_scan(
                args.username, include_google=not args.no_google
            )
            if args.social_analyzer or args.all:
                if social_analyzer_available():
                    print(f"[*] Running social-analyzer for: {args.username}")
                    collected_data["social_analyzer"] = run_social_analyzer(
                        args.username,
                        top=args.sa_top,
                        timeout=args.sa_timeout,
                    )
                else:
                    collected_data["social_analyzer"] = {
                        "username": args.username,
                        "detected": [],
                        "error": "social-analyzer not installed. uv pip install social-analyzer",
                        "source": "social-analyzer",
                    }

    if args.all or args.email:
        if args.email:
            print(f"[*] Scanning email: {args.email}")
            collected_data["email"] = run_email_scan(args.email)
            print(f"[*] Enriching profile links for: {args.email}")
            collected_data["links"] = run_email_link_enrichment(args.email)

    if args.all or args.phone:
        if args.phone:
            print(f"[*] Scanning phone: {args.phone}")
            collected_data["phone"] = run_phone_scan(args.phone)

    if "email" in collected_data or "phone" in collected_data:
        print("[*] Enriching address/profile info...")
        collected_data["person"] = run_address_enrichment(
            email=args.email, phone=args.phone
        )

    if collected_data:
        target_id = args.username or args.email or args.phone or "profile"
        save_results(target_id, collected_data)
        if args.output == "pretty":
            pretty_print(collected_data)
    else:
        print("[-] No input provided. Use --username, --email, or --phone")


if __name__ == "__main__":
    main()
