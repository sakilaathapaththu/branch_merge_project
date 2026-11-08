"""Common report shape used by every report, the frontend table and the Excel export.

{
  "title": str, "subtitle": str,
  "columns": [{"key", "label", "type": "text|money|number|percent|date"}],
  "rows": [{<key>: value, "_style": "heading|subtotal|total|detail"?}],
  "notes": [str]
}
"""
from fastapi import HTTPException

from app.core.config import get_settings


def resolve_branches(branch: str) -> list[str]:
    branches = get_settings().branches
    if branch == "all":
        return list(branches)
    if branch not in branches:
        raise HTTPException(400, f"Unknown branch {branch!r}; use 'all' or one of {list(branches)}")
    return [branch]


def db(code: str) -> str:
    return get_settings().branches[code]["database"]


def short(code: str) -> str:
    return get_settings().branches[code]["short"]


def branch_label(codes: list[str]) -> str:
    b = get_settings().branches
    return "Consolidated (all branches)" if len(codes) > 1 else f"{codes[0]} – {b[codes[0]]['name']}"


def amount_columns(codes: list[str], label: str = "Amount") -> list[dict]:
    """Per-branch + eliminations + consolidated columns when several branches."""
    if len(codes) == 1:
        return [{"key": "total", "label": label, "type": "money"}]
    return (
        [{"key": f"b{c}", "label": short(c), "type": "money"} for c in codes]
        + [
            {"key": "elim", "label": "Eliminations", "type": "money"},
            {"key": "total", "label": "Consolidated", "type": "money"},
        ]
    )


def report(title: str, codes: list[str], columns: list[dict], rows: list[dict],
           subtitle: str = "", notes: list[str] | None = None) -> dict:
    return {
        "title": title,
        "subtitle": " · ".join(filter(None, [branch_label(codes), subtitle])),
        "columns": columns,
        "rows": rows,
        "notes": notes or [],
    }
