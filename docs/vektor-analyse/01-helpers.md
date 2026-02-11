<!-- file: 01-helpers.md -->
# Helper (gemeinsame Utilities)

Diese Helper werden in mehreren Filtern referenziert.

```python
import math
import re

def get_color_value(c):
    # Erwartet RGB in 0-255 oder 0-1; normalisiert auf 0-255 (int)
    if c is None:
        return None
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        # Heuristik: floats 0..1
        if all(isinstance(x, (float, int)) for x in c[:3]) and max(c[:3]) <= 1.0:
            return tuple(int(round(x * 255)) for x in c[:3])
        return tuple(int(round(x)) for x in c[:3])
    return c

def parse_dashes(dashes_str: str) -> list[float]:
    # PyMuPDF: z.B. "[11.3386 2.8346 1.4173 2.8346] 0" oder "[] 0"
    if not dashes_str:
        return []
    m = re.search(r"\[(.*?)\]", dashes_str)
    if not m:
        return []
    inside = m.group(1).strip()
    if not inside:
        return []
    return [float(x) for x in inside.split() if x]

def path_length(items) -> float:
    total = 0.0
    for it in items:
        if it[0] != "l":
            continue
        p1, p2 = it[1], it[2]
        dx = (p2.x - p1.x)
        dy = (p2.y - p1.y)
        total += math.hypot(dx, dy)
    return total

def segment_dir(p1, p2):
    dx, dy = (p2.x - p1.x), (p2.y - p1.y)
    n = math.hypot(dx, dy) or 1.0
    return (dx / n, dy / n), math.hypot(dx, dy)

def angle_between(u, v):
    dot = max(-1.0, min(1.0, u[0]*v[0] + u[1]*v[1]))
    return math.degrees(math.acos(dot))
```
