"""Recalculate generated workbooks and store evaluated values as OOXML caches.

``formulas`` is the formula evaluation engine. Its Excel function catalog does
not implement SUBTOTAL, so this module registers the two semantics used by this
workbook (103=COUNTA excluding hidden rows; 109=SUM excluding hidden rows).
The workbook's generated transaction table has no hidden rows at export time.
The formulas themselves are preserved; only formula cached values are written.
"""

from __future__ import annotations

import io
import os
import uuid
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
from formulas import ExcelModel
from formulas import functions as formula_functions
from openpyxl import load_workbook


def _subtotal(function_num, values):
    code = int(float(function_num))
    cells = np.asarray(values, dtype=object).ravel()
    if code in (109, 9):
        return round(sum(float(v) for v in cells
                         if isinstance(v, (int, float, np.number))
                         and not isinstance(v, (bool, np.bool_))), 2)
    if code in (103, 3):
        return sum(v is not None and str(v) != "" for v in cells)
    raise ValueError(f"Unsupported SUBTOTAL function number: {code}")


def _register_functions():
    formula_functions.FUNCTIONS["SUBTOTAL"] = formula_functions.wrap_func(_subtotal)
    formula_functions.get_functions.cache_clear()


def recalculate_xlsx(xlsx_bytes: bytes) -> tuple[bytes, dict]:
    """Evaluate every formula with formulas and write the results into OOXML."""
    _register_functions()
    source = io.BytesIO(xlsx_bytes)
    workbook = load_workbook(source, data_only=False, read_only=True)
    formula_cells: list[tuple[str, str, str]] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_cells.append((sheet.title, cell.coordinate, cell.value))
    if not formula_cells:
        return xlsx_bytes, {"engine": "formulas", "formula_count": 0}

    work_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".recalc_work"))
    os.makedirs(work_root, exist_ok=True)
    filename = f"model-{uuid.uuid4().hex}.xlsx"
    model_path = os.path.join(work_root, filename)
    try:
        with open(model_path, "wb") as stream:
            stream.write(xlsx_bytes)
        solution = ExcelModel().loads(model_path).finish().calculate()
    finally:
        try:
            os.remove(model_path)
        except FileNotFoundError:
            pass
    calculated: dict[tuple[str, str], object] = {}
    errors = []
    for sheet, address, formula in formula_cells:
        key = f"'[{filename}]{sheet.upper()}'!{address}"
        result = solution.get(key)
        if result is None:
            errors.append(f"{sheet}!{address}: formula result missing")
            continue
        value = result.value
        if hasattr(value, "reshape"):
            value = value.reshape(-1)[0]
        if isinstance(value, np.generic):
            value = value.item()
        if str(value).startswith("#"):
            errors.append(f"{sheet}!{address}: {value}")
        else:
            calculated[(sheet, address)] = value
    if errors:
        raise ValueError("Workbook formula evaluation failed: " + "; ".join(errors[:20]))
    if len(calculated) != len(formula_cells):
        raise ValueError(f"Evaluated {len(calculated)} of {len(formula_cells)} formulas")

    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
          "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    zin = zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r")
    rel_root = ET.fromstring(zin.read("xl/_rels/workbook.xml.rels"))
    rels = {item.attrib["Id"]: "xl/" + item.attrib["Target"].lstrip("/").removeprefix("xl/")
            for item in rel_root.findall("rel:Relationship", ns)}
    workbook_root = ET.fromstring(zin.read("xl/workbook.xml"))
    sheet_paths = {}
    for item in workbook_root.findall("m:sheets/m:sheet", ns):
        sheet_paths[item.attrib["name"]] = rels[item.attrib[f"{{{ns['r']}}}id"]]

    by_sheet: dict[str, dict[str, object]] = {}
    for (sheet, address), value in calculated.items():
        by_sheet.setdefault(sheet, {})[address] = value
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            sheet_name = next((name for name, path in sheet_paths.items() if path == item.filename), None)
            if sheet_name in by_sheet:
                root = ET.fromstring(data)
                cells = {cell.attrib.get("r"): cell for cell in root.findall(".//m:sheetData/m:row/m:c", ns)}
                for address, value in by_sheet[sheet_name].items():
                    cell = cells.get(address)
                    if cell is None:
                        raise ValueError(f"Formula cell missing from XML: {sheet_name}!{address}")
                    value_node = cell.find("m:v", ns)
                    if value_node is None:
                        value_node = ET.SubElement(cell, f"{{{ns['m']}}}v")
                    if isinstance(value, str):
                        cell.set("t", "str")
                        value_node.text = value
                    elif isinstance(value, bool):
                        cell.set("t", "b")
                        value_node.text = "1" if value else "0"
                    else:
                        cell.attrib.pop("t", None)
                        value_node.text = repr(float(value)) if isinstance(value, (float, int)) else str(value)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            zout.writestr(item, data)
    zin.close()

    result_bytes = output.getvalue()
    verified = load_workbook(io.BytesIO(result_bytes), data_only=False, read_only=True)
    formula_total = sum(1 for sheet in verified for row in sheet.iter_rows()
                        for cell in row if isinstance(cell.value, str) and cell.value.startswith("="))
    if formula_total != len(formula_cells):
        raise ValueError("Formula preservation check failed after cache update")
    return result_bytes, {"engine": f"formulas {__import__('formulas').__version__}",
                          "formula_count": formula_total}
