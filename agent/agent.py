# Agent for cross-border-ai-agent
# Usage: python agent/agent.py --query "wireless earbuds" --company "ACME Corp" [--hs 851712]

import argparse
import json
import os
import re
import textwrap
from datetime import datetime

try:
    import requests
except Exception:
    requests = None

# Minimal HS mapping for common categories. Extend as needed.
HS_MAP = {
    "electronics": "85",
    "earbuds": "8518",
    "wireless earbuds": "8518",
    "phone": "85",
    "apparel": "61",
    "clothing": "61",
    "shoes": "64",
    "furniture": "94",
    "toys": "95",
}


def normalize_query(q: str) -> str:
    return q.strip().lower()


def lookup_hs(query: str) -> str:
    q = normalize_query(query)
    # If the query already looks like an HS code (digits, length 2-10), return it
    m = re.match(r"^(\d{2,10})$", q)
    if m:
        return q
    # direct map
    if q in HS_MAP:
        return HS_MAP[q]
    # fuzzy match: look for keywords
    for k in HS_MAP:
        if k in q:
            return HS_MAP[k]
    return ""  # unknown


def fetch_trade_data_by_hs(hs_code: str):
    """
    Attempt to fetch US import statistics for the HS code using Census API if CENSUS_API_KEY is set.
    Falls back to None (caller must mark as 待核实).
    """
    api_key = os.getenv("CENSUS_API_KEY")
    if not api_key:
        return None
    if not requests:
        return None

    # Note: Census trade API endpoints are versioned and require careful parameters.
    # We'll attempt a basic call to the International Trade API timeseries endpoint for imports.
    # This is a best-effort helper — if it fails, we return None and mark as 待核实.
    try:
        # This endpoint and parameters may need adjustment depending on Census API version and data needed.
        # We try a generic bulk endpoint for HS 6-digit (or prefix) monthly imports (value in USD).
        base = "https://api.census.gov/data/timeseries/intltrade/imports"
        # The parameter names vary; we attempt a simple query for HS in COMM_LVL and get ALL_VAL_MO
        params = {
            "get": "ALL_VAL_MO,MONTH,YEAR,CTY_NAME",
            "time": "2023",
            "COMM_LVL": "HS",
            "COMM_CODE": hs_code,
            "key": api_key,
        }
        r = requests.get(base, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        # First row is header
        headers = data[0]
        rows = data[1:]
        # Aggregate simple stats
        total = sum([float(r[headers.index("ALL_VAL_MO")]) for r in rows if r[headers.index("ALL_VAL_MO")] not in ("", None)])
        return {
            "source": "Census API",
            "hs_code": hs_code,
            "sample_rows": rows[:5],
            "total_sample_value": total,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception:
        return None


def estimate_tariff(hs_code: str):
    """
    Best-effort tariff estimate. Requires HTS lookup which is not available by default.
    This function will attempt to use a simple heuristic: if HS starts with known prefixes, return typical MFN ranges.
    Otherwise, return None and caller should mark as 待核实.
    """
    if not hs_code:
        return None
    # Very rough heuristics (for demo only)
    if hs_code.startswith("85"):
        return {"estimate_pct": 0.0, "note": "Electronics commonly have low MFN tariffs (~0%). Verify with HTS."}
    if hs_code.startswith("61") or hs_code.startswith("62"):
        return {"estimate_pct": 12.0, "note": "Apparel typically faces significant MFN tariffs (~10-16%). Verify with HTS."}
    if hs_code.startswith("64"):
        return {"estimate_pct": 8.0, "note": "Footwear typical MFN tariff range. Verify with HTS."}
    if hs_code.startswith("94"):
        return {"estimate_pct": 3.0, "note": "Furniture often low to moderate tariffs. Verify with HTS."}
    return None


def build_customer_profile(company: str, category: str, trade_data):
    """
    Simple heuristic-based customer profile based on provided company name and trade stats.
    """
    profile = {
        "company": company,
        "category": category,
        "summary": "Generated profile based on inputs and available trade data.",
        "assumptions": [],
        "data_points": [],
    }
    if trade_data:
        profile["data_points"].append({"label": "trade_sample_total_value", "value": trade_data.get("total_sample_value"), "source": trade_data.get("source")})
    else:
        profile["assumptions"].append("Trade data unavailable — marked 待核实")

    # Example heuristics
    if "apparel" in category.lower() or category.lower().startswith("61"):
        profile["summary"] = "SMB-to-midmarket apparel brand selling to US; price-competitive market; needs localization and fast shipping."
        profile["assumptions"].append("Competitive apparel market based on macro trade flows — 待核实 with HS import volumes")
    elif "earbud" in category.lower() or category.startswith("85"):
        profile["summary"] = "Consumer electronics (audio) category — high demand but price-sensitive; returns and warranty logistics matter."
        profile["assumptions"].append("Electronics category typically low tariffs but strong logistics/service expectations — 待核实")
    else:
        profile["summary"] = "General cross-border seller profile — validate with targeted market data."

    return profile


def generate_outreach_email(profile: dict, tariff_estimate: dict):
    """
    Generate a concise US-style outreach email following first-principles rules.
    Include data source citations and mark unverified items as 待核实.
    """
    company = profile.get("company") or "[Company]"
    category = profile.get("category") or "[Category]"
    first_name = "[First Name]"

    # Build bullet points with provenance
    bullets = []
    for dp in profile.get("data_points", []):
        bullets.append(f"{dp['label']}: {dp['value']} (source: {dp['source']})")
    for a in profile.get("assumptions", []):
        bullets.append(f"Assumption: {a}")

    tariff_line = "Tariff estimate:"
    if tariff_estimate:
        tariff_line += f" ~{tariff_estimate.get('estimate_pct')}% ({tariff_estimate.get('note')})"
    else:
        tariff_line += " 待核实 (no HTS lookup available)"

    body = textwrap.dedent(f"""
    Subject: Quick question about {company}'s {category} sales in the US

    Hi {first_name},

    I noticed {company} sells {category} and wanted to share two data-backed points that commonly move the needle for similar sellers:

    - {tariff_line}
    - {profile.get('summary')}

    Quick context:
    {chr(10).join(['- '+b for b in bullets])}

    Worth 15 minutes to walk through two concrete ideas to improve US conversion and landed cost? I'm flexible this week.

    Best,
    [Your First Name]
    [Title] | [Company]
    """)

    # Enforce lean language: strip excessive blank lines
    body = '\n'.join([line.rstrip() for line in body.splitlines() if line.strip() != ''])
    return body


def main():
    parser = argparse.ArgumentParser(description="Cross-border Agent: tariff estimate, customer profile, and outreach email generator.")
    parser.add_argument("--query", "-q", required=True, help="Category name or HS code (e.g., \"wireless earbuds\" or 851821)")
    parser.add_argument("--company", "-c", default="[Company]", help="Target company name")
    parser.add_argument("--hs", help="Explicit HS code if known (overrides category lookup)")
    args = parser.parse_args()

    query = args.query
    company = args.company
    hs = args.hs or lookup_hs(query)

    print("[Agent] Input:", query, "company:", company, "hs:", hs)

    trade_data = None
    if hs:
        print(f"[Agent] Attempting to fetch trade data for HS: {hs} (requires CENSUS_API_KEY env var)")
        trade_data = fetch_trade_data_by_hs(hs)
        if trade_data is None:
            print("[Agent] Trade data fetch failed or API key missing — marking trade data as 待核实")

    tariff = estimate_tariff(hs) if hs else None
    if tariff is None:
        print("[Agent] Tariff estimate not available via heuristics — will mark as 待核实 in output")

    profile = build_customer_profile(company, query, trade_data)

    email = generate_outreach_email(profile, tariff)

    output = {
        "query": query,
        "company": company,
        "hs": hs or "unknown",
        "tariff_estimate": tariff or {"status": "待核实"},
        "trade_data": trade_data or {"status": "待核实"},
        "customer_profile": profile,
        "outreach_email": email,
        "principles": {
            "first_principles": True,
            "notes": [
                "All key conclusions must cite sources or be marked '待核实'",
                "Language kept concise; data-first heuristics used where available"
            ]
        }
    }

    print("\n===== Agent Output (JSON) =====")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("\n===== Outreach Email =====")
    print(email)


if __name__ == "__main__":
    main()
