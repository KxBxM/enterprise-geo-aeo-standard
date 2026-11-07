#!/usr/bin/env python3
"""
Open-Source GEO & AEO Diagnostic Validator (v0.2.0)
Maintained by James Stone Advisory (https://jamesstone.dev)
License: MIT

A lightweight Python CLI utility for inspecting AI crawler HTTP accessibility,
/llms.txt documentation manifests, and Schema.org JSON-LD @graph entity structures.
"""

import sys
import re
import json
import argparse
import urllib.request
import urllib.error
from urllib.parse import urlparse
from html.parser import HTMLParser

VERSION = "0.2.0"

USER_AGENTS = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Applebot-Extended": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15 (Applebot/0.1; +http://www.apple.com/go/applebot)"
}

DEFAULT_BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 GEO-Validator/0.2.0"

TARGET_ROBOT_BOTS = [
    "OAI-SearchBot",
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "PerplexityBot",
    "Google-Extended",
    "Applebot-Extended"
]

SEARCH_URL_PATTERNS = [
    re.compile(r"google\.[a-z.]+/search", re.IGNORECASE),
    re.compile(r"bing\.com/search", re.IGNORECASE),
    re.compile(r"duckduckgo\.com/\?", re.IGNORECASE),
    re.compile(r"search\.yahoo\.com", re.IGNORECASE),
    re.compile(r"search\?q=", re.IGNORECASE),
]

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
                if isinstance(parsed, list):
                    self.schemas.extend(parsed)
                elif isinstance(parsed, dict):
                    self.schemas.append(parsed)
            except Exception:
                pass

def fetch_url(url, user_agent=None, timeout=8):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent or DEFAULT_BROWSER_UA}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.info())
            body = resp.read()
            return resp.status, headers, body, None
    except urllib.error.HTTPError as e:
        headers = dict(e.headers) if hasattr(e, "headers") else {}
        return e.code, headers, b"", f"HTTP {e.code}"
    except Exception as e:
        return 0, {}, b"", str(e)

def check_edge_clearance(domain):
    results = {}
    for bot_name, ua in USER_AGENTS.items():
        status, _, body, err = fetch_url(domain, user_agent=ua)
        results[bot_name] = {
            "status": status,
            "passed": status == 200,
            "bytes": len(body),
            "error": err
        }
    return results

def check_robots_txt(domain):
    url = f"{domain}/robots.txt"
    status, _, body, err = fetch_url(url)
    if status != 200:
        return {
            "status": status,
            "passed": False,
            "error": f"robots.txt returned HTTP {status}",
            "bots": {bot: False for bot in TARGET_ROBOT_BOTS}
        }

    text = body.decode("utf-8", errors="ignore")
    # Extract declared User-agents
    user_agents_declared = set()
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("user-agent:"):
            parts = line.split(":", 1)
            if len(parts) > 1:
                ua = parts[1].strip()
                if ua:
                    user_agents_declared.add(ua.lower())

    bot_coverage = {}
    all_covered = True
    for bot in TARGET_ROBOT_BOTS:
        # Covered if explicit rule exists or wildcard
        is_covered = bot.lower() in user_agents_declared
        bot_coverage[bot] = is_covered
        if not is_covered:
            all_covered = False

    return {
        "status": status,
        "passed": all_covered,
        "bots": bot_coverage,
        "user_agents_found": list(user_agents_declared)
    }

def check_machine_manifest(domain, path):
    url = f"{domain}{path}"
    status, headers, body, err = fetch_url(url)
    if status != 200:
        return {
            "path": path,
            "status": status,
            "passed": False,
            "content_type": headers.get("Content-Type", ""),
            "has_markdown_heading": False,
            "bytes": len(body),
            "error": f"HTTP {status}" if status else err
        }

    content_type = headers.get("Content-Type", "").lower()
    ct_valid = "text/plain" in content_type or "text/markdown" in content_type
    text = body.decode("utf-8", errors="ignore")
    has_heading = bool(re.search(r"^#{1,6}\s+\S+", text, re.MULTILINE))
    passed = ct_valid and has_heading and len(text.strip()) > 0

    return {
        "path": path,
        "status": status,
        "passed": passed,
        "content_type": content_type,
        "has_markdown_heading": has_heading,
        "bytes": len(body)
    }

def is_search_url(url):
    for pattern in SEARCH_URL_PATTERNS:
        if pattern.search(url):
            return True
    return False

def check_jsonld(domain):
    status, _, body, err = fetch_url(domain)
    if status != 200:
        return {
            "status": status,
            "passed": False,
            "error": f"Failed to retrieve domain HTML: HTTP {status}",
            "has_graph": False,
            "nodes": [],
            "core_types_status": {},
            "id_bindings": {},
            "same_as_audit": {}
        }

    html = body.decode("utf-8", errors="ignore")
    parser = JsonLdParser()
    parser.feed(html)

    all_nodes = []
    has_graph = False
    for schema in parser.schemas:
        if isinstance(schema, dict) and "@graph" in schema and isinstance(schema["@graph"], list):
            has_graph = True
            all_nodes.extend(schema["@graph"])
        elif isinstance(schema, dict):
            all_nodes.append(schema)

    # Core types to check:
    # 1. Organization or ProfessionalService
    # 2. Person
    # 3. WebSite
    # 4. FAQPage
    types_found = set()
    node_by_type = {}
    id_bindings = {}
    same_as_audit = {
        "valid_urls": [],
        "invalid_search_urls": []
    }

    for node in all_nodes:
        if not isinstance(node, dict):
            continue
        ntype = node.get("@type")
        if isinstance(ntype, list):
            for t in ntype:
                types_found.add(t)
                node_by_type[t] = node
        elif ntype:
            types_found.add(ntype)
            node_by_type[ntype] = node

        # Check @id bindings
        node_id = node.get("@id")
        if ntype:
            type_label = ntype if isinstance(ntype, str) else "/".join(ntype)
            id_bindings[type_label] = bool(node_id and str(node_id).strip())

        # Check sameAs
        same_as = node.get("sameAs")
        if same_as:
            urls = same_as if isinstance(same_as, list) else [same_as]
            for u in urls:
                if not isinstance(u, str):
                    continue
                if is_search_url(u):
                    same_as_audit["invalid_search_urls"].append(u)
                else:
                    same_as_audit["valid_urls"].append(u)

    core_types = {
        "Organization / ProfessionalService": bool("Organization" in types_found or "ProfessionalService" in types_found),
        "Person": bool("Person" in types_found),
        "WebSite": bool("WebSite" in types_found),
        "FAQPage": bool("FAQPage" in types_found)
    }

    all_core_present = all(core_types.values())
    no_search_urls = len(same_as_audit["invalid_search_urls"]) == 0
    passed = has_graph and all_core_present and no_search_urls

    return {
        "status": status,
        "passed": passed,
        "has_graph": has_graph,
        "nodes": list(types_found),
        "core_types_status": core_types,
        "id_bindings": id_bindings,
        "same_as_audit": same_as_audit
    }

def audit_domain(target_url, json_output=False):
    domain = target_url.rstrip("/")
    if not domain.startswith("http://") and not domain.startswith("https://"):
        domain = "https://" + domain

    edge_results = check_edge_clearance(domain)
    robots_results = check_robots_txt(domain)
    llms_results = check_machine_manifest(domain, "/llms.txt")
    llms_full_results = check_machine_manifest(domain, "/llms-full.txt")
    jsonld_results = check_jsonld(domain)

    overall_passed = (
        all(b["passed"] for b in edge_results.values()) and
        robots_results["passed"] and
        llms_results["passed"] and
        llms_full_results["passed"] and
        jsonld_results["passed"]
    )

    report = {
        "version": VERSION,
        "target": domain,
        "passed": overall_passed,
        "edge_crawler_clearance": edge_results,
        "robots_txt": robots_results,
        "manifests": {
            "/llms.txt": llms_results,
            "/llms-full.txt": llms_full_results
        },
        "schema_org_jsonld": jsonld_results
    }

    if json_output:
        print(json.dumps(report, indent=2))
        return 0 if overall_passed else 1

    print("\n=======================================================")
    print(f" GEO & AEO DIAGNOSTIC VALIDATOR v{VERSION}")
    print(f" Target: {domain}")
    print(" Architecture: Schema.org JSON-LD & /llms.txt manifests")
    print("=======================================================\n")

    # 1. Edge Clearance
    print("[1.0] Probing Edge AI Crawler Accessibility (User-Agent Probes)...")
    for bot, res in edge_results.items():
        badge = "PASS" if res["passed"] else "BLOCKED / FAILED"
        print(f"  • {bot:<18} -> HTTP {res['status']:<4} [{badge}]")

    # 2. Robots.txt
    print("\n[2.0] Inspecting robots.txt Directives...")
    if robots_results["status"] == 200:
        for bot, covered in robots_results["bots"].items():
            badge = "PASS" if covered else "MISSING RULE"
            print(f"  • {bot:<18} -> [{badge}]")
    else:
        print(f"  • robots.txt failed -> HTTP {robots_results['status']}")

    # 3. Machine Manifests
    print("\n[3.0] Verifying Machine-Readable Documentation Manifests...")
    for mf in [llms_results, llms_full_results]:
        badge = f"PASS ({mf['bytes']} bytes)" if mf["passed"] else f"FAIL (HTTP {mf['status']})"
        ct_note = f"Content-Type: {mf['content_type']}" if mf["passed"] else ""
        print(f"  • {mf['path']:<18} -> [{badge}] {ct_note}")

    # 4. JSON-LD @graph
    print("\n[4.0] Validating Schema.org JSON-LD @graph Entity Architecture...")
    if jsonld_results["has_graph"]:
        print(f"  • JSON-LD @graph      -> DETECTED [PASS]")
        print(f"  • Entities Detected   -> {', '.join(jsonld_results['nodes'])}")
        print("  • Core Entity Nodes:")
        for ctype, present in jsonld_results["core_types_status"].items():
            cbadge = "PASS" if present else "MISSING"
            print(f"    - {ctype:<35} -> [{cbadge}]")
        print("  • Entity @id Bindings:")
        for entity_type, bound in jsonld_results["id_bindings"].items():
            ibadge = "BOUND" if bound else "MISSING @ID"
            print(f"    - {entity_type:<35} -> [{ibadge}]")
        print("  • sameAs Profile Links:")
        valid_cnt = len(jsonld_results["same_as_audit"]["valid_urls"])
        invalid_cnt = len(jsonld_results["same_as_audit"]["invalid_search_urls"])
        print(f"    - Valid profiles    -> {valid_cnt}")
        if invalid_cnt > 0:
            print(f"    - Invalid search URLs (FLAGGED) -> {invalid_cnt} [{', '.join(jsonld_results['same_as_audit']['invalid_search_urls'])}]")
        else:
            print(f"    - Search URLs       -> None flagged [PASS]")
    else:
        print(f"  • JSON-LD @graph      -> MISSING / NOT DETECTED [ACTION REQUIRED]")

    print("\n-------------------------------------------------------")
    verdict = "AUDIT PASSED" if overall_passed else "REMEDIATION RECOMMENDED"
    print(f"OVERALL VERDICT: [{verdict}]")
    print("For full enterprise multi-model visibility benchmarking:")
    print("Visit: https://jamesstone.dev\n")

    return 0 if overall_passed else 1

def main():
    parser = argparse.ArgumentParser(
        description="Open-Source GEO & AEO Diagnostic Validator (v0.2.0)"
    )
    parser.add_argument("domain", help="Target domain (e.g., https://example.com)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON report")
    args = parser.parse_args()
    sys.exit(audit_domain(args.domain, json_output=args.json))

if __name__ == "__main__":
    main()
