#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translate grouped JSONs into localized JSONs using translation_key.json.
Outputs:
 - Pretty JSONs in: out/
 - Minified JSONs in: minified/
"""

import argparse
import json
import os
import re
from copy import deepcopy
from typing import Any, Dict

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
    if s in translations_for_locale:
        return translations_for_locale[s]
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--translations", default="translation_key.json", help="Path to translation_key.json")
    parser.add_argument("--outdir", default="out", help="Pretty output directory")
    parser.add_argument("--minout", default="minified", help="Minified output directory")
    parser.add_argument("--translate_keys", action="store_true", help="Also localize selected field/column keys")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.minout, exist_ok=True)

    translations = load_json(args.translations)
    grouped_jsons = [f for f in os.listdir('.') if f.endswith('_grouped.json')]

    for input_file in grouped_jsons:
        base_name = os.path.splitext(input_file)[0].replace('_grouped', '')
        data = load_json(input_file)

        for locale, tmap in translations.items():
            # Sanitize locale to use only underscores
            safe_locale = re.sub(r'[^A-Za-z0-9]+', '_', locale)

            translated = translate_structure(deepcopy(data), tmap, translate_keys=args.translate_keys)

            pretty_path = os.path.join(args.outdir, f"{base_name}_{safe_locale}.json")
            with open(pretty_path, "w", encoding="utf-8") as f:
                json.dump(translated, f, ensure_ascii=False, indent=2)

            min_path = os.path.join(args.minout, f"{base_name}_{safe_locale}.min.json")
            with open(min_path, "w", encoding="utf-8") as f:
                json.dump(translated, f, ensure_ascii=False, separators=(',', ':'))

            print(f"✅ Translated: {pretty_path} / {min_path}")

if __name__ == "__main__":
    main()
