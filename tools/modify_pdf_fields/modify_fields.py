#!/usr/bin/env python3
"""Modify form field positions/sizes in a local PDF using a JSON spec (mm).

Spec format (example):
{
  "fields": [
    {
      "name": "insertDate",
      "pageNumber": 1,
      "locations": [
        {"pageNumber": 1, "top": 29.31, "left": 82.8, "width": 172.0, "height": 8.8}
      ]
    }
  ]
}

Notes:
- Units in the spec are millimeters (mm). The script converts to PDF points.
- `top` is distance from the top edge of the page.
- Supports `width`/`height` or `right`/`under` (interpreted as width/height).
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any

log = logging.getLogger(__name__)


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def load_spec(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def find_widget_for_name(page, name: str):
    annots = page.get("/Annots")
    if not annots:
        return []
    widgets = []
    for a in annots:
        obj = a.get_object()
        t = obj.get("/T")
        if t and str(t) == name:
            widgets.append(obj)
    return widgets


def update_rect(widget, llx: float, lly: float, urx: float, ury: float) -> None:
    widget["/Rect"] = [llx, lly, urx, ury]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Modify PDF field positions from JSON spec (mm)"
    )
    parser.add_argument("pdf", help="Path to source PDF file")
    parser.add_argument("spec", help="JSON spec file with fields array")
    parser.add_argument(
        "--output", help="Output PDF path (defaults to <input>-modified.pdf)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing file",
    )
    args = parser.parse_args()

    try:
        from pypdf import PdfReader, PdfWriter
    except Exception as e:
        log.error("pypdf not installed. Install with: pip install pypdf")
        return 2

    pdf_path = Path(args.pdf)
    spec_path = Path(args.spec)
    if not pdf_path.exists():
        log.error("PDF not found: %s", pdf_path)
        return 3
    if not spec_path.exists():
        log.error("Spec not found: %s", spec_path)
        return 4

    spec = load_spec(spec_path)
    fields = spec.get("fields", [])
    if not fields:
        log.error("No fields defined in spec")
        return 5

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    # copy pages into writer (we'll modify annotations in-place on page objects)
    for p in reader.pages:
        writer.add_page(p)

    for f in fields:
        name = f.get("name")
        if not name:
            log.warning("Skipping field with no name: %s", f)
            continue
        locs = f.get("locations") or []
        for loc in locs:
            page_no = int(loc.get("pageNumber", 1)) - 1
            if page_no < 0 or page_no >= len(reader.pages):
                log.warning(
                    "Invalid pageNumber %s for field %s", loc.get("pageNumber"), name
                )
                continue
            page = reader.pages[page_no]

            # determine width/height in mm
            if "width" in loc and "height" in loc:
                width_mm = float(loc["width"])
                height_mm = float(loc["height"])
            else:
                # accept alternative keys 'right' and 'under' as width/height
                width_mm = float(loc.get("right", loc.get("width", 0)))
                height_mm = float(loc.get("under", loc.get("height", 0)))

            left_mm = float(loc.get("left", 0))
            top_mm = float(loc.get("top", 0))

            left_pt = mm_to_pt(left_mm)
            height_pt = mm_to_pt(height_mm)
            width_pt = mm_to_pt(width_mm)

            # page height in points
            try:
                page_height = float(page.mediabox.top)
            except Exception:
                # fallback: compute from mediabox coords
                mb = page.mediabox
                page_height = float(mb[3])

            # top is distance from top edge -> compute lower-left y
            lly = page_height - mm_to_pt(top_mm) - height_pt
            llx = left_pt
            urx = llx + width_pt
            ury = lly + height_pt

            widgets = find_widget_for_name(page, name)
            if not widgets:
                log.warning(
                    "No widget annotation found for field '%s' on page %d",
                    name,
                    page_no + 1,
                )
                continue

            for w in widgets:
                old_rect = w.get("/Rect")
                log.info(
                    "Field %s old Rect=%s -> new rect=[%s,%s,%s,%s] (pts)",
                    name,
                    old_rect,
                    llx,
                    lly,
                    urx,
                    ury,
                )
                if not args.dry_run:
                    update_rect(w, llx, lly, urx, ury)

    if args.dry_run:
        log.info("Dry-run complete. No output written.")
        return 0

    out_path = (
        Path(args.output)
        if args.output
        else pdf_path.with_name(pdf_path.stem + "-modified.pdf")
    )
    with open(out_path, "wb") as fh:
        writer.write(fh)

    log.info("Wrote modified PDF to %s", out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    raise SystemExit(main())
