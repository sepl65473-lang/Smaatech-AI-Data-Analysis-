import requests
import json

sid = '13890ba5-5c23-4a37-b9a3-47ebc8493c87'

# 1. Check Export Status
r_status = requests.get(f'http://127.0.0.1:8000/api/export/{sid}/status')
print('=== EXPORT STATUS ===')
print(f'Status Code: {r_status.status_code}')
print(json.dumps(r_status.json(), indent=2))

# 2. Test Export Formats
print('\n=== EXPORT FORMAT DOWNLOADS ===')
for fmt in ['pdf', 'xlsx', 'html', 'zip', 'csv']:
    r = requests.get(f'http://127.0.0.1:8000/api/export/{sid}?format={fmt}')
    cdisp = r.headers.get('content-disposition', '')
    ctype = r.headers.get('content-type', '')
    print(f'Format [{fmt.upper()}]: HTTP {r.status_code} | Size: {len(r.content):,} bytes | Type: {ctype} | Disp: {cdisp}')

# 3. Test Preview Formats
print('\n=== IN-APP PREVIEW ENDPOINTS ===')
r_prev_xlsx = requests.get(f'http://127.0.0.1:8000/api/export/{sid}?format=xlsx&preview=true')
xlsx_meta = r_prev_xlsx.json()
print(f'XLSX Preview: HTTP {r_prev_xlsx.status_code} | Sheets: {list(xlsx_meta.get("sheets", {}).keys())}')

r_prev_pdf = requests.get(f'http://127.0.0.1:8000/api/export/{sid}?format=pdf&preview=true')
print(f'PDF Inline: HTTP {r_prev_pdf.status_code} | Size: {len(r_prev_pdf.content):,} bytes | Disp: {r_prev_pdf.headers.get("content-disposition")}')
