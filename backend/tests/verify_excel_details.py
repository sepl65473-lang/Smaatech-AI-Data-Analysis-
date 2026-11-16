import openpyxl

wb = openpyxl.load_workbook('downloaded_workbook.xlsx', data_only=False)

for name in wb.sheetnames:
    ws = wb[name]
    formulas = [cell.value for row in ws.iter_rows() for cell in row if isinstance(cell.value, str) and cell.value.startswith('=')]
    print(f"Sheet: {name:30} | Rows: {ws.max_row:4} | Cols: {ws.max_column:2} | Formulas: {len(formulas):3} | First: {str(formulas[0])[:35] if formulas else 'N/A'}")

ws_tx = wb['Complete Transactions']
print("\nComplete Transactions Auto-Filter:", ws_tx.auto_filter.ref)
print("Complete Transactions Freeze Panes:", ws_tx.freeze_panes)
headers = [cell.value for cell in ws_tx[1]]
print("Headers:", headers)
