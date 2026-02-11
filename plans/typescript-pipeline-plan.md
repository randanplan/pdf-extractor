# Architektur-Plan: TypeScript CLI Pipeline für PDF-Extraktion

## Übersicht

Dieser Plan beschreibt die Entwicklung einer TypeScript-basierten CLI-Pipeline zur Extraktion und Verarbeitung von Informationen aus PDF-Vegetationspflegeplänen.

## Optionen-Vergleich

### Option A: Hybrid (Python Extraktion + TypeScript Processing)

| Aspekt | Python (PyMuPDF) | TypeScript |
|--------|------------------|------------|
| PDF-Parsing | ✅ Vollständig | ⚠️ Limitiert |
| Vektor-Extraktion | ✅ Stabil | ⚠️ Komplex |
| Text-Extraktion | ✅ Robust | ✅ Gut |
| Performance | ✅ Schnell | ✅ Gut |
| Wartbarkeit | ⚠️ Zwei Sprachen | ✅ Einheitlich |

### Option B: Vollständig TypeScript

| Aspekt | pdf-lib | pdfjs-dist |
|--------|---------|------------|
| Text-Extraktion | ⚠️ Basic | ✅ Vollständig |
| Vektor-Grafiken | ⚠️ Schreiben nur | ⚠️ Rendering-Fokus |
| Geometrie-Zugriff | ⚠️ Limitiert | ⚠️ Limitiert |
| Community | Mittel | Groß |

---

## Empfohlene Architektur: Option A (Hybrid)

```text
┌─────────────────────────────────────────────────────────────────┐
│                      CLI Interface (TypeScript)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  extract    │  │  detect     │  │  export     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Python Bridge (Python-Skripte)                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ get_drawings()  │  │ get_text()      │  │ analyze_pdf.py  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  PyMuPDF (PDF)  │
                    └─────────────────┘
```

## Pipeline-Stufen

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  INPUT   │───▶│ EXTRACT  │───▶│ PROCESS  │───▶│  OUTPUT  │
│  (PDF)   │    │  (Py)    │    │   (TS)   │    │ (JSON/   │
│          │    │          │    │          │    │ GeoJSON) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Stufe 1: INPUT

- **Eingabe**: PDF-Dateien (Vegetationspflegepläne)
- **Ort**: `input/` Verzeichnis oder CLI-Argument

### Stufe 2: EXTRACT (Python)

- **Skript**: `scripts/analyze_pdf_styles.py` (bestehend)
- **Output**: JSON mit:
  - `drawings`: Alle Vektorelemente (Mittellinie, Außenlinien, Masten, etc.)
  - `text`: Extrahierte Textelemente mit Position
  - `metadata`: Seiten-Info, Dimensionen

### Stufe 3: PROCESS (TypeScript)

- **Filterung**: Styles-Clustern (Farbe, Breite, Linienart)
- **Merging**: Segmente zu Polylines zusammenfassen
- **Klassifizierung**: Trassen-Elemente erkennen
- **Feature-Linking**: Masten → Achse, Maßnahmen → Schutzstreifen

### Stufe 4: OUTPUT

- **JSON**: Strukturiertes Datenmodell
- **GeoJSON**: Für GIS-Import (Punkte/Linien/Polygone)
- **Debug-PNG**: Visualisierung mit Overlays

---

## TypeScript Projekt-Struktur

```text
src/
├── cli/
│   ├── index.ts           # Haupt-CLI-Einstiegspunkt
│   ├── commands/
│   │   ├── extract.ts     # Python-Skripte aufrufen
│   │   ├── detect.ts       # Feature-Erkennung
│   │   └── export.ts       # Export-Funktionen
│   └── utils/
│       ├── file.ts        # Datei-Operationen
│       └── subprocess.ts  # Python-Bridge
├── core/
│   ├── models/
│   │   ├── drawing.ts     # Vektor-Datenmodell
│   │   ├── text.ts        # Text-Datenmodell
│   │   └── feature.ts     # Erkannte Features
│   ├── filters/
│   │   ├── style-filter.ts
│   │   └── dimension-filter.ts
│   ├── merging/
│   │   ├── segment-graph.ts
│   │   └── polyline.ts
│   └── detection/
│       ├── axis-detector.ts
│       ├── edge-detector.ts
│       ├── mast-detector.ts
│       └── measure-detector.ts
├── export/
│   ├── json-exporter.ts
│   ├── geojson-exporter.ts
│   └── debug-renderer.ts
└── types/
    └── index.ts
```

---

## Daten-Schema (TypeScript Interfaces)

### Koordinatensystem

- **PDF-Koordinaten**: Ursprung links unten (PyMuPDF-Standard)
- **Einheit**: Punkte (Points), 72 Punkte = 1 Zoll
- **Y-Achse**: Nach oben wachsend

### Geometrie-Typen

```typescript
interface Point {
  x: number;
  y: number;
}

interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

interface Polyline {
  type: 'polyline';
  points: Point[];
}

interface Polygon {
  type: 'polygon';
  points: Point[];
  closed: boolean; // true für geschlossene Polygone
}

interface Circle {
  type: 'circle';
  center: Point;
  radius: number;
}

// Union-Typ für alle Geometrien
type Geometry = Polyline | Polygon | Circle;
```

### RGB-Farbtyp

```typescript
interface RGB {
  r: number; // 0-255
  g: number; // 0-255
  b: number; // 0-255
}
```

### Drawing-Schnittstelle

```typescript
interface Drawing {
  /** eindeutige ID für das Drawing */
  id: string;
  /** Seitennummer (0-basiert) */
  pageId: number;
  /** Bounding Box */
  bbox: Rect;
  /** Pfad-Elemente: [['l', x1, y1, x2, y2], ...] */
  items: DrawingItem[];
  /** Zeichnungsstil */
  style: Style;
  /** Art des Drawings */
  kind: DrawingKind;
  /** PDF-Objekt-ID (optional) */
  objectId?: string;
  /** Layer-Name (optional) */
  layer?: string;
}

interface DrawingItem {
  /** Befehlstyp: 'l'=Linie, 'c'=Kurve, 'h'=Horizontal, 'v'=Vertikal */
  type: 'l' | 'c' | 'h' | 'v';
  /** Koordinaten je nach Befehl */
  coords: number[];
}
```

### Style-Schnittstelle

```typescript
interface Style {
  /** Strichfarbe */
  color: RGB;
  /** Strichbreite in Punkten */
  width: number;
  /** Linienenden: [start, end, dash] */
  lineCap: [number, number, number];
  /** Eckverbindung: 0=miter, 1=round, 2=bevel */
  lineJoin: number;
  /** Dash-Pattern: [dash, gap, ...] */
  dashes?: number[];
  /** Füllfarbe (für gefüllte Shapes) */
  fill?: RGB;
  /** Transparenz: 0-1 */
  opacity?: number;
}
```

### DrawingKind - Drawing-Typen

```typescript
type DrawingKind =
  | 'axis'           // Trassen-Mittellinie (Leitungsachse)
  | 'edge'           // Trassen-Außenlinien (Schutzstreifen-Begrenzung)
  | 'mast'           // Mast-Symbol (Quadrat)
  | 'dimension'      // Bemaßung (Schutzstreifen-Breite)
  | 'dimension-line' // Maßlinie (Teil der Bemaßung)
  | 'dimension-text' // Maßzahl (Text der Bemaßung)
  | 'leader'         // Verbindungslinie (LeaderLine)
  | 'arrow'          // Pfeillinie
  | 'target'         // Ziel-Geometrie (Polygon/Path/Circle)
  | 'box'            // Maßnahmen-Box (gelb gefüllt)
  | 'border'         // Rahmen/Umrandung
  | 'other';         // Sonstige Elemente
```

### Text-Schnittstelle

```typescript
interface TextElement {
  /** eindeutige ID */
  id: string;
  /** Seitennummer */
  pageId: number;
  /** Bounding Box */
  bbox: Rect;
  /** Textinhalt */
  text: string;
  /** Textrichtung: [dx, dy] */
  dir: [number, number];
  /** Schriftgröße */
  size: number;
  /** Schriftfarbe */
  color: RGB;
  /** Font-Name */
  font: string;
  /** Font-Flags */
  flags: number;
}
```

### Feature-Schnittstelle

```typescript
type FeatureType =
  | 'trassen-achse'
  | 'trassen-rand-links'
  | 'trassen-rand-rechts'
  | 'schutzstreifen'
  | 'mast'
  | 'masz-band'
  | 'massnahme-flaeche'
  | 'massnahme-pfad'
  | 'massnahme-kreis'
  | 'verbindungslinie'
  | 'ziel-polygon'
  | 'ziel-pfad'
  | 'ziel-kreis';

interface Feature {
  /** eindeutige ID */
  id: string;
  /** Feature-Typ */
  type: FeatureType;
  /** Geometrie */
  geometry: Geometry;
  /** Zusätzliche Eigenschaften */
  properties: FeatureProperties;
  /** Konfidenz: 0-1 */
  confidence: number;
  /** Quell-Drawing-IDs */
  sourceIds: string[];
}

interface FeatureProperties {
  /** Stationierung (bei Trassen-Elementen) */
  chainage?: number;
  /** Links/Rechts (bei Schutzstreifen) */
  side?: 'left' | 'right' | 'center';
  /** Maßnahmen-Nummer (bei Maßnahmen) */
  measureId?: string;
  /** Text-Inhalt (bei Bemaßung) */
  text?: string;
  /** Breite in Metern (bei Schutzstreifen) */
  width?: number;
  /** Zusätzliche Metadaten */
  [key: string]: unknown;
}
```

### Pipeline-Output-Schnittstelle

```typescript
interface PipelineOutput {
  /** Verarbeitungsdatum */
  timestamp: string;
  /** Quell-PDF */
  sourceFile: string;
  /** Verarbeitete Seiten */
  pages: PageResult[];
  /** Erkannte Features */
  features: Feature[];
  /** Statistiken */
  stats: PipelineStats;
}

interface PageResult {
  pageId: number;
  width: number;
  height: number;
  drawingsCount: number;
  textCount: number;
}

interface PipelineStats {
  totalDrawings: number;
  totalText: number;
  featuresByType: Record<FeatureType, number>;
  processingTime: number;
}
```

---

## CLI-Befehle

```bash
# PDF extrahieren (ruft Python-Skripte auf)
pdf-extractor extract input.pdf -o output/

# Features erkennen (TypeScript)
pdf-extractor detect extracted.json -o features.json

# Exportieren (GeoJSON/Debug)
pdf-extractor export features.json --format geojson
pdf-extractor export features.json --format debug-png

# Vollständiger Workflow
pdf-extractor process input.pdf -o result/
```

---

## Nächste Schritte

1. **Python Bridge implementieren** - Subprocess-Kommunikation
2. **TypeScript Datenmodelle definieren** - core/models/
3. **Filter-Logik portieren** - Python-Filter → TypeScript
4. **Merging-Algorithmus implementieren** - Segment-Graph
5. **CLI-Befehle implementieren** - Commander/Gluegun
6. **Export-Funktionen** - JSON/GeoJSON/Debug-PNG
