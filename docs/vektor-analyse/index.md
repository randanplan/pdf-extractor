# Trassenmanagementplan – Vektorelement-Analyse (Index)

Diese Dokumentation beschreibt die Erkennung und Extraktion relevanter Vektor- und Text-Elemente aus Ökologischen Trassenmanagementplänen (PDF) mittels `PyMuPDF`.

## Motivation & Problemstellung

Die manuelle Analyse komplexer Ökologischer Trassenmanagementpläne in PDF-Form ist zeitaufwändig und fehleranfällig. Dieses Toolset bietet eine automatisierte Lösung zur präzisen Identifizierung und Extraktion spezifischer geometrischer und textueller Informationen, die für weitere Analysen oder die Digitalisierung von Plänen unerlässlich sind.

## Grundlagen & Schlüsselkonzepte

*   **Vektorelemente:** Geometrische Formen wie Linien, Kreise, Polygone, die durch Pfadoperationen in der PDF definiert sind. Im Gegensatz zu Rastergrafiken sind sie skalierbar ohne Qualitätsverlust.
*   **`PyMuPDF`:** Eine leistungsstarke Python-Bibliothek zur Bearbeitung von PDF-Dokumenten, die den Zugriff auf die internen Strukturen von PDFs ermöglicht, einschließlich Vektorgrafiken und Text.

## Inhalte

1.  **Überblick & Ziele**
    → [`00-overview.md`](00-overview.md)
    *   *Umfasst die übergeordneten Ziele des Projekts und die Kernfunktionalitäten der Vektorelement-Analyse.*

2.  **Gemeinsame Helper / Utilities**
    → [`01-helpers.md`](01-helpers.md)
    *   *Beschreibt wiederverwendbare Funktionen und Klassen, die in mehreren Analysemodulen zum Einsatz kommen (z.B. Filterlogiken, Geometrie-Transformationen).*

3.  **Maßnahmen-Boxen & Text**
    (gelbe Boxen, Standard-Textfilter)
    → [`02-massnahmen-boxen-und-text.md`](02-massnahmen-boxen-und-text.md)
    *   *Fokus auf die Erkennung von rechteckigen "Maßnahmen-Boxen" (oft gelb hinterlegt) und der Extraktion des darin enthaltenen Textes für Maßnahmenkataloge.*

4.  **Verbindungslinien**
    (LeaderLine + ArrowLine)
    → [`03-verbindungslinien.md`](03-verbindungslinien.md)
    *   *Identifiziert und analysiert Linien, die Elemente miteinander verbinden, einschließlich Pfeillinien und Führungslinien, um Beziehungen zwischen Objekten herzustellen.*

5.  **Ziel-Geometrien**
    (TargetPolygon, TargetPath, TargetCircle)
    → [`04-zielgeometrien.md`](04-zielgeometrien.md)
    *   *Detaillierte Erläuterung der Erkennung und Klassifizierung spezifischer Zielgeometrien wie Polygone, Pfade und Kreise, die besondere Bedeutung in den Plänen haben.*

6.  **Trasse: Masten & Schutzstreifen**
    (Mast-Symbol, Trassen-Mittellinie/Leitungsachse, Trassen-Außenlinien, Schutzstreifen-Bemaßung)
    → [`05-trasse-masten-und-schutzstreifen.md`](05-trasse-masten-und-schutzstreifen.md)
    *   *Konzentriert sich auf die Extraktion von Elementen, die direkt mit der Trasse in Verbindung stehen: Mastpositionen, die zentrale Leitungsachse, äußere Begrenzungslinien und Bemaßungen von Schutzstreifen.*

## Schnellstart (Empfohlen)

1.  `00-overview.md` lesen (Kontext + Zielsetzung)
2.  `01-helpers.md` in dein Projekt übernehmen
3.  Je nach Bedarf:
    *   Maßnahmenkataster: `02` + `03` + `04`
    *   Trassengeometrie: `05`

## Voraussetzungen & Installation

Dieses Toolset benötigt Python 3.8+ und die Bibliothek `PyMuPDF`.
Installation: `pip install PyMuPDF`

## Namenskonventionen

*   **Filter** sind als `*_FILTER` definiert und direkt auf die Output-Objekte von `page.get_drawings()` anwendbar.
*   Post-Processing-Schritte (Clustering/Merging) sind Bestandteil der Erkennungslogik, wenn Elemente aus vielen Segmenten bestehen (z.B. Mittellinie, Außenlinien, Bemaßung).