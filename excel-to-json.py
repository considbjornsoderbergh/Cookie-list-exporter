
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate converted_cookie_data.json into fully localized JSONs using translation_key.json.

Features:
- Replaces placeholder tokens like "StrictlynecessaryCategoryName", "CookiePolicyTableDays",
  including cases such as "395 CookiePolicyTableDays" or strings that are just a key.
- Optionally renames certain field/column names (keys) in the output using a mapping to
  translation keys (e.g., "Lifespan" -> "CookiePolicyTableLifespan"), pulling the localized
  label per locale from translation_key.json.
- Writes one JSON per locale to the output directory.

Usage (defaults shown):
    python json_translator_rewrite.py \
        --translations /mnt/data/translation_key.json \
        --input /mnt/data/converted_cookie_data.json \
        --outdir /mnt/data/out \
        [--translate_keys]

If --translate_keys is provided, certain top-level table column names will be localized.
"""

import argparse
import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, Tuple


# A mapping of English field/column keys in converted_cookie_data.json to translation keys
# that exist in translation_key.json. If --translate_keys is used, we rename those keys.
FIELD_KEY_TO_TRANSLATION_KEY = {
    "Cookie subgroup": "CookiePolicyTableCookeiSubgroup",
    "Cookies": "CookiePolicyTableCookies",
    "Cookies used": "CookiePolicyTableCookiesUsed",
    "Lifespan": "CookiePolicyTableLifespan",
    # If you later want to localize other structural keys, add them here.
    # Note: We do NOT rename structural keys like "cookie_category", "category_description",
    # and "cookie_list" to keep the data structure stable for consumers.
}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_placeholder_token(token: str, translations_for_locale: Dict[str, str]) -> bool:
    """
    Determine if the string token corresponds exactly to a translation key.
    """
    return token in translations_for_locale


def replace_placeholders_in_string(
    s: str, translations_for_locale: Dict[str, str]
) -> str:
    """
    Replace placeholders in a string. Handles two cases:
    1) The whole string is a placeholder key (e.g., "StrictlynecessaryCategoryName").
    2) The string contains one or more placeholder tokens mixed with other text, e.g.:
          "395 CookiePolicyTableDays", " CookiePolicyTableSession"
    We replace only the placeholder parts that match keys in translations_for_locale.

    We preserve original spacing around tokens.
    """
    if not isinstance(s, str):
        return s

    # If the entire string is a placeholder
    if s in translations_for_locale:
        return translations_for_locale[s]

    # Otherwise, replace placeholder tokens within the string
    # We'll split on word-like tokens while preserving whitespace and punctuation
    def repl(match: re.Match) -> str:
        token = match.group(0)
        return translations_for_locale.get(token, token)

    # Tokens can contain letters, numbers, underscores, and hyphens (e.g., en-AU in keys),
    # but our placeholders look like "CookiePolicyTableDays", "StrictlynecessaryCategoryName", etc.
    # We'll match sequences of [A-Za-z0-9_\-]+ and replace if in translations map.
    pattern = re.compile(r"[A-Za-z0-9_\-]+")
    return pattern.sub(repl, s)


def translate_structure(
    obj: Any,
    translations_for_locale: Dict[str, str],
    translate_keys: bool = False,
) -> Any:
    """
    Recursively translate all placeholder strings found in values.
    If translate_keys=True, also rename certain keys using FIELD_KEY_TO_TRANSLATION_KEY.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = k
            if translate_keys and k in FIELD_KEY_TO_TRANSLATION_KEY:
                key_token = FIELD_KEY_TO_TRANSLATION_KEY[k]
                new_key = translations_for_locale.get(key_token, k)  # fallback to original key if missing

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
    parser.add_argument("--translations", default="/mnt/data/translation_key.json", help="Path to translation_key.json")
    parser.add_argument("--input", default="/mnt/data/converted_cookie_data.json", help="Path to input JSON with placeholders")
    parser.add_argument("--outdir", default="/mnt/data/out", help="Output directory for per-locale JSON files")
    parser.add_argument("--translate_keys", action="store_true", help="Also localize selected field/column keys")
    args = parser.parse_args()

    translations = load_json(args.translations)  # { locale: { key: "translated string", ... }, ... }
    data = load_json(args.input)

    os.makedirs(args.outdir, exist_ok=True)

    # For each locale, produce a fully translated copy
    for locale, tmap in translations.items():
        translated = translate_structure(deepcopy(data), tmap, translate_keys=args.translate_keys)

        out_path = os.path.join(args.outdir, f"cookie_data_{locale}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)

    print(f"Done. Wrote {len(translations)} localized files to: {args.outdir}")


if __name__ == "__main__":
    main()
