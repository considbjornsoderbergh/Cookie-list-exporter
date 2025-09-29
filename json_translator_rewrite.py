#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate converted_cookie_data.json into fully localized JSONs using translation_key.json.
Outputs:
  - Pretty JSONs in: out/ (or fallback out_build-<timestamp>/ if a FILE named 'out' exists)
  - Minified JSONs in: minified/ (or fallback minified_build-<timestamp>/ if a FILE named 'minified' exists)

Features:
- Replaces placeholder tokens with localized strings per locale.
- Handles mixed strings like "395 CookiePolicyTableDays".
- Optional localization of column headers (use --translate_keys).
- Defaults to using files from the same folder as this script.
- Robust dir creation with smart fallbacks and optional --force.
"""

import argparse
import json
import os
import re
import shutil
import time
from copy import deepcopy
from typing import Any, Dict

# Mapping for optional field/column name translations
FIELD_KEY_TO_TRANSLATION_KEY = {
    "Cookie subgroup": "CookiePolicyTableCookeiSubgroup",
    "Cookies": "CookiePolicyTableCookies",
    "Cookies used": "CookiePolicyTableCookiesUsed",
    "Lifespan": "CookiePolicyTableLifespan",
}

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def replace_placeholders_in_string(s: str, translations_for_locale: Dict[str, str]) -> str:
    if not isinstance(s, str):
        return s
    # Entire string is a placeholder key
    if s in translations_for_locale:
        return translations_for_locale[s]
    # Replace inline tokens like "... CookiePolicyTableDays"
    token_re = re.compile(r"[A-Za-z0-9_\-]+")
    return token_re.sub(lambda m: translations_for_locale.get(m.group(0), m.group(0)), s)

def translate_structure(obj: Any, translations_for_locale: Dict[str, str], translate_keys: bool = False) -> Any:
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = k
            if translate_keys and k in FIELD_KEY_TO_TRANSLATION_KEY:
                key_token = FIELD_KEY_TO_TRANSLATION_KEY[k]
                new_key = translations_for_locale.get(key_token, k)
            new_dict[new_key] = translate_structure(v, translations_for_locale, translate_keys)
        return new_dict
    elif isinstance(obj, list):
        return [translate_structure(item, translations_for_locale, translate_keys) for item in obj]
    elif isinstance(obj, str):
        return replace_placeholders_in_string(obj, translations_for_locale)
    else:
        return obj

def _ensure_writable_dir(path: str, force: bool = False) -> str:
    """
    Ensure 'path' exists and is a directory.
    - If it doesn't exist: create it.
    - If it exists as a directory: fine.
    - If it exists as a file:
        * if force=True: remove file and create directory at same path.
        * else: create and return a timestamped fallback directory (path + suffix).
    Returns the directory path that will be used.
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return path

    if os.path.isdir(path):
        # Directory already exists — OK
        return path

    # Path exists but is a FILE
    if force:
        # Remove the file and create directory in its place
        os.remove(path)
        os.makedirs(path, exist_ok=True)
        return path

    # Create a fallback directory name
    ts = time.strftime("%Y%m%d-%H%M%S")
    base = os.path.basename(path)
    parent = os.path.dirname(path) or "."
    fallback = os.path.join(parent, f"{base}_build-{ts}")
    os.makedirs(fallback, exist_ok=True)
    print(
        f"[info] '{path}' exists and is a file. "
        f"Using fallback directory: {fallback}"
    )
    return fallback

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument("--translations", default=os.path.join(script_dir, "translation_key.json"),
                        help="Path to translation_key.json (default: same dir as script)")
    parser.add_argument("--input", default=os.path.join(script_dir, "converted_cookie_data.json"),
                        help="Path to input JSON (default: same dir as script)")
    parser.add_argument("--outdir", default=os.path.join(script_dir, "out"),
                        help="Pretty output directory (default: ./out next to script)")
    parser.add_argument("--minout", default=os.path.join(script_dir, "minified"),
                        help="Minified output directory (default: ./minified next to script)")
    parser.add_argument("--translate_keys", action="store_true",
                        help="Also localize selected field/column keys")
    parser.add_argument("--force", action="store_true",
                        help="If a FILE exists at outdir/minout, delete it and create a directory there.")
    args = parser.parse_args()

    translations = load_json(args.translations)
    data = load_json(args.input)

    # Ensure output directories exist and are usable
    outdir = _ensure_writable_dir(args.outdir, force=args.force)
    minout = _ensure_writable_dir(args.minout, force=args.force)

    count = 0
    for locale, tmap in translations.items():
        translated = translate_structure(deepcopy(data), tmap, translate_keys=args.translate_keys)

        # Pretty file
        pretty_path = os.path.join(outdir, f"cookie_data_{locale}.json")
        with open(pretty_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)

        # Minified file
        min_path = os.path.join(minout, f"cookie_data_{locale}.min.json")
        with open(min_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, separators=(',', ':'))

        count += 1

    print(f"Done. Wrote {count} pretty files to: {outdir}")
    print(f"Done. Wrote {count} minified files to: {minout}")

if __name__ == "__main__":
    main()
