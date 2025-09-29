import pandas as pd
import json
from pathlib import Path

# === Inputs ===
excel_file = '2Kopia av hm-cookielist.xlsx'  # adjust if needed

# === Load & normalize ===
df = pd.read_excel(excel_file, engine='openpyxl')

# Make sure we have consistent column names in the expected order
# (adjust these if your sheet has different headers)
df.columns = [
    'Cookie subgroup',       # e.g., hm.com
    'Cookies used',          # e.g., First party / Third party
    'Cookies',               # e.g., _ga, _gid, ...
    'Lifespan',              # e.g., 399 Days, Session, ...
    'Cookie category',       # (not used in the final table, but fine to keep)
    'Cookie description'     # (not used in the final table)
][:len(df.columns)]

# Trim whitespace & drop fully empty rows
for col in ['Cookie subgroup', 'Cookies used', 'Cookies', 'Lifespan']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
df = df.dropna(how='all')

# Keep only the columns we need for the subgroup table
needed = ['Cookie subgroup', 'Cookies used', 'Cookies', 'Lifespan']
df_small = df[needed].copy()

# Optional: preserve original row order within each subgroup when aggregating
# by adding an index to sort back after a groupby
df_small['_row_order'] = range(len(df_small))

# === Group & aggregate ===
rows = []
for subgroup, g in df_small.groupby('Cookie subgroup', dropna=True):
    g_sorted = g.sort_values('_row_order')

    cookies_list   = g_sorted['Cookies'].dropna().tolist()
    lifespan_list  = g_sorted['Lifespan'].dropna().tolist()

    # "Cookies used" can sometimes vary inside a subgroup. Handle that gracefully.
    used_unique = [u for u in g_sorted['Cookies used'].dropna().unique().tolist() if u]
    if len(used_unique) == 1:
        cookies_used_out = used_unique[0]
    elif len(used_unique) == 0:
        cookies_used_out = ''
    else:
        cookies_used_out = 'Mixed: ' + ', '.join(used_unique)

    rows.append({
        'Cookie subgroup': subgroup,
        'Cookies': ', '.join(cookies_list),
        'Cookies used': cookies_used_out,
        'Lifespan': ', '.join(lifespan_list),
    })

result_df = pd.DataFrame(rows)

# Optional: sort by subgroup name
result_df = result_df.sort_values('Cookie subgroup', kind='stable').reset_index(drop=True)

# === Write outputs ===
# CSV for Excel
csv_path = Path('cookie_subgroups_table.csv')
result_df.to_csv(csv_path, index=False, encoding='utf-8')

# JSON (if you still need machine-readable output)
json_path = Path('cookie_subgroups_table.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(result_df.to_dict(orient='records'), f, indent=2, ensure_ascii=False)

print(f'Wrote: {csv_path.resolve()}')
print(f'Wrote: {json_path.resolve()}')
