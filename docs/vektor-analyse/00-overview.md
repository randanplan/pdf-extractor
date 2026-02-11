<!-- file: 00-overview.md -->
# Analyse von Vektorelementen aus Trassenmanagementplänen

Diese Dokumentation dient zur Analyse von Vektorelementen die typischerweise in **Ökologischen Trassenmanagementplänen** (PDF) vorkommen. Ziel ist es, die relevanten Inhalte automatisiert zu erkennen und als strukturierte Daten (z.B. GeoJSON/GIS) weiterzuverarbeiten.

## Bereiche der PDF-Dateien

* **Kartenbereich**
  * Amtliche Flurkarte (Parzellen, Wege, Ortsbezeichnungen)
  * Trassen-spezifische Layer
    * Leitungs-/Trassen-Mittellinie (Leitungsachse)
    * Trassen-Außenlinien (Schutzstreifen-Begrenzung)
    * Mast-Standorte (Quadrat-Symbole)
    * Maßnahmenpositionen (Flächen, Pfade, Kreise)
  * Informations-Layer
    * Maßnahmen-Boxen (gelbe Textboxen)
    * Verbindungslinien (LeaderLine + ArrowLine)

* **Informationsblock**
  * Kopfzeile (Projekt-/Blattnummer, Logo)
  * Leitungs-Informationen (Leitungsabschnitt, Mast von/bis)
  * Titelblock (Plantyp, Region, Maßstab)
  * Administrative Zuordnung (Gemarkung, Gemeinde, Kreis, Land)
  * Fußzeile/Revisionsblock (Dateiname/Referenz, Änderungsprotokoll)

## Koordinatenbereiche (Beispiel)

Koordinaten beziehen sich auf ein PDF-Koordinatensystem mit Ursprung links unten (z.B. PyMuPDF).

**Y-Grenzen**
* Obere Grenze: `14.2`
* Untere Grenze: `page.height - 13.9`

**X-Grenzen**
| Bereich | X-Start | X-Ende |
|---|---:|---:|
| Karte-Ausschnitt | `70.6` | `page.width - 1572.9` |
| Karten-Legende | `page.width - 1573.4` | `page.width - 1048.5` |
| Karten-Details | `page.width - 1049.0` | `page.width - 524.1` |
| Plan-Infos | `page.width - 524.6` | `page.width - 13.9` |

## Ziel der Analyse

1. Zentralisierung der Daten aus vielen PDF-Plänen
2. Maßnahmenkataster (Boxen, Flächen, Pfade, Symbole)
3. GIS-Überführung (Punkte/Linien/Polygone)
4. Optimierung von Planung/Reporting

Die folgenden Dateien definieren Filterkriterien für `PyMuPDF` (`page.get_drawings()` / Text-Extraktion).
