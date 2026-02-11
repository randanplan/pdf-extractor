# scripts/analyze_pdf_styles.py
"""
PDF Style Analyzer (PyMuPDF)

Analysiert Vektor-Drawings einer PDF-Seite (page.get_drawings()) und gruppiert sie nach Style:
- width
- color (stroke)
- fill
- type
- lineCap / lineJoin
- even_odd
- dashes

Filter:
- Style/Drawing: width±tol, color, fill, type, dashed/solid, lineCap, lineJoin, evenOdd
- Drawing-level items: --filter-items-count/min/max (len(items) pro drawing)
- Style-level items: --style-items-count/min/max (agg.items_min/max über einen Style)
- Style min-count: --min-count (Aggregat pro Style)

Export:
- json (aggregierte Styles, nach Filtern)
- csv (aggregierte Styles, nach Filtern)
- json_raw (Drawings, nach Filtern)
- png (BBox Overlay für Drawings, nach Filtern)

Beispiele:
  python scripts/analyze_pdf_styles.py "file.pdf"
  python scripts/analyze_pdf_styles.py "file.pdf" --page 0 --filter-items-count 120
  python scripts/analyze_pdf_styles.py "file.pdf" --page 0 --export png --filter-items-count 120
  python scripts/analyze_pdf_styles.py "file.pdf" --page 0 --export json_raw --filter-color "(95,95,95)" --filter-width 0.51023 --width-tol 0.06
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# PyMuPDF import (support both)
try:
    import pymupdf as fitz  # type: ignore
except Exception:  # pragma: no cover
    import fitz  # type: ignore

RGB = Tuple[int, int, int]


# -----------------------------
# Logging
# -----------------------------
def setup_logging(level: str = "INFO", log_file: str = "pdf_analysis.log") -> logging.Logger:
    logger = logging.getLogger("pdf-style-analyzer")
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


logger = setup_logging()


# -----------------------------
# Utils
# -----------------------------
def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def clamp_int(v: int, lo: int = 0, hi: int = 255) -> int:
    return int(max(lo, min(hi, v)))


def norm_rgb(c: Any) -> Optional[RGB]:
    """
    Normalisiert stroke/fill Farben aus PyMuPDF:
    - floats 0..1 -> 0..255
    - ints 0..255 -> unverändert
    """
    if c is None:
        return None
    if not isinstance(c, (list, tuple)) or len(c) < 3:
        return None

    try:
        vals = [float(x) for x in c[:3]]
    except Exception:
        return None

    mx = max(vals)
    if mx <= 1.0:
        r, g, b = (clamp_int(int(round(v * 255.0))) for v in vals)
        return (r, g, b)

    r, g, b = (clamp_int(int(round(v))) for v in vals)
    return (r, g, b)


def parse_rect(rect: Any) -> Optional[fitz.Rect]:
    """Akzeptiert fitz.Rect oder 'Rect(x0, y0, x1, y1)' als String."""
    if rect is None:
        return None
    if isinstance(rect, fitz.Rect):
        return rect
    s = str(rect).strip()
    m = re.match(r"Rect\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)$", s)
    if not m:
        return None
    try:
        x0, y0, x1, y1 = (float(m.group(i)) for i in range(1, 5))
        return fitz.Rect(x0, y0, x1, y1)
    except Exception:
        return None


def rect_to_list(r: Optional[fitz.Rect]) -> Optional[List[float]]:
    if r is None:
        return None
    return [float(r.x0), float(r.y0), float(r.x1), float(r.y1)]


def to_jsonable(x: Any) -> Any:
    """
    Rekursive Serialisierung für json_raw:
    - Rect -> [x0,y0,x1,y1]
    - Point -> [x,y]
    - dict/list -> rekursiv
    """
    if x is None or isinstance(x, (str, int, float, bool)):
        return x

    if isinstance(x, fitz.Rect):
        return rect_to_list(x)

    # fitz.Point hat x,y
    if hasattr(x, "x") and hasattr(x, "y"):
        try:
            return [float(x.x), float(x.y)]
        except Exception:
            pass

    if isinstance(x, dict):
        return {str(k): to_jsonable(v) for k, v in x.items()}

    if isinstance(x, (list, tuple)):
        return [to_jsonable(v) for v in x]

    return str(x)


def default_export_path(pdf_path: str, page_num: int, suffix: str) -> str:
    base = os.path.splitext(pdf_path)[0]
    return f"{base}_p{page_num+1}_{suffix}"


def is_dashed(dashes: Optional[str]) -> bool:
    if not dashes:
        return False
    s = str(dashes).strip()
    # PyMuPDF often: "[] 0" => solid
    return not s.startswith("[]")


def style_to_rgba(seed: str) -> Tuple[int, int, int, int]:
    # deterministisch, damit gleiche Styles gleiche Farbe bekommen
    h = 0
    for ch in seed:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    r = 80 + (h & 0x7F)
    g = 80 + ((h >> 7) & 0x7F)
    b = 80 + ((h >> 14) & 0x7F)
    return (int(r), int(g), int(b), 220)


# -----------------------------
# Style model
# -----------------------------
@dataclass(frozen=True)
class StyleKey:
    width: Optional[float]
    color: Optional[RGB]
    fill: Optional[RGB]
    obj_type: str
    line_cap: Optional[Tuple[int, int, int]]
    line_join: Optional[float]
    even_odd: Optional[bool]
    dashes: Optional[str]


@dataclass
class StyleAgg:
    count: int = 0
    example_seqno: Optional[int] = None
    example_rect: Optional[fitz.Rect] = None
    items_min: Optional[int] = None
    items_max: Optional[int] = None
    items_sum: int = 0

    def add(self, seqno: Optional[int], rect: Optional[fitz.Rect], items_count: int) -> None:
        self.count += 1
        self.items_sum += items_count
        self.items_min = items_count if self.items_min is None else min(self.items_min, items_count)
        self.items_max = items_count if self.items_max is None else max(self.items_max, items_count)
        if self.example_seqno is None:
            self.example_seqno = seqno
        if self.example_rect is None:
            self.example_rect = rect

    @property
    def items_avg(self) -> float:
        return (self.items_sum / self.count) if self.count else 0.0


def line_cap_key(lc: Any) -> Optional[Tuple[int, int, int]]:
    if lc is None:
        return None
    if isinstance(lc, (list, tuple)) and len(lc) >= 3:
        try:
            return (int(lc[0]), int(lc[1]), int(lc[2]))
        except Exception:
            return None
    return None


def round_width(w: Any, ndigits: int) -> Optional[float]:
    if w is None:
        return None
    try:
        return round(float(w), ndigits)
    except Exception:
        return None


def extract_style(draw: Dict[str, Any], width_round: int = 12) -> Tuple[StyleKey, int, Optional[int], Optional[fitz.Rect]]:
    width = round_width(draw.get("width"), width_round)
    color = norm_rgb(draw.get("color"))
    fill = norm_rgb(draw.get("fill"))
    obj_type = str(draw.get("type", "unknown"))
    seqno = draw.get("seqno")
    line_cap = line_cap_key(draw.get("lineCap"))
    line_join_raw = draw.get("lineJoin")
    try:
        line_join = float(line_join_raw) if line_join_raw is not None else None
    except Exception:
        line_join = None
    even_odd = draw.get("even_odd")
    even_odd = even_odd if isinstance(even_odd, bool) else None
    dashes = draw.get("dashes")
    dashes = str(dashes) if dashes is not None else None
    rect = parse_rect(draw.get("rect"))

    items = draw.get("items") or []
    items_count = len(items) if isinstance(items, list) else 0

    key = StyleKey(
        width=width,
        color=color,
        fill=fill,
        obj_type=obj_type,
        line_cap=line_cap,
        line_join=line_join,
        even_odd=even_odd,
        dashes=dashes,
    )
    seqno_i = int(seqno) if isinstance(seqno, int) else None
    return key, items_count, seqno_i, rect


# -----------------------------
# Filters
# -----------------------------
@dataclass
class Filters:
    # style-like filters (apply both on drawing and style level)
    width: Optional[float] = None
    width_tol: float = 0.01
    color: Optional[RGB] = None
    fill: Optional[RGB] = None
    obj_type: Optional[str] = None
    dashed: Optional[bool] = None  # True dashed, False solid, None ignore
    line_cap: Optional[Tuple[int, int, int]] = None
    line_join: Optional[float] = None
    even_odd: Optional[bool] = None

    # style-level filter (after aggregation)
    min_count: Optional[int] = None

    # drawing-level items filters (len(items) pro drawing)  ✅ das ist dein use-case
    drawing_items_eq: Optional[int] = None
    drawing_items_min: Optional[int] = None
    drawing_items_max: Optional[int] = None

    # style-level items filters (über agg.items_min/max) – optional
    style_items_eq: Optional[int] = None
    style_items_min: Optional[int] = None
    style_items_max: Optional[int] = None


def match_key_filters(f: Filters, key: StyleKey) -> bool:
    if f.width is not None:
        if key.width is None or abs(float(key.width) - float(f.width)) > float(f.width_tol):
            return False

    if f.color is not None and key.color != f.color:
        return False

    if f.fill is not None and key.fill != f.fill:
        return False

    if f.obj_type is not None and key.obj_type != f.obj_type:
        return False

    if f.dashed is not None:
        if is_dashed(key.dashes) != f.dashed:
            return False

    if f.line_cap is not None and key.line_cap != f.line_cap:
        return False

    if f.line_join is not None:
        if key.line_join is None or abs(float(key.line_join) - float(f.line_join)) > 1e-9:
            return False

    if f.even_odd is not None and key.even_odd != f.even_odd:
        return False

    return True


def match_drawing_filters(f: Filters, key: StyleKey, items_count: int) -> bool:
    """Filter auf Drawing-Level (inkl. len(items))."""
    if not match_key_filters(f, key):
        return False

    if f.drawing_items_eq is not None and items_count != f.drawing_items_eq:
        return False
    if f.drawing_items_min is not None and items_count < f.drawing_items_min:
        return False
    if f.drawing_items_max is not None and items_count > f.drawing_items_max:
        return False

    return True


def match_style_filters(f: Filters, key: StyleKey, agg: StyleAgg) -> bool:
    """Filter auf aggregiertem Style-Level (inkl. min_count, optional style_items_*)."""
    if not match_key_filters(f, key):
        return False

    if f.min_count is not None and agg.count < f.min_count:
        return False

    if f.style_items_eq is not None:
        if agg.items_min is None or agg.items_max is None:
            return False
        if not (agg.items_min == agg.items_max == f.style_items_eq):
            return False

    if f.style_items_min is not None and (agg.items_min is None or agg.items_min < f.style_items_min):
        return False

    if f.style_items_max is not None and (agg.items_max is None or agg.items_max > f.style_items_max):
        return False

    return True


# -----------------------------
# PNG overlay
# -----------------------------
def export_marked_png(
    page: fitz.Page,
    drawings: List[Dict[str, Any]],
    filters: Filters,
    export_path: str,
    pdf_path: str,
    page_num: int,
    zoom: float = 2.0,
    max_boxes: int = 5000,
    show_labels: bool = False,
    width_round: int = 12,
) -> str:
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception as e:
        raise RuntimeError("PNG export benötigt Pillow (pip install pillow).") from e

    export_path = export_path or default_export_path(pdf_path, page_num, "styles.png")
    Path(export_path).parent.mkdir(parents=True, exist_ok=True)

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.open(BytesIO(pix.tobytes("png"))).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    marked = 0
    skipped_no_rect = 0

    for idx, d in enumerate(drawings):
        key, items_count, _, rect = extract_style(d, width_round=width_round)

        # drawing-level filtering
        if not match_drawing_filters(filters, key, items_count):
            continue

        if rect is None:
            skipped_no_rect += 1
            continue

        x0 = rect.x0 * zoom
        y0 = rect.y0 * zoom
        x1 = rect.x1 * zoom
        y1 = rect.y1 * zoom

        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0

        x0 = clamp(x0, 0, img.size[0] - 1)
        x1 = clamp(x1, 0, img.size[0] - 1)
        y0 = clamp(y0, 0, img.size[1] - 1)
        y1 = clamp(y1, 0, img.size[1] - 1)

        # Deterministische Farbe basierend auf Style, damit gleiche Styles gleiche Farben bekommen
        seed = f"{key.width}|{key.color}|{key.fill}|{key.obj_type}|{key.line_cap}|{key.line_join}|{key.even_odd}|{key.dashes}"
        
        # Outline mit voller Deckkraft
        outline = style_to_rgba(seed)
        
        # Fill mit reduzierter Deckkraft (z.B. 55 von 255), damit darunterliegende Objekte sichtbar bleiben
        fill_rgba = (outline[0], outline[1], outline[2], 55)

        # Rechteck zeichnen: Outline + transparenter Fill für bessere Sichtbarkeit
        draw.rectangle([x0, y0, x1, y1], outline=outline, fill=fill_rgba, width=2.5)

        if show_labels:
            label = str(marked + 1)
            tx, ty = x0 + 2, y0 + 2
            draw.rectangle([tx, ty, tx + 30, ty + 14], fill=(0, 0, 0, 160))
            draw.text((tx + 2, ty), label, fill=(255, 255, 255, 255), font=font)

        marked += 1
        if marked >= max_boxes:
            logger.warning(f"Reached max_boxes={max_boxes}. Stopping overlay rendering.")
            break

    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(export_path, format="PNG")

    logger.info(f"PNG export: {export_path} (marked={marked}, skipped_no_rect={skipped_no_rect}, zoom={zoom})")
    return export_path


# -----------------------------
# Core analysis
# -----------------------------
def validate_pdf_path(pdf_path: str) -> str:
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if p.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid file type. Expected PDF, got: {pdf_path}")
    return str(p.resolve())


def validate_page_number(doc: fitz.Document, page_num: int) -> int:
    if page_num < 0 or page_num >= len(doc):
        raise ValueError(f"Page number {page_num} out of range. Document has {len(doc)} pages.")
    return page_num


def analyze_pdf_styles(
    pdf_path: str,
    page_num: int = 0,
    export_format: Optional[str] = None,
    export_path: Optional[str] = None,
    filters: Optional[Filters] = None,
    width_round: int = 12,
    sort_by: str = "width",
    png_zoom: float = 2.0,
    png_max_boxes: int = 5000,
    png_labels: bool = False,
) -> None:
    filters = filters or Filters()
    pdf_path = validate_pdf_path(pdf_path)
    logger.info(f"Analyzing {pdf_path}, page={page_num}")

    doc = fitz.open(pdf_path)
    try:
        page_num = validate_page_number(doc, page_num)
        page = doc[page_num]

        drawings: List[Dict[str, Any]] = page.get_drawings()
        logger.info(f"Total vector objects: {len(drawings)}")

        # 1) Drawing-level filter first -> then aggregate by style
        stats: Dict[StyleKey, StyleAgg] = {}

        for d in drawings:
            key, items_count, seqno, rect = extract_style(d, width_round=width_round)

            if not match_drawing_filters(filters, key, items_count):
                continue

            agg = stats.get(key)
            if agg is None:
                agg = StyleAgg()
                stats[key] = agg
            agg.add(seqno, rect, items_count)

        # Summary
        unique_styles = len(stats)
        unique_types = sorted({k.obj_type for k in stats.keys()})
        unique_colors = sorted({k.color for k in stats.keys() if k.color is not None})

        print("\n=== STATISTICS SUMMARY ===")
        print(f"PDF: {pdf_path}")
        print(f"Page: {page_num} (1-based {page_num+1})")
        print(f"Total vector objects (page): {len(drawings)}")
        print(f"After drawing filters: {sum(a.count for a in stats.values())}")
        print(f"Unique object types (after): {len(unique_types)} ({', '.join(unique_types)})")
        print(f"Unique style combinations (after): {unique_styles}")
        print(f"Unique stroke colors (after): {len(unique_colors)}")
        if unique_colors:
            print("Color palette (first 12):", unique_colors[:12])

        # Active filters display
        print("\n=== DETAILED ANALYSIS ===")
        active = []
        if filters.width is not None:
            active.append(f"width≈{filters.width}±{filters.width_tol}")
        if filters.color is not None:
            active.append(f"color={filters.color}")
        if filters.fill is not None:
            active.append(f"fill={filters.fill}")
        if filters.obj_type is not None:
            active.append(f"type={filters.obj_type}")
        if filters.dashed is not None:
            active.append("dashed" if filters.dashed else "solid")
        if filters.drawing_items_eq is not None:
            active.append(f"items_eq={filters.drawing_items_eq}")
        if filters.drawing_items_min is not None:
            active.append(f"items_min={filters.drawing_items_min}")
        if filters.drawing_items_max is not None:
            active.append(f"items_max={filters.drawing_items_max}")
        if filters.min_count is not None:
            active.append(f"min_count={filters.min_count}")
        if filters.style_items_eq is not None:
            active.append(f"style_items_eq={filters.style_items_eq}")
        if filters.style_items_min is not None:
            active.append(f"style_items_min={filters.style_items_min}")
        if filters.style_items_max is not None:
            active.append(f"style_items_max={filters.style_items_max}")
        if filters.line_cap is not None:
            active.append(f"lineCap={filters.line_cap}")
        if filters.line_join is not None:
            active.append(f"lineJoin={filters.line_join}")
        if filters.even_odd is not None:
            active.append(f"evenOdd={filters.even_odd}")

        print("Active filters:", ", ".join(active) if active else "none")

        header = (
            f"{'Width':<12} | {'Color':<14} | {'Fill':<14} | {'Type':<4} | "
            f"{'Dashed':<6} | {'Count':<6} | {'Items[min/avg/max]':<17} | "
            f"{'Seqno':<6} | {'LineCap':<11} | {'LineJoin':<8} | {'EvenOdd':<7}"
        )
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        items: List[Tuple[StyleKey, StyleAgg]] = list(stats.items())

        if sort_by == "width":
            items.sort(key=lambda kv: (kv[0].width is None, kv[0].width if kv[0].width is not None else 0.0))
        else:
            items.sort(key=lambda kv: kv[1].count, reverse=True)

        exported_rows: List[Dict[str, Any]] = []
        shown_styles = 0
        shown_drawings = 0

        for key, agg in items:
            # style-level filters (min_count, optional style_items_*)
            if not match_style_filters(filters, key, agg):
                continue

            dashed_flag = is_dashed(key.dashes)

            w_str = f"{key.width:.6f}" if isinstance(key.width, float) else str(key.width)
            c_str = str(key.color) if key.color is not None else "None"
            f_str = str(key.fill) if key.fill is not None else "None"
            lc_str = str(key.line_cap) if key.line_cap is not None else "None"
            lj_str = f"{key.line_join:.3f}" if isinstance(key.line_join, float) else str(key.line_join)

            items_min = agg.items_min if agg.items_min is not None else 0
            items_max = agg.items_max if agg.items_max is not None else 0
            items_avg = agg.items_avg
            items_str = f"{items_min}/{items_avg:.1f}/{items_max}"

            print(
                f"{w_str:<12} | {c_str:<14} | {f_str:<14} | {key.obj_type:<4} | "
                f"{('Y' if dashed_flag else 'N'):<6} | {agg.count:<6} | {items_str:<17} | "
                f"{str(agg.example_seqno):<6} | {lc_str:<11} | {lj_str:<8} | {str(key.even_odd):<7}"
            )

            shown_styles += 1
            shown_drawings += agg.count

            exported_rows.append(
                {
                    "width": key.width,
                    "color": key.color,
                    "fill": key.fill,
                    "type": key.obj_type,
                    "dashes": key.dashes,
                    "dashed": dashed_flag,
                    "count": agg.count,
                    "items_min": agg.items_min,
                    "items_avg": agg.items_avg,
                    "items_max": agg.items_max,
                    "seqno": agg.example_seqno,
                    "lineCap": key.line_cap,
                    "lineJoin": key.line_join,
                    "even_odd": key.even_odd,
                    "rect": rect_to_list(agg.example_rect),
                }
            )

        print("-" * len(header))
        print(f"\nShown styles: {shown_styles}, drawings: {shown_drawings}")

        # Export
        if export_format:
            fmt = export_format.lower()
            if fmt == "png":
                out_path = export_path or default_export_path(pdf_path, page_num, "styles.png")
                export_marked_png(
                    page=page,
                    drawings=drawings,
                    filters=filters,
                    export_path=out_path,
                    pdf_path=pdf_path,
                    page_num=page_num,
                    zoom=png_zoom,
                    max_boxes=png_max_boxes,
                    show_labels=png_labels,
                    width_round=width_round,
                )
            elif fmt == "json":
                out_path = export_path or default_export_path(pdf_path, page_num, "styles.json")
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as fobj:
                    json.dump(exported_rows, fobj, indent=2, ensure_ascii=False, default=to_jsonable)
                logger.info(f"Exported JSON: {out_path}")
            elif fmt == "csv":
                out_path = export_path or default_export_path(pdf_path, page_num, "styles.csv")
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", newline="", encoding="utf-8") as fobj:
                    fieldnames = list(exported_rows[0].keys()) if exported_rows else [
                        "width","color","fill","type","dashes","dashed","count",
                        "items_min","items_avg","items_max","seqno","lineCap","lineJoin","even_odd","rect"
                    ]
                    writer = csv.DictWriter(fobj, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in exported_rows:
                        writer.writerow(row)
                logger.info(f"Exported CSV: {out_path}")
            elif fmt == "json_raw":
                out_path = export_path or default_export_path(pdf_path, page_num, "styles_raw.json")
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)

                raw: List[Any] = []
                for d in drawings:
                    key, items_count, _, _ = extract_style(d, width_round=width_round)
                    if match_drawing_filters(filters, key, items_count):
                        raw.append(to_jsonable(d))

                with open(out_path, "w", encoding="utf-8") as fobj:
                    json.dump(raw, fobj, indent=2, ensure_ascii=False)
                logger.info(f"Exported JSON_RAW: {out_path}")
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

    finally:
        doc.close()


# -----------------------------
# CLI
# -----------------------------
def parse_rgb_tuple(s: str) -> Optional[RGB]:
    if not s:
        return None
    try:
        v = ast.literal_eval(s)
        if isinstance(v, (list, tuple)) and len(v) == 3:
            r, g, b = (int(v[0]), int(v[1]), int(v[2]))
            return (r, g, b)
    except Exception:
        return None
    return None


def parse_arguments() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze vector drawing styles on a PDF page (PyMuPDF).",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("pdf_path", help="Path to the PDF file")
    p.add_argument("--page", type=int, default=0, help="0-based page number (default: 0)")

    p.add_argument("--export", choices=["json", "json_raw", "csv", "png"], help="Export format")
    p.add_argument("--export-path", help="Custom export path (file)")

    # Style-like filters
    p.add_argument("--filter-width", type=float, help="Filter by stroke width (approx)")
    p.add_argument("--width-tol", type=float, default=0.01, help="Tolerance for --filter-width (default: 0.01)")
    p.add_argument("--filter-color", help="Filter by stroke color, e.g. '(0,0,0)'")
    p.add_argument("--filter-fill", help="Filter by fill color, e.g. '(255,255,153)'")
    p.add_argument("--filter-type", help="Filter by drawing type, e.g. 's' or 'fs'")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--filter-dashed", action="store_true", help="Only dashed drawings")
    g.add_argument("--filter-solid", action="store_true", help="Only solid drawings")
    p.add_argument("--filter-linecap", help="Filter by lineCap, e.g. '(0,0,0)' or '(1,1,1)'")
    p.add_argument("--filter-linejoin", type=float, help="Filter by lineJoin, e.g. 0.0 or 1.0")
    p.add_argument("--filter-evenodd", choices=["true", "false"], help="Filter by even_odd flag")

    # Drawing-level items filter (len(items) pro drawing) ✅
    p.add_argument("--filter-items-count", type=int, help="Only drawings with len(items) == VALUE")
    p.add_argument("--filter-items-min", type=int, help="Only drawings with len(items) >= VALUE")
    p.add_argument("--filter-items-max", type=int, help="Only drawings with len(items) <= VALUE")

    # Style-level filters (after aggregation)
    p.add_argument("--min-count", type=int, help="Only show styles with at least this count (after drawing filters)")
    p.add_argument("--style-items-count", type=int, help="Only styles with items_min=items_max=VALUE (after aggregation)")
    p.add_argument("--style-items-min", type=int, help="Only styles with items_min >= VALUE (after aggregation)")
    p.add_argument("--style-items-max", type=int, help="Only styles with items_max <= VALUE (after aggregation)")

    # Output tuning
    p.add_argument("--sort-by", choices=["count", "width"], default="count", help="Sort table by count or width")
    p.add_argument("--width-round", type=int, default=12, help="Rounding digits for width grouping (default: 12)")

    # PNG options
    p.add_argument("--png-zoom", type=float, default=2.0, help="PNG render zoom (default: 2.0)")
    p.add_argument("--png-max-boxes", type=int, default=5000, help="Safety limit of drawn boxes (default: 5000)")
    p.add_argument("--png-labels", action="store_true", help="Draw small index labels on boxes")

    # Logging
    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING...)")
    p.add_argument("--log-file", default="pdf_analysis.log", help="Log file path")

    return p.parse_args()


def build_filters(args: argparse.Namespace) -> Filters:
    f = Filters()

    if args.filter_width is not None:
        f.width = float(args.filter_width)
        f.width_tol = float(args.width_tol)

    if args.filter_color:
        c = parse_rgb_tuple(args.filter_color)
        if c is None:
            logger.warning(f"Invalid --filter-color: {args.filter_color}")
        else:
            f.color = c

    if args.filter_fill:
        fc = parse_rgb_tuple(args.filter_fill)
        if fc is None:
            logger.warning(f"Invalid --filter-fill: {args.filter_fill}")
        else:
            f.fill = fc

    if args.filter_type:
        f.obj_type = str(args.filter_type)

    if args.filter_dashed:
        f.dashed = True
    elif args.filter_solid:
        f.dashed = False

    if args.filter_linecap:
        lc = parse_rgb_tuple(args.filter_linecap)
        if lc is None:
            logger.warning(f"Invalid --filter-linecap: {args.filter_linecap}")
        else:
            f.line_cap = lc

    if args.filter_linejoin is not None:
        f.line_join = float(args.filter_linejoin)

    if args.filter_evenodd:
        f.even_odd = True if args.filter_evenodd == "true" else False

    # Drawing-level items ✅ (dein use-case)
    if args.filter_items_count is not None:
        f.drawing_items_eq = int(args.filter_items_count)
    if args.filter_items_min is not None:
        f.drawing_items_min = int(args.filter_items_min)
    if args.filter_items_max is not None:
        f.drawing_items_max = int(args.filter_items_max)

    # Style-level filters (after aggregation)
    if args.min_count is not None:
        f.min_count = int(args.min_count)
    if args.style_items_count is not None:
        f.style_items_eq = int(args.style_items_count)
    if args.style_items_min is not None:
        f.style_items_min = int(args.style_items_min)
    if args.style_items_max is not None:
        f.style_items_max = int(args.style_items_max)

    return f


if __name__ == "__main__":
    """
    Ordner mit PDFs:
        C:\\Users\\randanplan\\Dropbox\\Arbeit\\BMP 2025\\9 Neuss-Krefeld
        C:\\Users\\randanplan\\Dropbox\\Arbeit\\BMP 2025\\7 Heinsberg
    Beispiel PDF:
        C:\\Users\\randanplan\\Dropbox\\Arbeit\\BMP 2025\\9 Neuss-Krefeld\\4539_Viersen_0015_53_57.PDF
    Beispiel:
        python scripts/analyze_pdf_styles.py C:\\Users\\randanplan\\Dropbox\\Arbeit\\BMP 2025\\9 Neuss-Krefeld\\4539_Viersen_0015_53_57.PDF
        python scripts/analyze_pdf_styles.py "C:\\Users\\randanplan\\Dropbox\\Arbeit\\BMP 2025\\9 Neuss-Krefeld\\4539_Viersen_0015_53_57.PDF" --filter-items-count 120 --export png --png-labels --export-path "samples/4539_Viersen_0015_53_57_styles.png"
        
    """
    args = parse_arguments()
    logger = setup_logging(args.log_level, args.log_file)

    filters = build_filters(args)
    analyze_pdf_styles(
        pdf_path=args.pdf_path,
        page_num=args.page,
        export_format=args.export,
        export_path=args.export_path,
        filters=filters,
        width_round=args.width_round,
        sort_by=args.sort_by,
        png_zoom=args.png_zoom,
        png_max_boxes=args.png_max_boxes,
        png_labels=args.png_labels,
    )