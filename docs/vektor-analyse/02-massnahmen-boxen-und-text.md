<!-- file: 02-massnahmen-boxen-und-text.md -->
# Maßnahmen-Boxen und Text

## 1. Maßnahmen-Boxen

Gelb gefüllte Boxen mit Maßnahmenbeschreibung.

### Filterdefinition
```python
import math

BOX_FILL_COLOR = (255, 255, 153)  # #FFFF99
BOX_STROKE_COLOR = (153, 153, 0)  # #999900
BOX_STROKE_WIDTH = 0.39684998989105225
BOX_ITEMS_COUNT = 4  # vier Linien

BOX_FILTER = {
    "type": "fs",  # filled shape
    "fill": lambda f: get_color_value(f) == BOX_FILL_COLOR,
    "color": lambda c: get_color_value(c) == BOX_STROKE_COLOR,
    "width": lambda w: math.isclose(w, BOX_STROKE_WIDTH, abs_tol=0.1),
    "items": lambda items: len(items) == BOX_ITEMS_COUNT
}
2. Text-Elemente in der Maßnahmen-Box
Standardtext innerhalb der Box (horizontal, schwarz, nicht fett/italic).

Filterdefinition
import math
import pymupdf

TEXT_DIR = (1.0, 0.0)
TEXT_COLOR = (0.0, 0.0, 0.0)
TEXT_SIZE = 11.17548942565918

TEXT_FILTER = {
    "dir": lambda d: d == TEXT_DIR,
    "color": lambda c: get_color_value(c) == TEXT_COLOR,
    "flags": lambda f: (f & pymupdf.TEXT_FONT_BOLD) == 0 and (f & pymupdf.TEXT_FONT_ITALIC) == 0,
    "size": lambda s: math.isclose(s, TEXT_SIZE, abs_tol=0.1)
}
```
