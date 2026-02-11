# Plan: TypeScript CLI Pipeline für PDF-Extraktion (PLAN v2)

## Übersicht

Dieser Plan beschreibt die Entwicklung einer Pipeline zur Extraktion von Informationen aus PDF‑Vegetationspflegeplänen für Hochspannungsleitungen. Die Architektur kombiniert Python (zuverlässige PDF-Extraktion) mit TypeScript (Detektion, Linking, Export, CLI).

---

## Ziel, Deliverables, Erfolgskriterien

### Ziel
Automatisierte Extraktion und Strukturierung von Trassen‑, Mast‑, Maßnahme‑ und Bemaßungs‑Elementen aus PDF-Plänen in standardisierte JSON/PNG‑Outputs.

### Deliverables
- CLI mit Befehlen `extract`, `detect`, `export`, `process`
- Stabiler Daten‑Contract (Raw + Derived + Schema‑Version)
- Detektions‑Pipeline (Kandidaten → Struktur → Linking)
- Export (JSON/PNG) + Debug‑Overlays
- Test- & Debug-Infrastruktur

### Erfolgskriterien (Definition of Done pro Phase)
1. **Extract**
   - Raw‑JSON entspricht Schema (`schemaVersion`)
   - Pro PDF: Drawings + Text + Metadata vollständig
   - Laufzeit ≤ X Sekunden/Seite (Ziel: 2–3s)
2. **Detect**
   - ≥ 90% Recall auf Referenz‑Masten (Gold‑PDFs)
   - Achsen erkennen + verknüpfte Außenlinien
   - Maßnahmen‑Box + Text korrekt verlinkt
3. **Export**
   - JSON validierbar
   - PNG‑Overlay vollständig, farbcodiert, beschriftet
4. **QA/Debug**
   - Pro Seite Report mit Stats + Fehlern
   - Visual Regression Tests über Debug‑PNG

---

## Architektur: Python + TypeScript Hybrid

### Optionen‑Vergleich

| Aspekt | Python (PyMuPDF) | TypeScript |
|--------|------------------|------------|
| PDF‑Parsing | ✅ Vollständig | ⚠️ Limitiert |
| Vektor‑Extraktion | ✅ Stabil | ⚠️ Komplex |
| Text‑Extraktion | ✅ Robust | ✅ Gut |
| Performance | ✅ Schnell | ✅ Gut |
| Wartbarkeit | ⚠️ Zwei Sprachen | ✅ Einheitlich |

### Empfohlene Architektur: Hybrid

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

### Pipeline‑Stufen

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  INPUT   │───▶│ EXTRACT  │───▶│ PROCESS  │───▶│  OUTPUT │
│  (PDF)   │    │  (Py)    │    │   (TS)   │    │ (JSON/PNG)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

- **INPUT**: PDF‑Dateien (Vegetationspflegepläne)
- **EXTRACT**: `scripts/analyze_pdf_styles.py` → Raw‑JSON
- **PROCESS**: TypeScript (Filterung, Merging, Klassifizierung, Feature‑Linking)
- **OUTPUT**: JSON, PNG + Debug

### CLI‑Befehle

```bash
pdf-extractor extract input.pdf -o output/     # Python: PDF → JSON
pdf-extractor detect extracted.json -o features.json  # TS: Erkennung
pdf-extractor export features.json --format json  # TS: Export
pdf-extractor export features.png --format png  # TS: PNG-Export
pdf-extractor process input.pdf -o result/     # All‑in‑One
```

---

## 1. Stabiler Daten‑Contract

### Raw vs Derived trennen

| Raw | Derived |
|-----|---------|
| Original Drawing | Feature‑Geometrie (Polyline/Polygon) |
| `pageId`, `bbox`, `items` | `type`, `geometry`, `properties` |
| `style` (color/width/dashes) | `properties` |

### Schema‑Versionierung

```typescript
interface ProducerInfo {
  name: string; // z. B. "pdf-extractor"
  version: string; // semver
  gitCommit?: string;
  buildTime?: string; // ISO
}

interface PipelineOutput {
  schemaVersion: '1.0.0';
  producer: ProducerInfo;
  timestamp: string;
  pdf: PDFResult;
  features: Feature[];
  stats: PipelineStats;
}
```

### Python ↔ TS Bridge Contract

**I/O‑Konventionen**
- Python liefert JSON via Datei (Pfad als CLI‑Argument) oder stdout (Flag `--stdout`)
- Exit Codes: `0=ok`, `10=invalid-pdf`, `20=extract-error`, `30=unexpected`
- Fehlerobjekt (`errors[]`) pro Seite:

```typescript
interface PipelineError {
  code: string;
  message: string;
  pageId?: number;
  context?: Record<string, unknown>;
}
```

- Timeout: Standard 60s pro PDF, CLI‑Flag `--timeout`
- Retries optional (`--retry 1`)

---

## 2. Daten‑Schema (TypeScript Interfaces)

### Koordinatensystem

- **PDF‑Koordinaten**: Ursprung links unten (PyMuPDF‑Standard)
- **Einheit**: Punkte (Points), 72 Punkte = 1 Zoll
- **Y‑Achse**: Nach oben wachsend

### Koordinaten‑Transformation (Architekturregel)

Alle Render‑/Debug‑Operationen nutzen zentrale Utilities (kein ad‑hoc Y‑Invert):

```typescript
function pdfToCanvas(p: Point, pageHeight: number): Point;
function canvasToPdf(p: Point, pageHeight: number): Point;
```

### Geometrie‑Typen

```typescript
interface Point {
  x: number;
  y: number;
}

type Line = {
  p1: Point;
  p2: Point;
};

type Curve = {
  p1: Point;
  p2: Point;
  cp: Point; // Kontrollpunkt für Quadratische Bezier‑Kurve
};

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
  closed: boolean;
}

interface Circle {
  type: 'circle';
  center: Point;
  radius: number;
}

type Geometry = Polyline | Polygon | Circle;
```

### RGB‑Farbtyp

```typescript
interface RGB {
  r: number; // 0-255
  g: number; // 0-255
  b: number; // 0-255
}
```

### Drawing‑Schnittstelle

```typescript
interface Drawing {
  id: string;
  pageId: number;
  bbox: Rect;
  items: DrawingItem[];
  style: Style;
  kind: DrawingKind;
  objectId?: string;
  layer?: string;
}

// Einzelnes Segment innerhalb eines Drawings
interface DrawingItem {
  type: 'line' | 'curve' | 'path' | 'rect' | 'circle';
  points: Point[]; // Linie=2, Curve=3, Rect=4, Circle=1+radius in props
  // TODO: Mapping-Tabelle PyMuPDF → DrawingItem
}
```

### Style‑Schnittstelle

```typescript
interface Style {
  color: RGB;
  width: number;
  lineCap: [number, number, number];
  lineJoin: number;
  dashes?: number[];
  fill?: RGB;
  opacity?: number;
}
```

### DrawingKind

```typescript
type DrawingKind =
  | 'axis'
  | 'edge'
  | 'mast'
  | 'measure'
  | 'massnahme-box'
  | 'massnahme-text'
  | 'unknown';
```

### Feature‑Schnittstellen

```typescript
type FeatureType =
  | 'trassen-mittellinie'
  | 'trassen-aussenlinie'
  | 'trassen-overlay'
  | 'mast'
  | 'mast-label'
  | 'massnahme'
  | 'massnahme-box'
  | 'massnahme-text'
  | 'massnahme-flaeche'
  | 'massnahme-pfad'
  | 'massnahme-kreis'
  | 'massnahme-pointer'
  | 'bemassung'
  | 'bemassung-linie'
  | 'bemassung-text'
  | 'bemassung-pfeil'
  | 'sonstiges';

interface FeatureBase<TType extends FeatureType, TProps> {
  id: string;
  type: TType;
  geometry: Geometry;
  properties: TProps;
  confidence: number;
  sourceIds: string[];
}

interface MastProperties {
  id?: string;
  line?: string;
  next?: string;
  prev?: string;
  label?: string;
  center?: Point;
  rotation?: number;
  size?: number;
  linkEvidence?: LinkEvidence[];
}

interface MassnahmeProperties {
  id?: string;
  type?: string;
  text?: string;
  linkEvidence?: LinkEvidence[];
}

interface BemassungProperties {
  id?: string;
  text?: string;
  line?: string;
  linkEvidence?: LinkEvidence[];
}

interface TrassenElementProperties {
  id?: string;
}

type Feature =
  | FeatureBase<'mast', MastProperties>
  | FeatureBase<'massnahme', MassnahmeProperties>
  | FeatureBase<'bemassung', BemassungProperties>
  | FeatureBase<'trassen-mittellinie', TrassenElementProperties>
  | FeatureBase<'trassen-aussenlinie', TrassenElementProperties>
  | FeatureBase<'trassen-overlay', TrassenElementProperties>
  | FeatureBase<'sonstiges', Record<string, unknown>>;
```

### Pipeline‑Output

```typescript
interface PDFResult {
  id: string;
  name: string;
  size: number;
  path: string;
  pageCount: number;
  pages: PageResult[];
  creationDate: string;
  updateDate: string;
  metadata: PDFMetadata;
}

interface PageResult {
  pageId: number;
  width: number;
  height: number;
  layout: 'portrait' | 'landscape';
  planType?: 'bmp' | 'standard';
}

interface PipelineStats {
  totalDrawings: number;
  totalText: number;
  featuresByType: Record<FeatureType, number>;
  processingTime: number;
}
```

---

## 3. Zwei‑Phasen‑Erkennung

### Phase A – Kandidaten (harte Merkmale)

Artikel: "Vektor‑Analyse der PDF‑Pläne" (`docs/vektor-analyse/`) – Filterregeln für harte Merkmale.

| Element | Farbe | Breite | Orientierung | Anzahl | Merkmale | Besonderheiten |
|---------|-------|--------|-------------|--------|----------|----------------|
<!-- TODO: Tabelle mit konkreten Werten aus docs/vektor-analyse/ ergänzen -->

### Phase B – Struktur (Soft‑Heuristiken)

- **Mast‑Achse**: Mittellinie + regelmäßige Abstände → Mast‑Kandidaten clustern
- **Maßnahmen**: Box + Text → Maßnahme‑Feature‑Linking
- **Bemaßung**: Linie + Text → Bemaßungs‑Feature‑Linking
- **Trassen‑Elemente**: Achse + Außenlinien → Trassen‑Feature‑Linking

---

## 4. Segment‑Merging (Graph‑basiert)

### Algorithmus‑Spezifikation (Minimum)

- **Knoten**: Segmente (Linie/Curve) + Metadaten (Style, Länge, Richtung)
- **Kanten**: Merge‑Kandidaten (Distanz < d, Winkel < θ, Style‑Ähnlichkeit)
- **Reihenfolge**:
  1. Collinear‑Merge (gleiche Richtung)
  2. Junction‑Handling (T‑Knoten)
  3. Pfad‑Rekonstruktion (Grad‑1 Endpunkte)
  4. Simplifizierung (Douglas‑Peucker, Mastnähe schützen)
- **Konfliktlösung**: höchster Merge‑Score gewinnt

---

## 5. Style‑Drift abfangen

Statt width‑Werte hart zu codieren: **pro PDF/Seite Style‑Clustering**.

```typescript
interface StyleGroup {
  style: Style;
  count: number;
  totalLength: number;
}

function clusterStyles(drawings: Drawing[]): StyleGroup[] {
  // Clustering: z. B. DBSCAN oder hierarchisch
  // Ähnlichkeit über Farb- und Breiten‑Toleranzen
}
```

---

## 6. Feature‑Linking

### Regelbasiertes Scoring

```typescript
interface LinkEvidence {
  rule: string;
  score: number;
  distance?: number;
  angle?: number;
  styleMatch?: boolean;
}
```

**Score = gewichtete Summe** aus Distanz, Orientierung, Topologie, Style. Mindestscore → Linking, sonst `sonstiges`.

---

## 7. Qualitätssicherung (Debug‑Modus)

**Debug‑Artefakt pro Seite:**

- PNG mit Overlays:
  - Achse = rot (dicke Linie)
  - Außenlinien = orange (normale Linie)
  - Bemaßung = magenta (Linie + Text)
  - Masten = cyan (Polygon + Labels)
  - Maßnahmen‑Geometrien = gelb (Polygon/Polyline/Circle)
  - Maßnahme‑Boxen = grün (Bounding Box)
  - Maßnahme‑Texte = blau (Bounding Box + Text)

- JSON‑Report pro Seite:
  - `axis`: Länge, Anzahl Segmente, Durchschnittsbreite
  - `masten`: Anzahl, Durchschnittsgröße
  - `massnahmen`: Anzahl, Typen, Größen/Längen/Stückzahlen
  - `bemassungen`: Anzahl, Durchschnittslänge, Text‑Statistiken
  - `sonstiges`: Anzahl, Typen, Style‑Statistiken

---

## 8. Observability & Tracing

- CLI‑Flags: `--verbose`, `--debug`, `--trace-json`
- Timings pro Stage (extract/detect/export)
- Zähler: verworfene Kandidaten + Grund

---

## 9. TypeScript Projekt‑Struktur

```text
src/
├── cli/
│   ├── index.ts
│   ├── commands/
│   │   ├── extract.ts
│   │   ├── detect.ts
│   │   └── export.ts
│   └── utils/
│       ├── subprocess.ts
│       ├── db.ts
│       └── file.ts
├── core/
│   ├── models/
│   ├── filters/
│   ├── merging/
│   └── detection/
├── export/
│   ├── json-exporter.ts
│   ├── png-exporter.ts
│   └── debug-renderer.ts
└── types/
    └── index.ts
```

---

## 10. Konfiguration statt Hardcoding

- `config/profiles/*.json` (z. B. pro Netzbetreiber)
- CLI‑Flags: `--profile`, `--tolerance-scale`

---

## 11. Teststrategie

- Unit‑Tests: Geometrie, Clustering, Scoring
- Golden‑Master: feste PDFs → erwartete JSON‑Outputs
- Visual Regression: Debug‑PNG
- Corpus mit schwierigen PDFs (Style‑Drift, schiefe Scans)

---

## 12. Roadmap (Lieferpakete)

1. **MVP 1**: extract + schema + basic detect (Mast/Achse)
2. **MVP 2**: Maßnahmen + Bemaßung + Linking
3. **MVP 3**: Export PNG + QA reports + tuning
4. **MVP 4**: Profilsystem + Performanceoptimierung

---

## 13. Nächste Schritte

1. **Python‑Bridge implementieren** (Subprocess + Error‑Handling)
2. **TypeScript Datenmodelle definieren**
3. **Filter‑Logik portieren**
4. **Merging‑Algorithmus implementieren**
5. **CLI‑Befehle implementieren**
6. **Export‑Funktionen** (JSON/PNG)
7. **Debug‑PNG Renderer**

---

## Letzte Aktualisierung

- **Datum**: 2026‑02‑11
- **Version**: 2.1 (PLAN v2 erweitert)
- **Quelldateien**: docs/PLAN.md, docs/todo.md, plans/typescript-pipeline-plan.md