import io
import re

from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

_FMT = {"money": "#,##0.00;(#,##0.00)", "number": "#,##0", "percent": "0.00"}
_FILL = {"total": "D9E1F2", "subtotal": "EDEDED", "heading": "FFFFFF", "subheading": "F7F7F7"}


def to_xlsx(rep: dict) -> StreamingResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = re.sub(r"[^\w ]", "", rep["title"])[:31] or "Report"
    ws.append([rep["title"]])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([rep["subtitle"]])
    ws.append([])
    cols = rep["columns"]
    ws.append([c["label"] for c in cols])
    for i in range(1, len(cols) + 1):
        cell = ws.cell(row=4, column=i)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="BDD7EE")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for r in rep["rows"]:
        style = r.get("_style")
        ws.append([r.get(c["key"]) for c in cols])
        n = ws.max_row
        for i, c in enumerate(cols, 1):
            cell = ws.cell(row=n, column=i)
            if c["type"] in _FMT:
                cell.number_format = _FMT[c["type"]]
            if style in ("total", "subtotal", "heading", "subheading"):
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor=_FILL[style])

    if rep["notes"]:
        ws.append([])
        for note in rep["notes"]:
            ws.append([note])

    for i, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = 45 if c["key"] in ("title", "label", "descr", "product", "customer") else 18
    ws.freeze_panes = "A5"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = re.sub(r"\W+", "_", rep["title"]).strip("_")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
    )
