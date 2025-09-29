#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate converted_cookie_data.json into fully localized JSONs using translation_key.json.
Outputs:
  - Pretty JSONs in: out/
  - Minified JSONs in: minified/

Features:
- Replaces placeholder tokens with the localized strings for each locale.
- Handles mixed strings like "395 CookiePolicyTableDays".
- Optional localization of column headers (use --translate_keys).
- Defaults to using files from the same folder as this script.
"""

import argparse
import json
import os
import re
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
    args = parser.parse_args()

    translations = load_json(args.translations)
    data = load_json(args.input)

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.minout, exist_ok=True)

    count = 0
    for locale, tmap in translations.items():
        translated = translate_structure(deepcopy(data), tmap, translate_keys=args.translate_keys)

        # Pretty file
        pretty_path = os.path.join(args.outdir, f"cookie_data_{locale}.json")
        with open(pretty_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)

        # Minified file
        min_path = os.path.join(args.minout, f"cookie_data_{locale}.min.json")
        with open(min_path, "w", encoding="utf-8") as f:
            # separators=(',', ':') removes spaces after commas/colons
            json.dump(translated, f, ensure_ascii=False, separators=(',', ':'))
        count += 1

    print(f"Done. Wrote {count} pretty files to: {args.outdir}")
    print(f"Done. Wrote {count} minified files to: {args.minout}")

if __name__ == "__main__":
    main()
