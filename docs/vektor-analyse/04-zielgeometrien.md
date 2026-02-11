<!-- file: 04-zielgeometrien.md -->
# Ziel-Geometrien

Zielgeometrien sind die geometrischen Objekte, die Maßnahmen referenzieren (Linien, Polygone, Kreise).

## 4.1 TargetPolygon (Polygon-Linien)

```python
TARGET_POLYGON_LINE_WIDTH = 0.25512000918388367
TARGET_POLYGON_LINE_COLOR = (88, 88, 88)  # rgb(88,88,88)
```

## 4.2 TargetPath (Pfad-Linien)
```python
TARGET_PATH_LINE_WIDTH = 5.669260025024414
TARGET_PATH_LINE_COLOR = (0, 0, 127)  # dunkelblau
```

## 4.3 TargetCircle (Kreis aus 4 Kurven)
```python
import math

TARGET_CIRCLE_WIDTH = [0.7086600065231323, 1.0629899501800537]
TARGET_CIRCLE_COLOR = (0, 0, 0)
TARGET_CIRCLE_ITEMS_COUNT = 4

TARGET_CIRCLE_FILTER = {
    "type": "s",
    "color": lambda c: get_color_value(c) == TARGET_CIRCLE_COLOR,
    "width": lambda w: w in TARGET_CIRCLE_WIDTH,
    "items": lambda items: len(items) == TARGET_CIRCLE_ITEMS_COUNT and all(item[0] == 'c' for item in items)
}
```