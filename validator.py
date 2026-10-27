#!/usr/bin/env python3
"""
Enterprise GEO & AEO Standard Validator
Maintained by James Stone Advisory (https://jamesstone.dev)
License: MIT
"""

import sys
import json
import argparse
import urllib.request
import urllib.error
from html.parser import HTMLParser

USER_AGENTS = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Applebot-Extended": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)"
}

class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.schemas = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attr_dict = dict(attrs)
            if attr_dict.get("type") == "application/ld+json":
                self.in_script = True

    def handle_endtag(self, tag):
        if tag.lower() == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            try:
                parsed = json.loads(data.strip())
                self.schemas.append(parsed)
            except Exception:
                pass

def check_endpoint(url, user_agent=None):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent or "GEO-Standard-Validator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, len(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return 0, 0

def audit_domain(target_url):
    domain = target_url.rstrip("/")
    print(f"\n=======================================================")
    print(f" GEO & AEO DOMAIN AUDIT: {domain}")
    print(f" Standard: Enterprise AI Search Architecture (2026)")
    print(f" Specification: https://jamesstone.dev")
    print(f"=======================================================\n")

    # 1. Edge WAF Bot Clearance
    print("[1.0] Probing Edge WAF AI Crawler Clearance...")
    for bot_name, ua in USER_AGENTS.items():
        status, _ = check_endpoint(domain, ua)
        badge = "PASS" if status == 200 else "BLOCKED / CHALLENGED"
        print(f"  • {bot_name:<18} -> HTTP {status:<4} [{badge}]")

    # 2. Machine Endpoints (/llms.txt)
    print("\n[2.0] Verifying Machine-Readable Endpoints...")
    for endpoint in ["/llms.txt", "/llms-full.txt"]:
        url = domain + endpoint
        status, size = check_endpoint(url)
        badge = f"PASS ({size} bytes)" if status == 200 else "FAIL"
        print(f"  • {endpoint:<18} -> HTTP {status:<4} [{badge}]")

    # 3. 4-Node JSON-LD @graph Check
    print("\n[3.0] Scraping DOM for JSON-LD Knowledge Graph...")
    try:
        req = urllib.request.Request(domain, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        
        parser = JsonLdParser()
        parser.feed(html)
        
        has_graph = False
        nodes_found = []
        for s in parser.schemas:
            if "@graph" in s:
                has_graph = True
                nodes_found.extend([n.get("@type") for n in s["@graph"] if "@type" in n])

        if has_graph:
            print(f"  • JSON-LD @graph  -> DETECTED [PASS]")
            print(f"  • Entity Nodes    -> {', '.join(str(n) for n in nodes_found)}")
        else:
            print(f"  • JSON-LD @graph  -> MISSING / ISOLATED [ACTION REQUIRED]")
    except Exception as e:
        print(f"  • Scraping Error: {e}")

    print("\n-------------------------------------------------------")
    print("For full enterprise multi-model benchmarking & remediation:")
    print("Visit: https://jamesstone.dev\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit a domain for Enterprise GEO/AEO standards.")
    parser.add_argument("domain", help="Target domain (e.g., https://example.com)")
    args = parser.parse_args()
    target = args.domain if args.domain.startswith("http") else f"https://{args.domain}"
    audit_domain(target)