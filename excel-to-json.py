#!/usr/bin/env python3
"""
excel-to-json.py
- Reads an Excel export of cookies
- Produces a table with ONE ROW PER COOKIE SUBGROUP
- Writes:
    * cookie_subgroups_table.csv
    * cookie_subgroups_table.json
    * converted_cookie_data.json   <-- CI artifact expected
    * converted_cookie_data_ordered.json (kept for backward compatibility)

Usage:
  python excel-to-json.py [path_to_excel] [optional_sheet_name]

Notes:
- The script tries to auto-detect columns even if headers vary slightly
  (e.g., "Cookie subgroup" vs "Cookie Sub-group").
- If a subgroup mixes "Cookies used" values, we output "Mixed: First party, Third party".
"""

import sys
import json
from pathlib import Path

import pandas as pd

# ---------- Config ----------
# Toggle to deduplicate cookie names per subgroup while preserving first-seen order
DEDUP_COOKIES_PER_SUBGROUP = False

# Fallback input file if none provided
DEFAULT_EXCEL = "cookies.xlsx"

# ---------- Helpers ----------

def find_col(df, candidates):
    """
    Find a column in df whose name matches any of the 'candidates' (case-insensitive).
    Returns the actual column name or raises KeyError if not found.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    # Fuzzy: try contains search
    for c in df.columns:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    raise KeyError(f"Could not find any of columns: {candidates}. Found: {list(df.columns)}")

def stable_dedupe(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def load_excel(path, sheet_name=None):
    try:
        return pd.read_excel(path, engine="openpyxl", sheet_name=sheet_name)
    except TypeError:
        # Older pandas may not support engine arg; try default
        return pd.read_excel(path, sheet_name=sheet_name)

# ---------- Main ----------

def main():
    # Parse CLI args
    excel_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else Path(DEFAULT_EXCEL)
    sheet_name = sys.argv[2] if len(sys.argv) >= 3 else None

    if not excel_path.exists():
        raise FileNotFoundError(f"Input Excel not found: {excel_path.resolve()}")

    df = load_excel(excel_path, sheet_name=sheet_name)

    # Normalize column names by detecting likely headers
    subgroup_col = find_col(df, [
        "Cookie subgroup", "Cookie sub group", "Subgroup", "Domain", "Cookie domain"
    ])
    used_col = find_col(df, [
        "Cookies used", "First or Third Party", "Party", "Cookie party"
    ])
    cookie_name_col = find_col(df, [
        "Cookies", "Cookie", "Cookie name", "Name"
    ])
    lifespan_col = find_col(df, [
        "Lifespan", "Duration", "Expiry", "Expiration", "Cookie duration"
    ])

    # Work with a trimmed copy
    df_small = df[[subgroup_col, used_col, cookie_name_col, lifespan_col]].copy()

    # Clean up whitespace and drop rows that don't have a cookie name
    for c in [subgroup_col, used_col, cookie_name_col, lifespan_col]:
        df_small[c] = df_small[c].astype(str).str.strip()
    df_small = df_small[df_small[cookie_name_col].ne("").fillna(False)]
    df_small = df_small.reset_index(drop=True)

    # Preserve original ordering within groups
    df_small["_row_order"] = range(len(df_small))

    # Build one row per subgroup
    rows = []
    for subgroup, g in df_small.groupby(subgroup_col, dropna=True):
        g_sorted = g.sort_values("_row_order", kind="stable")

        cookies_list = g_sorted[cookie_name_col].tolist()
        lifespan_list = g_sorted[lifespan_col].tolist()

        if DEDUP_COOKIES_PER_SUBGROUP:
            # dedupe cookies and align lifespan by first occurrence of each cookie
            first_seen = {}
            for ck, life in zip(cookies_list, lifespan_list):
                if ck not in first_seen:
                    first_seen[ck] = life
            cookies_list = list(first_seen.keys())
            lifespan_list = [first_seen[ck] for ck in cookies_list]

        # Cookies used may vary inside a subgroup
        used_uniques = [u for u in g_sorted[used_col].unique().tolist() if u]
        if len(used_uniques) == 1:
            cookies_used_out = used_uniques[0]
        elif len(used_uniques) == 0:
            cookies_used_out = ""
        else:
            # preserve stable order of first-seen values
            cookies_used_out = "Mixed: " + ", ".join(stable_dedupe(used_uniques))

        rows.append({
            "Cookie subgroup": subgroup,
            "Cookies": ", ".join(cookies_list),
            "Cookies used": cookies_used_out,
            "Lifespan": ", ".join(lifespan_list),
        })

    result_df = pd.DataFrame(rows).sort_values("Cookie subgroup", kind="stable").reset_index(drop=True)

    # ---------- Outputs ----------
    # Ensure output directory is current working directory (CI-friendly)
    out_csv = Path("cookie_subgroups_table.csv")
    out_json = Path("cookie_subgroups_table.json")
    out_conv = Path("converted_cookie_data.json")               # CI expected
    out_conv_ordered = Path("converted_cookie_data_ordered.json")  # legacy/compat

    # CSV
    result_df.to_csv(out_csv, index=False, encoding="utf-8")

    # Flat JSON array of records
    payload = result_df.to_dict(orient="records")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Write CI-expected artifact
    with open(out_conv, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Optional: also write the ordered variant for backward compatibility
    with open(out_conv_ordered, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Log paths for CI logs
    print(f"Wrote: {out_csv.resolve()}")
    print(f"Wrote: {out_json.resolve()}")
    print(f"Wrote: {out_conv.resolve()}")
    print(f"Wrote: {out_conv_ordered.resolve()}")

if __name__ == "__main__":
    main()
