# Open-Source GEO & AEO Diagnostic Validator

Maintained by **James Stone Advisory** (https://jamesstone.dev).  
License: MIT

A lightweight Python CLI utility for inspecting AI crawler HTTP accessibility, `/llms.txt` documentation manifests, and Schema.org JSON-LD `@graph` entity structures.

> **Prefer a Zero-Install Web Diagnostic?**  
> You can run a cloud-hosted version of this diagnostic—including live Edge WAF crawler checks and multi-model recommendation share benchmarking—directly in your browser at **[https://jamesstone.dev/#benchmark](https://jamesstone.dev/#benchmark)**.

> **Note on Crawler Probes:** User-Agent HTTP probes executed by this tool test baseline server and edge response codes. Synthetic client probes do not replace ASN/IP-verified bot authentication (such as Cloudflare `cf.client.bot` or published crawler CIDR validation).

---

## Capabilities Inspected

1. **Edge Bot Clearance & Access:** Checks baseline HTTP response codes for major AI crawlers (`GPTBot`, `ClaudeBot`, `PerplexityBot`, `Applebot-Extended`).
2. **Robots.txt Directive Verification:** Inspects `robots.txt` for explicit directives covering key AI search crawlers: `OAI-SearchBot`, `GPTBot`, `ChatGPT-User`, `ClaudeBot`, `Claude-Web`, `PerplexityBot`, `Google-Extended`, and `Applebot-Extended`.
3. **Machine Manifest Endpoints (`/llms.txt` & `/llms-full.txt`):** Verifies endpoints return `HTTP 200`, appropriate content-type (`text/plain` or `text/markdown`), and a non-empty Markdown heading structure.
4. **Schema.org JSON-LD `@graph` Entity Architecture:** Detects JSON-LD `@graph` arrays, validates the presence of core entity nodes (`Organization` / `ProfessionalService`, `Person`, `WebSite`, `FAQPage`), verifies `@id` URI bindings, and checks for valid, non-search `sameAs` profile links.
5. **Machine-Readable JSON Reporting:** Pass `--json` to produce deterministic, reproducible JSON output suitable for CI/CD pipelines or audit ingestion.

---

## Installation & Usage

```bash
# Install locally in editable mode
pip install -e .

# Run standard console audit
python validator.py https://example.com

# Run machine-readable JSON output
python validator.py https://example.com --json
```

For complete enterprise multi-model visibility benchmarking and engineering remediation:  
Visit [James Stone Advisory](https://jamesstone.dev).
