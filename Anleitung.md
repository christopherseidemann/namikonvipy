# NaMi-SEPA-Konverter (DPSG)

Dieses Tool hilft DPSG-Stämmen, die Mitgliederdaten aus der offiziellen NaMi-Datenbank (Nutzerverwaltung der DPSG) zu exportieren und automatisch eine SEPA-Lastschriftdatei (Format `pain.008.003.02`) für das Online-Banking zu erstellen.

Zusätzlich filtert das Skript Mitglieder heraus, die selbst überweisen, sowie fehlerhafte Datensätze (z. B. ungültige IBANs).

Schnuppermitglieder und inaktive Mitglieder werden ebenfalls einfach gefiltert.

---

## Mit der App (für Einsteiger :) )

Die App läuft im Browser, aber nur auf deinem Computer. Du brauchst dafür kein Programmierwissen.

### Einmalig: Python installieren

Lade Python von [python.org](https://www.python.org/downloads/) herunter und installiere es mit den vorgeschlagenen Einstellungen. Python ist die Programmiersprache, in der das Tool geschrieben ist.

### Einmalig: Tool herunterladen

Auf der GitHub-Seite des Projekts auf **Code** → **Download ZIP** klicken und die ZIP-Datei entpacken.

### Starten

Doppelklick auf `starten.bat`. Beim ersten Start richtet sich das Tool ein, das dauert ein paar Minuten. Danach öffnet sich die App im Browser. Das schwarze Fenster offen lassen, solange du die App benutzt; zum Beenden einfach schließen.

Zeigt Windows eine Sicherheitswarnung, liegt das daran, dass die Datei aus dem Internet stammt. Dann das Ausführen erlauben.

### In der App

1. Links die Einstellungen ausfüllen (Vereinsdaten, Beiträge, Stammesname) und **Einstellungen speichern** klicken. Das ist nur beim ersten Mal nötig.
2. In NaMi einen Excel-Export der aktiven Mitglieder erstellen und die heruntergeladene `.xls`-Datei in der App hochladen. Umwandeln in `.xlsx` ist nicht nötig.
3. Das Abbuchungsdatum wählen. Die Bank braucht die Datei mindestens einen Bankarbeitstag vorher.
4. Unter **Prüfen** die Lastschriften durchsehen. In den Reitern **Zahlen selbst** und **Fehler** stehen alle, die nicht abgebucht werden.
5. **SEPA-Datei herunterladen**, von einer zweiten Person prüfen lassen und im Online-Banking hochladen.

Die Listen „Zahlen selbst“ und den Fehlerbericht kannst du ebenfalls als Excel-Datei herunterladen.

---

## Ohne App (Kommandozeile)

1. Einmalig im Ordner des Tools: `pip install -r requirements.txt`
2. Den NaMi-Export als `mitglieder_nami.xls` (oder `.xlsx`) in denselben Ordner legen.
3. `namikonvi.py` mit einem Texteditor öffnen und den oberen Bereich (VEREINSDATEN) anpassen:
   - `GLAEUBIGER_NAME`, `GLAEUBIGER_ID`: Name und Gläubiger-Identifikationsnummer deines Stammes (gibt's bei der Bundesbank/deiner Bank).
   - `GLAEUBIGER_IBAN`, `GLAEUBIGER_BIC`: Die Kontodaten deines Stammeskontos.
   - `FAELLIGKEITSDATUM`: Tag der Abbuchung, leer lassen für heute.
   - `STAMM_NAME`, `BEITRAGSJAHR`: Stehen im Verwendungszweck.
   - `MSG_ID_PREFIX`: Anfang der Dateikennung für die Bank, höchstens 17 Zeichen.
   - `BEITRAG_EINZELKIND`, `BEITRAG_GESCHWISTER`: Eure aktuellen Stammesbeiträge. Ein Kind zahlt den Einzelbeitrag; sind es zwei oder mehr Kinder auf demselben Konto, zahlt jedes Kind den Geschwisterbeitrag.
4. `python namikonvi.py` ausführen.

Das Skript erstellt dann drei Dateien (falls Daten vorhanden sind):

- `sepa_abbuchung.xml`: Diese Datei lädst du im Online-Banking deines Vereins hoch, um die Beiträge einzuziehen. **Bitte vorher alles kontrollieren.**
- `ueberweiser_finanzen.xlsx`: Eine Liste aller Mitglieder, bei denen keine IBAN hinterlegt ist. Diese müssen den Beitrag selbst überweisen.
- `fehlende_daten.xlsx`: Mitglieder, die zwar aktiv sind, aber nicht abgebucht werden können, weil die IBAN ungültig ist oder das Eintrittsdatum (= Mandatsdatum) fehlt. Der Grund steht in der Spalte `Fehlergrund`.

---

## Datenschutz & Sicherheit

Das Tool läuft vollständig lokal auf deinem Computer. Es werden keine Mitgliederdaten ins Internet hochgeladen oder an Dritte übertragen. Die App ist nur auf deinem eigenen Computer erreichbar, nicht im WLAN, und sendet auch keine Nutzungsstatistik an Streamlit. Die `.gitignore`-Datei sorgt dafür, dass deine Excel-Tabellen und Einstellungen niemals versehentlich auf GitHub veröffentlicht werden.

Gut Pfad :)

## Credits

Dieses Skript wurde von DPSG Balingen e.V. mit Unterstützung von Claude (Anthropic AI) entwickelt.
