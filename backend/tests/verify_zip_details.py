import zipfile
import pypdf
import openpyxl

with zipfile.ZipFile('downloaded_package.zip', 'r') as zf:
    names = zf.namelist()
    print("Files in ZIP:", names)
    assert len(names) == 3, f"Expected 3 files, got {len(names)}"
    
    pdf_name = next(n for n in names if n.endswith('.pdf'))
    xlsx_name = next(n for n in names if n.endswith('.xlsx'))
    html_name = next(n for n in names if n.endswith('.html'))
    
    # Read PDF from zip
    with zf.open(pdf_name) as f:
        reader = pypdf.PdfReader(f)
        print(f"ZIP -> {pdf_name}: {len(reader.pages)} pages")
        assert len(reader.pages) >= 10
        
    # Read XLSX from zip
    with zf.open(xlsx_name) as f:
        wb = openpyxl.load_workbook(f)
        print(f"ZIP -> {xlsx_name}: sheets = {wb.sheetnames}")
        assert len(wb.sheetnames) == 7
        
    # Read HTML from zip
    with zf.open(html_name) as f:
        html = f.read().decode('utf-8')
        print(f"ZIP -> {html_name}: {len(html)} bytes")
        assert "<!DOCTYPE html>" in html
        assert "REPORT_DATA =" in html

print("ZIP package verification: 100% PASS")
