#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
excel-to-json.py

Converts an Excel cookie list into `converted_cookie_data.json` ready for translation.

Usage:
    python excel-to-json.py
    python excel-to-json.py --input "cookies.xlsx" --output converted_cookie_data.json

Defaults:
- If --input is not provided, the script will pick the first .xlsx in the current directory.
- If --output is not provided, writes to converted_cookie_data.json.

Expected/typical columns (adjust detection below if yours differ):
- Category (e.g., "Strictly necessary", "Performance", "Functional", "Marketing", "Social media")
- Cookie subgroup
- Cookies
- Cookies used (e.g., "First party", "Third party")
- Lifespan (e.g., "395 Days", "Less than one day", "Session", "2 Years")
"""

import argparse
import os
import sys
import json
import re
from typing import Optional

import pandas as pd

# Map human-readable category to placeholder keys used by the translator
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


def find_first_excel() -> Optional[str]:
    """Return the first .xlsx filename in the current directory, if any."""
    for name in sorted(os.listdir(".")):
        if name.lower().endswith(".xlsx"):
            return name
    return None


def normalize(s) -> str:
    """Coerce to string and strip whitespace; return empty string for None/NaN."""
    if s is None:
        return ""
    # pd.isna handles NaN/NaT
    try:
        if isinstance(s, float) and pd.isna(s):
            return ""
    except Exception:
        pass
    return str(s).strip()


def cookies_used_placeholder(text: str) -> str:
    """
    Map "First party"/"Third party" to placeholders the translator knows.
    Defaults to First party if ambiguous.
    """
    t = normalize(text).lower()
    if "third" in t:
        return "CookiePolicyTableThirdpParty"
    return "CookiePolicyTableFirstParty"


def parse_lifespan_placeholder(text: str) -> str:
    """
    Turn human text like:
      - "395 Days" -> "395 CookiePolicyTableDays"
      - "2 Years"  -> "2 CookiePolicyTableYears"
      - "Session"  -> " CookiePolicyTableSession"
      - "Less than one day" -> " CookiePolicyTableFirstPartyLessThanOneDy"

    Robust to leading/trailing spaces, numeric-only cells, and NaN.
    """
    # Handle None/NaN up front
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""

    # Always coerce to string and strip whitespace
    raw = str(text).strip()
    t = raw.lower()

    # session
    if t == "session":
        return " CookiePolicyTableSession"

    # less than one day (allow variations)
    if "less" in t and "one" in t and "day" in t:
        return " CookiePolicyTableFirstPartyLessThanOneDy"

    # number + unit (day[s]/year[s])
    m = re.match(r"^(\d+)\s*(day|days|year|years)$", t)
    if m:
        num = m.group(1)
        unit = m.group(2)
        if unit.startswith("day"):
            return f"{num} CookiePolicyTableDays"
        else:
            return f"{num} CookiePolicyTableYears"

    # plain number only -> assume days
    m2 = re.match(r"^(\d+)$", t)
    if m2:
        return f"{m2.group(1)} CookiePolicyTableDays"

    # Fallback: return stripped original (translator may still replace any tokens it recognizes)
    return raw


def category_placeholders(text: str) -> dict:
    """
    Find best category placeholder mapping based on Category cell.
    Falls back to "Strictly necessary" if unknown/missing.
    """
    t = normalize(text).lower()
    for k, v in CATEGORY_TO_PLACEHOLDERS.items():
        if t == k or t.startswith(k):
            return v
    return CATEGORY_TO_PLACEHOLDERS["strictly necessary"]


def transform_excel_to_json(xlsx_path: str) -> dict:
    """
    Read the first sheet and build the JSON that the translator expects.
    Adjust the column inference if your headers differ.
    """
    df = pd.read_excel(xlsx_path, sheet_name=0)

    # Try to infer common column names (case-insensitive)
    cols = {c.lower(): c for c in df.columns}
    get = lambda key: cols.get(key.lower())

    col_category = get("Category") or get("cookie category") or get("category")
    col_subgroup = get("Cookie subgroup") or get("subgroup") or get("cookie_subgroup")
    col_cookies  = get("Cookies") or get("cookie") or get("cookie name")
    col_used     = get("Cookies used") or get("used") or get("party")   # first/third party
    col_lifespan = get("Lifespan") or get("duration") or get("expires")

    # Basic validation
    required_map = {
        "Cookie subgroup": col_subgroup,
        "Cookies": col_cookies,
        "Cookies used": col_used,
        "Lifespan": col_lifespan,
    }
    missing = [name for name, col in required_map.items() if not col]
    if missing:
        print(f"ERROR: Missing expected columns in Excel: {', '.join(missing)}", file=sys.stderr)
        print(f"Found columns: {list(df.columns)}", file=sys.stderr)
        sys.exit(2)

    # If no category column, assign a default for the whole sheet
    if not col_category:
        df["_Category_"] = "Strictly necessary"
        col_category = "_Category_"

    output = {"notice_table": []}

    # Group rows by category to attach name/description placeholders per block
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
            life = parse_lifespan_placeholder(row.get(col_lifespan, ""))  # ← trimmed & robust

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
    parser.add_argument("--input", help="Path to source .xlsx (default: first .xlsx in current directory)")
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
