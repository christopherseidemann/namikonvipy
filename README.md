# NaMi-SEPA-Konverter (DPSG)

Dieses Tool hilft DPSG-Stämmen, die Mitgliederdaten aus der offiziellen NaMi-Datenbank (Nutzerverwaltung der DPSG) zu exportieren und automatisch eine SEPA-Lastschriftdatei (`Format pain.008.003.02`) für das Online-Banking zu erstellen. 

Zusätzlich filtert das Skript Mitglieder heraus, die selbst überweisen, sowie fehlerhafte Datensätze (z.B. ungültige IBANs).

Schnuppermitglieder und inaktive Mitglieder werden ebenfalls einfach gefiltert.

---

## Voraussetzungen (Für Einsteiger :) )

Um dieses Skript zu nutzen, brauchst du **Python** auf deinem Computer und zwei Erweiterungen (sogenannte Bibliotheken):

1. **Python:** Das ist die Programmiersprache, in der das Skript geschrieben ist. ([Hier herunterladen](https://www.python.org/downloads/))
2. **Pandas:** Eine Erweiterung, die extrem gut mit Tabellen (Excel) umgehen kann.
3. **Openpyxl:** Eine Erweiterung, die Python erlaubt, moderne `.xlsx`-Dateien zu schreiben.

---

## Step-for-Step-Anleitung

### Schritt 1: Vorbereitung im NaMi
1. Logge dich ins NaMi ein.
2. Erstelle einen Excel-Export deiner aktiven Mitglieder. 
3. Benenne diese Datei um in: `mitglieder_nami.xlsx` und lege sie in denselben Ordner wie das Skript.

### Schritt 2: Installation (Nur beim ersten Mal)
Öffne die Eingabeaufforderung (Windows: `cmd` eingeben in der Suche) oder das Terminal (Mac) und tippe folgenden Befehl ein, um die benötigten Erweiterungen zu installieren:

```bash
pip install -r requirements.txt 
 
```

Schritt 3: Skript anpassen

Öffne die Datei namikonvi.py mit einem Texteditor und passe den oberen Bereich (VEREINSDATEN) an:

    GLAEUBIGER_ID: Die Gläubiger-Identifikationsnummer deines Stammes (gibt's bei der Bundesbank/deiner Bank).

    GLAEUBIGER_IBAN & GLAEUBIGER_BIC: Die Kontodaten deines Stammeskontos.

    BEITRAG_ERSTKIND & BEITRAG_GESCHWISTER: Eure aktuellen Stammesbeiträge.

Schritt 4: Skript starten

Führe das Skript im Terminal aus:

```bash
python namikonvi.py

```


Was passiert danach? (Ausgabedateien)

Das Skript erstellt drei Dateien (falls Daten vorhanden sind):

    sepa_abbuchung.xml: Diese Datei lädst du im Online-Banking deines Vereins hoch, um die Beiträge einzuziehen. BITTE VORHER ALLES KONTROLLIEREN.

    ueberweiser_finanzen.xlsx: Eine Liste aller Mitglieder, bei denen keine IBAN hinterlegt ist. Diese müssen den Beitrag selbst überweisen.

    fehlende_daten.xlsx: Eine Liste von Mitgliedern, bei denen der Status zwar auf "Aktiv" steht, aber die IBAN fehlerhaft oder ungültig ist.


Datenschutz & Sicherheit

Dieses Skript läuft vollständig lokal auf deinem Computer. Es werden keine Mitgliederdaten ins Internet hochgeladen oder an Dritte übertragen. Die .gitignore-Datei sorgt dafür, dass deine Excel-Tabellen niemals versehentlich auf GitHub veröffentlicht werden.

Gut Pfad :)

Credits
Dieses Skript wurde von DPSG Balingen e.V. mit Unterstützung von Claude (Anthropic AI) entwickelt.

