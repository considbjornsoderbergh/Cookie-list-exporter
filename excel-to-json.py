#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
excel-to-json.py

Reads the first .xlsx (or --input) and produces converted_cookie_data.json (or --output).
Builds correct placeholder strings so the translator can localize them later.

Expected/typical columns (adjust if yours differ):
- Category (e.g., "Strictly necessary", "Performance", "Functional", "Marketing", "Social media")
- Cookie subgroup
- Cookies
- Cookies used (e.g., "First party", "Third party")
- Lifespan (e.g., "395 Days", "Less than one day", "Session", "2 Years")

If your sheet stores number + unit in separate columns, update `parse_lifespan_placeholder`.
"""

import argparse
import os
import sys
import json
import re
import pandas as pd

CATEGORY_TO_PLACEHOLDERS = {
    "strictly necessary": {
        "name": "StrictlynecessaryCategoryName",
        "desc": "Strictlynecessarycategorydescription",
    },
    "performance": {
        "name": "PerformancecookiesCategoryName",
        "desc": "Performancecookiescategorydescription",
    },
    "functional": {
        "name": "FunctionalcookiesCategoryName",
        "desc": "Functionalcookiescategorydescription",
    },
    "marketing": {
        "name": "MarketingcookiesCategoryName",
        "desc": "Marketingcookiescategorydescription",
    },
    "social media": {
        "name": "SocialmediacookiesCategoryName",
        "desc": "Socialmediacookiescategorydescription",
    },
}

def find_first_excel():
    for name in sorted(os.listdir(".")):
        if name.lower().endswith(".xlsx"):
            return name
    return None

def normalize(s):
    return (str(s) if s is not None else "").strip()

def parse_lifespan_placeholder(text: str) -> str:
    """
    Turn human text like:
      - "395 Days" -> "395 CookiePolicyTableDays"
      - "2 Years"  -> "2 CookiePolicyTableYears"
      - "Session"  -> " CookiePolicyTableSession"
      - "Less than one day" -> " CookiePolicyTableFirstPartyLessThanOneDy"
        (Yes, the key includes FirstParty in your data keys; keep as-is to match translation keys.)
    Adjust mapping if your translation keys differ.
    """
    t = normalize(text).lower()

    # session
    if t == "session":
        return " CookiePolicyTableSession"

    # less than one day (various spellings)
    if "less" in t and "one" in t and "day" in t:
        return " CookiePolicyTableFirstPartyLessThanOneDy"

    # number + unit
    m = re.match(r"^\s*(\d+)\s*(day|days|year|years)\s*$", t)
    if m:
        num = m.group(1)
        unit = m.group(2)
        if unit.startswith("day"):
            return f"{num} CookiePolicyTableDays"
        else:
            return f"{num} CookiePolicyTableYears"

    # Fallback: if it's a plain number, assume days
    m2 = re.match(r"^\s*(\d+)\s*$", t)
    if m2:
        return f"{m2.group(1)} CookiePolicyTableDays"

    # If we can't parse, leave as-is (translator will replace any tokens it recognizes)
    return text

def cookies_used_placeholder(text: str) -> str:
    """
    Map to placeholders:
      - First party  -> CookiePolicyTableFirstParty
      - Third party  -> CookiePolicyTableThirdpParty
    """
    t = normalize(text).lower()
    if "third" in t:
        return "CookiePolicyTableThirdpParty"  # matches translation keys you have
    return "CookiePolicyTableFirstParty"

def category_placeholders(text: str) -> dict:
    t = normalize(text).lower()
    # find best match by startswith or exact
    for k, v in CATEGORY_TO_PLACEHOLDERS.items():
        if t == k or t.startswith(k):
            return v
    # default to strictly necessary if unknown
    return CATEGORY_TO_PLACEHOLDERS["strictly necessary"]

def transform_excel_to_json(xlsx_path: str) -> dict:
    df = pd.read_excel(xlsx_path, sheet_name=0)

    # Try to infer columns (rename to expected names silently if close)
    cols = {c.lower(): c for c in df.columns}
    get = lambda key: cols.get(key.lower())

    col_category = get("Category") or get("cookie category") or get("category")
    col_subgroup = get("Cookie subgroup") or get("subgroup") or get("cookie_subgroup")
    col_cookies  = get("Cookies") or get("cookie") or get("cookie name")
    col_used     = get("Cookies used") or get("used") or get("party")  # first/third party source
    col_lifespan = get("Lifespan") or get("duration") or get("expires")

    if not all([col_subgroup, col_cookies, col_used, col_lifespan]):
        missing = [n for n,(v) in {
            "Cookie subgroup":col_subgroup, "Cookies":col_cookies, "Cookies used":col_used, "Lifespan":col_lifespan
        }.items() if not v]
        print(f"ERROR: Missing expected columns in Excel: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    # Group rows by Category so we can attach name/description placeholders once per group
    if not col_category:
        # If no category column, default whole sheet to "Strictly necessary"
        df["_Category_"] = "Strictly necessary"
        col_category = "_Category_"

    output = {"notice_table": []}
    for cat_value, group in df.groupby(col_category):
        cat_ph = category_placeholders(cat_value)
        block = {
            "cookie_category": cat_ph["name"],
            "category_description": cat_ph["desc"],
            "cookie_list": []
        }

        for _, row in group.iterrows():
            subgroup = normalize(row.get(col_subgroup, ""))
            cookie = normalize(row.get(col_cookies, ""))
            used = cookies_used_placeholder(row.get(col_used, "First party"))
            life = parse_lifespan_placeholder(row.get(col_lifespan, ""))

            block["cookie_list"].append({
                "Cookie subgroup": subgroup,
                "Cookies": cookie,
                "Cookies used": used,
                "Lifespan": life
            })

        output["notice_table"].append(block)

    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to source .xlsx (default: first .xlsx in repo)")
    parser.add_argument("--output", default="converted_cookie_data.json", help="Output JSON filename")
    args = parser.parse_args()

    xlsx = args.input or find_first_excel()
    if not xlsx or not os.path.exists(xlsx):
        print("ERROR: Excel file not found. Use --input or place an .xlsx in the repo root.", file=sys.stderr)
        sys.exit(2)

    print(f"Reading Excel file: {xlsx}")
    data = transform_excel_to_json(xlsx)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output}")

if __name__ == "__main__":
    main()
