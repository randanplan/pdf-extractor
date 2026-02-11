<!-- file: 05-trasse-masten-und-schutzstreifen.md -->
# Trasse: Masten, Mittellinie, Außenlinien, Bemaßung

## 5. Mast-Symbol

Quadrat aus 4 Linien; Größe und Rotation variabel.

```python
import math

MAST_SYMBOL_WIDTH = 0.7086600065231323
MAST_SYMBOL_COLOR = (0, 0, 0)
MAST_SYMBOL_ITEMS_COUNT = 4

MAST_SYMBOL_FILTER = {
    "type": "s",
    "color": lambda c: get_color_value(c) == MAST_SYMBOL_COLOR,
    "width": lambda w: math.isclose(w, MAST_SYMBOL_WIDTH, abs_tol=0.1),
    "items": lambda items: len(items) == MAST_SYMBOL_ITEMS_COUNT and all(item[0] == 'l' for item in items)
}
```

## 6. Trassen-Mittellinie / Leitungsachse

Mittellinie aus vielen Segmenten, die zusammengefasst werden.

### 6.1 Filter: segmentierte Mittellinie
```python
import math

AXIS_COLOR = (0, 0, 0)
AXIS_WIDTH = 0.9921200275421143
AXIS_WIDTH_TOL = 0.08

TRASSEN_MITTELLINIE_SEGMENT_FILTER = {
    "type": "s",
    "fill": None,
    "color": lambda c: get_color_value(c) == AXIS_COLOR,
    "width": lambda w: math.isclose(w, AXIS_WIDTH, abs_tol=AXIS_WIDTH_TOL),
    "lineCap": lambda lc: tuple(lc) == (0, 0, 0),
    # "lineJoin": lambda lj: math.isclose(lj, 0.0, abs_tol=1e-6),
    "items": lambda items: len(items) == 1 and items[0][0] == "l",
}
```

### 6.2 Post-Processing: Mittellinie aus Segmenten zusammenfassen
1. Segmente nach Endpunktnähe clustern (eps z.B. 3–8 px)
2. innerhalb eines Clusters nach Richtung ordnen und verbinden
3. optional: Mast-Symbole als Anker nutzen (Achse durch/nahe Mastzentrum)

## 7. Trassen-Außenlinien (Schutzstreifen-Begrenzung)

Zwei lange Begrenzungslinien (links/rechts), meist durchgezogen und parallel zur Mittellinie.

### 7.1 Filter: segmentierte Außenlinie
```python
import math

TRASSE_EDGE_COLOR = (95, 95, 95)
TRASSE_EDGE_WIDTH = 0.5102300047874451
TRASSE_EDGE_WIDTH_TOL = 0.06

TRASSEN_AUSSENLINIE_FILTER = {
    "type": "s",
    "fill": None,
    "color": lambda c: get_color_value(c) == TRASSE_EDGE_COLOR,
    "width": lambda w: math.isclose(w, TRASSE_EDGE_WIDTH, abs_tol=TRASSE_EDGE_WIDTH_TOL),
    "lineCap": lambda lc: tuple(lc) == (0, 0, 0),
    # "lineJoin": lambda lj: math.isclose(lj, 0.0, abs_tol=1e-6),
    "items": lambda items: len(items) >= 10 and all(it[0] == "l" for it in items),
}
```

### 7.2 Post-Processing: Außenlinie aus Segmenten zusammenfassen
1. Segment-Merging wie bei Mittellinie
2. Links/Rechts trennen: signierten Abstand zur Achse verwenden
3. Optional: Schutzstreifen-Fläche als Polygon erzeugen (Außenlinien + Endkappen)

## 8. Schutzstreifen-Bemaßung (Breitenangaben)

Bemaßung besteht aus mehreren separaten Items (nicht „ein Drawing = eine Bemaßung“).

Bestandteile:
* Maßlinie(n): durchgezogen, typischerweise im rechten Winkel zur Leitungs-/Mittellinie
* Hilfs-/Bezugslinien + Pfeile/Endmarken
* Text (z.B. 40.00, 80.00) parallel zur Maßlinie (also ebenfalls quer zur Achse)

### 8.1 Filter: Kandidaten-Items (Linienanteile der Bemaßung)

```python
import math

SCHUTZ_DIM_COLOR = (0, 0, 0)
SCHUTZ_DIM_WIDTH = 0.5102300047874451
SCHUTZ_DIM_WIDTH_TOL = 0.06

SCHUTZ_DIM_ITEM_FILTER = {
    "type": "s",
    # "fill": None,
    "color": lambda c: get_color_value(c) == SCHUTZ_DIM_COLOR,
    "width": lambda w: math.isclose(w, SCHUTZ_DIM_WIDTH, abs_tol=SCHUTZ_DIM_WIDTH_TOL),
    "items": lambda items: len(items) >= 1 and all(it[0] == "l" for it in items),
}
```

### 8.2 Gruppierung: mehrere Items → eine Bemaßung

1. Alle Kandidaten-Items sammeln
2. Spatial Clustering über rect-Nähe/Overlap (Cluster = eine Bemaßung)
3. Pro Cluster: Haupt-Maßlinie bestimmen (längstes Segment)
4. Orientierung prüfen:
    * Hauptlinie ~ 90° zur Achs-Tangente
    * Text-Spans in der Nähe suchen, parallel zur Maßlinie

### 8.3 Text-Findung (parallel zur Maßlinie)

```python
import re

DIM_VALUE_RE = re.compile(r"^\d+(\.\d+)?$")  # z.B. 40.00

def is_text_parallel_to_dim(span_dir, dim_dir, tol_deg=10.0):
    ang = angle_between(span_dir, dim_dir)
    ang = min(ang, 180 - ang)
    return ang <= tol_deg

def find_dim_text(spans, cluster_rect, dim_dir, max_dist=40.0):
    cx = (cluster_rect.x0 + cluster_rect.x1) / 2
    cy = (cluster_rect.y0 + cluster_rect.y1) / 2

    best, best_d2 = None, 1e18
    for sp in spans:
        txt = (sp.get("text") or "").strip()
        if not DIM_VALUE_RE.match(txt):
            continue

        d = sp.get("dir")
        if d and not is_text_parallel_to_dim((d[0], d[1]), dim_dir):
            continue

        r = pymupdf.Rect(sp["bbox"])
        sx = (r.x0 + r.x1) / 2
        sy = (r.y0 + r.y1) / 2
        d2 = (sx - cx)**2 + (sy - cy)**2
        if d2 < best_d2 and d2 <= (max_dist**2):
            best_d2, best = d2, txt

    return best
```

