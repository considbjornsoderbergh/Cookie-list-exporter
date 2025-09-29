import pandas as pd
import json
from collections import defaultdict

# Load the Excel file
excel_file = '2Kopia av hm-cookielist.xlsx'
df = pd.read_excel(excel_file, engine='openpyxl')

# Rename columns for consistency
df.columns = ['Cookie subgroup', 'Cookies used', 'Cookies', 'Lifespan', 'Cookie category', 'Cookie description']

# Define the desired order of cookie categories
desired_order = [
    "StrictlynecessaryCategoryName",
    "PerformancecookiesCategoryName",
    "FunctionalcookiesCategoryName",
    "MarketingcookiesCategoryName"
]

# Group data by cookie category and description
grouped = defaultdict(lambda: {
    "cookie_category": "",
    "category_description": "",
    "cookie_list": []
})

for _, row in df.iterrows():
    category = row['Cookie category']
    description = row['Cookie description']
    subgroup = row['Cookie subgroup']
    cookies_used = row['Cookies used']  # Keep original value
    cookies = row['Cookies']
    lifespan = row['Lifespan']  # Keep original value

    key = (category, description)
    grouped[key]["cookie_category"] = category
    grouped[key]["category_description"] = description
    grouped[key]["cookie_list"].append({
        "Cookie subgroup": subgroup,
        "Cookies": cookies,
        "Cookies used": cookies_used,
        "Lifespan": lifespan
    })

# Sort the grouped data by the desired category order
sorted_notice_table = sorted(
    grouped.values(),
    key=lambda x: desired_order.index(x["cookie_category"]) if x["cookie_category"] in desired_order else len(desired_order)
)

# Convert to final JSON structure
final_json = {"notice_table": sorted_notice_table}

# Save to a JSON file
with open("converted_cookie_data_ordered.json", "w", encoding="utf-8") as f:
    json.dump(final_json, f, indent=4, ensure_ascii=False)

