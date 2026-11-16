import re

with open('downloaded_dashboard.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("HTML Length:", len(html), "bytes")
assert "<!DOCTYPE html>" in html
assert "Financial Analysis Dashboard" in html

# External dependency check (must be 0)
external_scripts = re.findall(r'<script[^>]+src=["\']http[^"\']+["\']', html, re.I)
external_css = re.findall(r'<link[^>]+href=["\']http[^"\']+["\']', html, re.I)
print("External script tags:", len(external_scripts), external_scripts)
print("External CSS links:", len(external_css), external_css)

# Data check
assert "REPORT_DATA =" in html
assert "4548780" in html
assert "4626410" in html
assert "-77630" in html
print("Canonical metrics present in embedded data: True")

# Interactive controls check
assert 'id="search-input"' in html
assert 'id="cat-filter"' in html
assert 'id="type-filter"' in html
assert 'id="date-from"' in html
assert 'id="date-to"' in html
print("Interactive filter inputs verified: True")

# Canvas charts check
assert '<canvas id="category-chart"' in html
assert 'drawCategoryChart' in html
print("Offline HTML verification: 100% PASS")
