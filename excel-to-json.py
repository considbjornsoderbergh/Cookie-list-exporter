#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
excel-to-json.py

Converts an Excel cookie list into a structured JSON file.

Usage:
    python excel-to-json.py
    python excel-to-json.py --input "cookies.xlsx" --output converted_cookie_data.json

Defaults:
- If --input is not provided, the script will pick the first .xlsx in the current directory.
- If --output is not provided, writes to converted_cookie_data.json.
"""

import argparse
import os
import sys
import json
import pandas as pd


def find_first_excel() -> str | None:
    """Find the first .xlsx file in the current directory."""
    for name in sorted(os.listdir(".")):
        if name.lower().endswith(".xlsx"):
            return name
    return None


def transform_excel_to_json(xlsx_path: str) -> dict:
    """
    Transform the Excel file into the JSON structure expected
    by json_translator_rewrite.py.

    ⚠️ TODO: Adapt this function to your real Excel structure.
    Below is a stub that just reads the first sheet and
    builds a placeholder notice_table.
    """
    df = pd.read_excel(xlsx_path, sheet_name=0)

    # Example stub: return JSON with placeholder
    data = {
        "notice_table": []
    }

    # Example: loop through rows and append minimal info
    for _, row in df.iterrows():
        data["notice_table"].append({
            "cookie_category": "StrictlynecessaryCategoryName",  # placeholder key
            "category_description": "StrictlynecessaryCategoryDescription",  # placeholder key
            "cookie_list": [
                {
                    "Cookie subgroup": str(row.get("Cookie subgroup", "")),
                    "Cookies": str(row.get("Cookies", "")),
                    "Cookies used": "CookiePolicyTableFirstParty",  # placeholder
                    "Lifespan": "365 CookiePolicyTableDays"  # placeholder
                }
            ]
        })

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to source .xlsx (default: first .xlsx in repo)")
    parser.add_argument("--output", default="converted_cookie_data.json",
                        help="Output JSON filename (default: converted_cookie_data.json)")
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
