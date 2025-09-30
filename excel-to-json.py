import pandas as pd
import json
import os
from collections import defaultdict

# Desired category order
desired_order = [
    'Strictly necessary cookies',
    'Performance Cookies',
    'Functional Cookies',
    'Marketing Cookies'
]

excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]

for excel_file in excel_files:
    df = pd.read_excel(excel_file, engine='openpyxl')
    df.columns = ['Cookie subgroup', 'Cookies used', 'Cookies', 'Lifespan', 'Cookie category', 'Cookie description']
    df = df.dropna(subset=['Cookie subgroup', 'Cookie category'])

    category_data = defaultdict(lambda: {'cookie_list': []})

    for category in df['Cookie category'].unique():
        category_desc = df[df['Cookie category'] == category]['Cookie description'].iloc[0]
        category_data[category]['category_description'] = category_desc

    for category in df['Cookie category'].unique():
        category_df = df[df['Cookie category'] == category]
        for domain in category_df['Cookie subgroup'].unique():
            domain_df = category_df[category_df['Cookie subgroup'] == domain]
            cookies = ', '.join(str(v) for v in domain_df['Cookies'] if pd.notna(v))
            cookies_used = domain_df['Cookies used'].iloc[0] if len(domain_df) > 0 else ''
            lifespans = ', '.join(str(v) for v in domain_df['Lifespan'] if pd.notna(v))

            domain_entry = {
                'Cookie subgroup': domain,
                'Cookies': cookies,
                'Cookies used': cookies_used,
                'Lifespan': lifespans
            }
            category_data[category]['cookie_list'].append(domain_entry)

    # Build notice_table in the desired order
    notice_table = []
    for category in desired_order:
        if category in category_data:
            notice_table.append({
                'cookie_category': category,
                'category_description': category_data[category]['category_description'],
                'cookie_list': category_data[category]['cookie_list']
            })

    final_json = {'notice_table': notice_table}

    base_name = os.path.splitext(os.path.basename(excel_file))[0]
    json_filename = f"{base_name}_grouped.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=4, ensure_ascii=False)
