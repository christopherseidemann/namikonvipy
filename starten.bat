@echo off
REM Startet die App per Doppelklick. Beim ersten Mal wird alles Noetige installiert.
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python wurde nicht gefunden.
    echo Bitte von https://www.python.org/downloads/ installieren und danach erneut starten.
    pause
    exit /b 1
)

if not exist .venv (
    echo Erster Start: Programm wird eingerichtet. Das dauert ein paar Minuten ...
    py -3 -m venv .venv
)

.venv\Scripts\python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo.
echo Die App oeffnet sich gleich im Browser. Dieses Fenster offen lassen, solange du sie benutzt.
.venv\Scripts\python -m streamlit run app.py
pause
