#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import re
import time
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

def make_case_insensitive_map(translations_for_locale: Dict[str, str]) -> Dict[str, str]:
    # Lowercased key -> translated value (original value preserved)
    return {k.lower(): v for k, v in translations_for_locale.items()}

def replace_placeholders_in_string(s: str, translations_for_locale: Dict[str, str], ci_map: Dict[str, str]) -> str:
    if not isinstance(s, str):
        return s

    # If full string matches (case-insensitive), replace whole thing
    val = ci_map.get(s.lower())
    if val is not None:
        return val

    # Otherwise replace tokens inside the string (e.g., "395 CookiePolicyTableDays")
    token_re = re.compile(r"[A-Za-z0-9_\-]+")
    def repl(m: re.Match) -> str:
        tok = m.group(0)
        return translations_for_locale.get(tok, ci_map.get(tok.lower(), tok))
    return token_re.sub(repl, s)

def translate_structure(obj: Any, translations_for_locale: Dict[str, str], ci_map: Dict[str, str], translate_keys: bool=False) -> Any:
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = k
            if translate_keys and k in FIELD_KEY_TO_TRANSLATION_KEY:
                key_token = FIELD_KEY_TO_TRANSLATION_KEY[k]
                new_key = translations_for_locale.get(key_token, ci_map.get(key_token.lower(), k))
            new_dict[new_key] = translate_structure(v, translations_for_locale, ci_map, translate_keys)
        return new_dict
    elif isinstance(obj, list):
        return [translate_structure(x, translations_for_locale, ci_map, translate_keys) for x in obj]
    elif isinstance(obj, str):
        return replace_placeholders_in_string(obj, translations_for_locale, ci_map)
    else:
        return obj

def _ensure_writable_dir(path: str, force: bool=False) -> str:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return path
    if os.path.isdir(path):
        return path
    if force:
        os.remove(path)
        os.makedirs(path, exist_ok=True)
        return path
    ts = time.strftime("%Y%m%d-%H%M%S")
    parent = os.path.dirname(path) or "."
    base = os.path.basename(path)
    fallback = os.path.join(parent, f"{base}_build-{ts}")
    os.makedirs(fallback, exist_ok=True)
    print(f"[info] '{path}' is a file; using fallback dir: {fallback}")
    return fallback

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument("--translations", default=os.path.join(script_dir, "translation_key.json"))
    parser.add_argument("--input", default=os.path.join(script_dir, "converted_cookie_data.json"))
    parser.add_argument("--outdir", default=os.path.join(script_dir, "out"))
    parser.add_argument("--minout", default=os.path.join(script_dir, "minified"))
    parser.add_argument("--translate_keys", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    translations = load_json(args.translations)
    data = load_json(args.input)

    outdir = _ensure_writable_dir(args.outdir, force=args.force)
    minout = _ensure_writable_dir(args.minout, force=args.force)

    count = 0
    for locale, tmap in translations.items():
        ci_map = make_case_insensitive_map(tmap)
        translated = translate_structure(deepcopy(data), tmap, ci_map, translate_keys=args.translate_keys)

        pretty_path = os.path.join(outdir, f"cookie_data_{locale}.json")
        with open(pretty_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, indent=2)

        min_path = os.path.join(minout, f"cookie_data_{locale}.min.json")
        with open(min_path, "w", encoding="utf-8") as f:
            json.dump(translated, f, ensure_ascii=False, separators=(',', ':'))

        count += 1

    print(f"Done. Wrote {count} pretty files to: {outdir}")
    print(f"Done. Wrote {count} minified files to: {minout}")

if __name__ == "__main__":
    main()
