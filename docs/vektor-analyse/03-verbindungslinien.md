<!-- file: 03-verbindungslinien.md -->
# Verbindungslinien (LeaderLine + ArrowLine)

Verbindungslinien bestehen aus:
* `LeaderLine`: eine Linie von Box zu Zielpunkt
* `ArrowLine`: Pfeilspitze am Zielpunkt (zwei Linien)

## 3.1 LeaderLine

### Filterdefinition
```python
import math

LEADER_LINE_WIDTH = 2.834630012512207
LEADER_LINE_COLOR = (0, 0, 0)
LEADER_LINE_COUNT = 1

LEADER_LINE_FILTER = {
    "type": "s",
    "fill": None,
    "color": lambda c: get_color_value(c) == LEADER_LINE_COLOR,
    "width": lambda w: math.isclose(w, LEADER_LINE_WIDTH, abs_tol=0.1),
    "items": lambda items: len(items) == LEADER_LINE_COUNT
}
```

## 3.2 ArrowLine

### Filterdefinition
```python
import math

ARROW_LINE_WIDTH = 2.834630012512207
ARROW_LINE_COLOR = (0, 0, 0)
ARROW_LINE_ITEMS_COUNT = 2

ARROW_PATH_FILTER = {
    "type": "s",
    "fill": None,
    "color": lambda c: get_color_value(c) == ARROW_LINE_COLOR,
    "width": lambda w: math.isclose(w, ARROW_LINE_WIDTH, abs_tol=0.1),
    "items": lambda items: len(items) == ARROW_LINE_ITEMS_COUNT
}
```